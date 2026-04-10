from sqlalchemy.orm import Session
from app.models.minuta import ConsultaMinuta, ParticipanteMinuta, ValorMinutaMaster, ValorTransferencia, ValorMedioPago, BienMinuta
from app.utils.date_utils import parse_optional_date
import logging

logger = logging.getLogger(__name__)

class MinutaRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_full_minuta(self, payload: dict, docx_bytes: bytes, co_cnl: str, estado: str = "EXITO") -> ConsultaMinuta:
        """
        Persiste el payload canónico y el archivo binario en la base de datos histórica.
        """
        try:
            acto_data = payload.get("acto", {})
            
            # 1. Crear Cabecera (ConsultaMinuta)
            nueva_consulta = ConsultaMinuta(
                co_cnl=co_cnl,
                no_servicio=acto_data.get("nombre_servicio"),
                fe_minuta=parse_optional_date(acto_data.get("fecha_minuta")),
                minuta_archivo=docx_bytes,
                estado_minuta=estado
            )
            self.db.add(nueva_consulta)
            self.db.flush()  # Para obtener el id_consulta

            # 2. Procesar Participantes
            participantes_group = payload.get("participantes", {})
            for grupo_key, lista in participantes_group.items():
                if not lista:
                    continue
                # grupo_key: otorgantes, beneficiarios, fiduciarios
                grupo_name = grupo_key[:-1].upper() if grupo_key.endswith('s') else grupo_key.upper()
                
                for p in lista:
                    # Si no hay nombre ni razón social, ignorar
                    if not p.get("nombres") and not p.get("razon_social"):
                        continue
                        
                    doc = p.get("documento", {})
                    dom = p.get("domicilio", {})
                    ubi = dom.get("ubigeo", {})
                    
                    nuevo_p = ParticipanteMinuta(
                        id_consulta=nueva_consulta.id_consulta,
                        grupo_participante=grupo_name,
                        tipo_persona=p.get("tipo_persona"),
                        nombres=p.get("nombres"),
                        apellido_paterno=p.get("apellido_paterno"),
                        apellido_materno=p.get("apellido_materno"),
                        razon_social=p.get("razon_social"),
                        ciiu=p.get("ciiu"),
                        co_ciiu=p.get("co_ciiu"),
                        objeto_empresa=p.get("objeto_empresa"),
                        pais=p.get("pais"),
                        co_pais=p.get("co_pais"),
                        documento_tipo=doc.get("tipo_documento"),
                        documento_numero=doc.get("numero_documento"),
                        documento_co=doc.get("co_documento"),
                        ocupacion=p.get("ocupacion"),
                        co_ocupacion=p.get("co_ocupacion"),
                        otros_ocupaciones=p.get("otros_ocupaciones"),
                        estado_civil=p.get("estado_civil"),
                        co_estado_civil=p.get("co_estado_civil"),
                        domicilio_direccion=dom.get("direccion"),
                        ubigeo_departamento=ubi.get("departamento"),
                        ubigeo_provincia=ubi.get("provincia"),
                        ubigeo_distrito=ubi.get("distrito"),
                        genero=p.get("genero"),
                        rol=p.get("rol"),
                        relacion=p.get("relacion"),
                        porcentaje_participacion=p.get("porcentaje_participacion", 0.0),
                        nu_acciones=p.get("numeroAcciones_participaciones", 0),
                        nu_acciones_suscritas=p.get("acciones_suscritas", 0),
                        mo_aportado=p.get("monto_aportado", 0.0)
                    )
                    self.db.add(nuevo_p)

            # 3. Procesar Valores (Jerarquía: Maestro -> Detalles)
            valores_group = payload.get("valores", {})
            trans_list = valores_group.get("transferencia", [])
            pagos_list = valores_group.get("medioPago", [])

            max_len = max(len(trans_list), len(pagos_list))
            for i in range(max_len):
                t = trans_list[i] if i < len(trans_list) else {}
                p = pagos_list[i] if i < len(pagos_list) else {}

                # Si ambos están vacíos (placeholders), saltar
                if not any(t.values()) and not any(p.values()):
                    continue

                # 3.1 Crear el Maestro
                maestro = ValorMinutaMaster(
                    id_consulta=nueva_consulta.id_consulta,
                    tipo_registro="VALOR"
                )
                self.db.add(maestro)
                self.db.flush()  # Para obtener el id_valor generado

                # 3.2 Crear Detalle de Transferencia si hay data
                if any(t.values()):
                    nueva_t = ValorTransferencia(
                        id_valor=maestro.id_valor,
                        moneda=t.get("moneda"),
                        co_moneda=t.get("co_moneda"),
                        monto=t.get("monto"),
                        forma_pago=t.get("forma_pago"),
                        oportunidad_pago=t.get("oportunidad_pago")
                    )
                    self.db.add(nueva_t)

                # 3.3 Crear Detalle de Medio de Pago si hay data
                if any(p.values()):
                    nuevo_p = ValorMedioPago(
                        id_valor=maestro.id_valor,
                        medio_pago=p.get("medio_pago"),
                        moneda=p.get("moneda"),
                        co_moneda=p.get("co_moneda"),
                        valor_bien=p.get("valor_bien"),
                        fecha_pago=parse_optional_date(p.get("fecha_pago")),
                        bancos=p.get("bancos"),
                        documento_pago=p.get("documento_pago")
                    )
                    self.db.add(nuevo_p)

            # 4. Procesar Bienes
            for b in payload.get("bienes", []):
                # Validar que no sea un objeto vacío
                if not b.get("tipo_bien") and not b.get("partida_registral"):
                    continue
                    
                ubi = b.get("ubigeo", {})
                nuevo_b = BienMinuta(
                    id_consulta=nueva_consulta.id_consulta,
                    tipo_bien=b.get("tipo_bien"),
                    clase_bien=b.get("clase_bien"),
                    ubigeo_departamento=ubi.get("departamento"),
                    ubigeo_provincia=ubi.get("provincia"),
                    ubigeo_distrito=ubi.get("distrito"),
                    partida_registral=b.get("partida_registral"),
                    zona_registral=b.get("zona_registral"),
                    co_zona_registral=b.get("co_zona_registral"),
                    fe_adquisicion=parse_optional_date(b.get("fecha_adquisicion")),
                    fe_minuta_bien=parse_optional_date(b.get("fecha_minuta")),
                    opcion_bien_mueble=b.get("opcion_bien_mueble"),
                    nu_psm=b.get("numero_psm"),
                    otros_bienes=b.get("otros_bienes"),
                    pais=b.get("pais"),
                    origen_bien=b.get("origen_del_bien")
                )
                self.db.add(nuevo_b)

            self.db.commit()
            return nueva_consulta
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error guardando historial de minuta: {str(e)}")
            raise e
