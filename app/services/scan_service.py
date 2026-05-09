from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException
from app.models.scan import EscaneoMedioPago, AuditoriaEscaneo
from app.models.minuta import HCredencialSeguridad, PSeguridad
from app.services.openai_service import client
from app.core.config import settings
from app.utils.json_utils import parse_json_strict
import time
import uuid
import os
import base64
from datetime import datetime

class ScanService:
    @staticmethod
    async def scan_medio_pago(token: str, file: UploadFile, db: Session):
        start_time = time.time()
        
        # 0. Validar Seguridad Token y obtener co_notaria
        credencial = db.query(HCredencialSeguridad).join(
            PSeguridad, HCredencialSeguridad.co_seguridad == PSeguridad.co_seguridad
        ).filter(
            HCredencialSeguridad.no_token_api == token,
            HCredencialSeguridad.in_estado == 1
        ).first()

        if not credencial:
            raise HTTPException(status_code=400, detail="token incorrecto")

        co_notaria = str(credencial.seguridad.co_notaria)
        
        # 1. Generar nombre único para el archivo
        now = datetime.now()
        ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        unique_filename = f"{uuid.uuid4()}_{now.strftime('%H%M%S_%d%M%Y')}.{ext}"
        
        folder_path = os.path.join("assets", "escaneos")
        os.makedirs(folder_path, exist_ok=True)
        
        file_path = os.path.join(folder_path, unique_filename)
        try:
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"No se pudo guardar la imagen: {str(e)}")
            
        url_imagen = f"/{file_path.replace(os.sep, '/')}"
        
        # 2. Codificar imagen a Base64 para enviarla a OpenAI
        try:
            with open(file_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al procesar la imagen para IA: {str(e)}")

        # 3. Llamar a OpenAI con Vision
        prompt = """
        Eres un experto en extraer datos de documentos financieros (vouchers, cheques, capturas de transferencias).
        Analiza la imagen adjunta y extrae los siguientes datos en formato JSON estricto:
        {
          "medio_pago": "...", // Debe ser uno de: "DEPOSITO EN CUENTA", "CHEQUE DE GERENCIA", "TRANSFERENCIA DE FONDOS" según corresponda. Si es voucher de depósito -> "DEPOSITO EN CUENTA", si es cheque -> "CHEQUE DE GERENCIA", si es transferencia bancaria -> "TRANSFERENCIA DE FONDOS".
          "moneda": "...", // "SOLES" o "DOLARES"
          "valor_bien": "...", // El monto como string decimal, ej: "20000.00"
          "fecha_pago": "...", // En formato YYYY-MM-DD (si no encuentras el año, asume 2026)
          "bancos": "...", // Nombre del BANCO DE ORIGEN. ¡ATENCIÓN! Si la interfaz es de BCP (barra azul, iconos naranjas), pon "BCP" obligatoriamente, ignorando el texto de destino.
          "documento_pago": "..." // El número de operación, código de voucher o número de cheque.
        }
        
        REGLAS DE IDENTIFICACIÓN VISUAL DE BANCOS (SÚPER CRÍTICO):
        Queremos saber el BANCO DE ORIGEN (desde dónde se envía el dinero).
        En las transferencias interbancarias, el banco de destino aparece en texto (ej. "Enviado a SCOTIABANK"), pero el banco de origen es el dueño de la app (BCP).
        
        1. Para BCP:
        Si ves una barra superior azul intenso, botones o íconos de acción en color naranja, fondo blanco, check de éxito naranja, texto centrado de “Transferencia exitosa”, monto grande en azul, acciones “Descargar” y “Compartir” en naranja, y un botón inferior naranja redondeado:
        ¡ESTO ES BCP! Ignora cualquier texto que diga "Enviado a [Otro Banco]". El valor en "bancos" DEBE SER "BCP". No pongas el banco de destino.

        
        2. Para BBVA:
        Identifica como BBVA cuando la constancia tenga una interfaz blanca y limpia, textos principales en azul marino oscuro, título superior centrado como “Transferir”, botón de cierre “X” azul en la esquina superior derecha, una tarjeta grande de color verde claro con un check verde sólido, mensaje central “Operación exitosa”, monto grande en azul, y debajo una tarjeta de detalle con campos alineados en dos columnas: etiqueta a la izquierda y valor en negrita a la derecha. Si cumple estas características visuales, pon "BBVA" en el campo "bancos" aunque en el texto diga que se envió a otro banco.
        
        Si la imagen NO cumple con las características visuales de BCP o BBVA, entonces extrae el nombre del banco que aparezca explícitamente en el texto.
        
        El valor que devuelves en "bancos" debe ser SIEMPRE el nombre limpio del catálogo (ej: "BCP", "BBVA", "SCOTIABANK"). No uses prefijos como "Probable".
        
        Devuelve SOLO el objeto JSON, sin markdown ni texto adicional.


        """


        try:
            response = client.chat.completions.create(
                model=getattr(settings, "openai_model", "gpt-4o-mini"),
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "Devuelve SOLO un objeto JSON válido."},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{ext};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
            )
            
            # Extraer respuesta
            text_response = response.choices[0].message.content
            detected_data = parse_json_strict(text_response)
            
            usage = getattr(response, "usage", None)
            tokens_consumidos = getattr(usage, "total_tokens", 0) if usage else 0
            
        except Exception as e:
            # En caso de error, guardamos la auditoría como fallida
            duracion_ms = int((time.time() - start_time) * 1000)
            auditoria = AuditoriaEscaneo(
                co_notaria=co_notaria,
                duracion_ms=duracion_ms,
                tokens_consumidos=0,
                estado="ERROR",
                mensaje_error=str(e)
            )
            # Necesitamos un id_escaneo, pero si falló la IA antes de insertar el histórico, 
            # tal vez queramos insertar el histórico de todas formas con datos nulos.
            # Vamos a insertar el histórico con datos nulos para dejar rastro de la imagen subida.
            
            escaneo_fail = EscaneoMedioPago(
                co_notaria=co_notaria,
                co_tipo_doc=1, 
                url_imagen=url_imagen,
                raw_ai_response={"error": str(e)}
            )
            db.add(escaneo_fail)
            db.commit()
            db.refresh(escaneo_fail)
            
            auditoria.id_escaneo = escaneo_fail.id_escaneo
            db.add(auditoria)
            db.commit()
            
            raise HTTPException(status_code=500, detail=f"Error en el procesamiento de IA: {str(e)}")

        # 4. Guardar en Histórico (Éxito)
        # Mapeo de tipo_doc según medio_pago detectado
        co_tipo_doc = 1 # Por defecto Voucher
        if detected_data.get("medio_pago") == "CHEQUE DE GERENCIA":
            co_tipo_doc = 2
        elif detected_data.get("medio_pago") == "TRANSFERENCIA DE FONDOS":
            co_tipo_doc = 3

        escaneo = EscaneoMedioPago(
            co_notaria=co_notaria,
            co_tipo_doc=co_tipo_doc, 
            url_imagen=url_imagen,
            medio_pago=detected_data.get("medio_pago"),
            moneda=detected_data.get("moneda"),
            monto=float(detected_data.get("valor_bien")) if detected_data.get("valor_bien") else None,
            fecha_pago=datetime.strptime(detected_data.get("fecha_pago"), "%Y-%m-%d").date() if detected_data.get("fecha_pago") else None,
            bancos=detected_data.get("bancos"),
            documento_pago=detected_data.get("documento_pago"),
            raw_ai_response=detected_data
        )
        
        db.add(escaneo)
        db.commit()
        db.refresh(escaneo)
        
        # 5. Guardar en Auditoría (Éxito)
        duracion_ms = int((time.time() - start_time) * 1000)
        auditoria = AuditoriaEscaneo(
            id_escaneo=escaneo.id_escaneo,
            co_notaria=co_notaria,
            duracion_ms=duracion_ms,
            tokens_consumidos=tokens_consumidos,
            estado="SUCCESS"
        )
        db.add(auditoria)
        db.commit()
        
        return {
            "status": "success",
            "data": {
                "id_escaneo": escaneo.id_escaneo,
                "tipo_documento": detected_data.get("medio_pago"),
                "valores": {
                    "medio_pago": detected_data.get("medio_pago"),
                    "moneda": detected_data.get("moneda"),
                    "co_moneda": 1 if detected_data.get("moneda") == "SOLES" else 2,
                    "valor_bien": detected_data.get("valor_bien"),
                    "fecha_pago": detected_data.get("fecha_pago"),
                    "bancos": detected_data.get("bancos"),
                    "documento_pago": detected_data.get("documento_pago")
                }
            }
        }
