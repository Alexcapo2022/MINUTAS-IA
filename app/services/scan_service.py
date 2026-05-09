from sqlalchemy.orm import Session
from fastapi import UploadFile
from app.models.scan import EscaneoMedioPago, AuditoriaEscaneo
import time
import uuid
from datetime import datetime

class ScanService:
    @staticmethod
    def scan_medio_pago(co_notaria: str, file: UploadFile, db: Session):
        start_time = time.time()
        
        # 1. Generar nombre único para el archivo
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
