from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException
from app.models.scan import EscaneoMedioPago, AuditoriaEscaneo
from app.models.minuta import HCredencialSeguridad, PSeguridad
import time
import uuid
from datetime import datetime

class ScanService:
    @staticmethod
    def scan_medio_pago(token: str, file: UploadFile, db: Session):
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

        # Obtenemos la notaría asociada al token
        co_notaria = str(credencial.seguridad.co_notaria)
        
        # 1. Generar nombre único para el archivo
        # Patrón: UUID_HHMMSS_DDMMYYYY.ext
        now = datetime.now()
        ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        unique_filename = f"{uuid.uuid4()}_{now.strftime('%H%M%S_%d%M%Y')}.{ext}"
        
        url_imagen = f"/assets/escaneos/{unique_filename}"
        
        # 2. Simulación de IA (Para pruebas)
        detected_data = {
            "medio_pago": "DEPOSITO EN CUENTA",
            "moneda": "SOLES",
            "valor_bien": "20000.00",
            "fecha_pago": "2026-05-07",
            "bancos": "BBVA",
            "documento_pago": "VOU-998822"
        }
        
        # 3. Guardar en Histórico
        escaneo = EscaneoMedioPago(
            co_notaria=co_notaria,
            co_tipo_doc=1, 
            url_imagen=url_imagen,
            medio_pago=detected_data["medio_pago"],
            moneda=detected_data["moneda"],
            monto=float(detected_data["valor_bien"]),
            fecha_pago=datetime.strptime(detected_data["fecha_pago"], "%Y-%m-%d").date(),
            bancos=detected_data["bancos"],
            documento_pago=detected_data["documento_pago"],
            raw_ai_response=detected_data
        )
        
        db.add(escaneo)
        db.commit()
        db.refresh(escaneo)
        
        # 4. Guardar en Auditoría
        duracion_ms = int((time.time() - start_time) * 1000)
        auditoria = AuditoriaEscaneo(
            id_escaneo=escaneo.id_escaneo,
            co_notaria=co_notaria,
            duracion_ms=duracion_ms,
            tokens_consumidos=150,
            estado="SUCCESS"
        )
        db.add(auditoria)
        db.commit()
        
        return {
            "status": "success",
            "data": {
                "id_escaneo": escaneo.id_escaneo,
                "tipo_documento": "VOUCHER",
                "valores": {
                    "medio_pago": detected_data["medio_pago"],
                    "moneda": detected_data["moneda"],
                    "co_moneda": 1,
                    "valor_bien": detected_data["valor_bien"],
                    "fecha_pago": detected_data["fecha_pago"],
                    "bancos": detected_data["bancos"],
                    "documento_pago": detected_data["documento_pago"]
                }
            }
        }
