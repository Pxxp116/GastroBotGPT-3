import httpx
import logging
from typing import Dict, Any, Optional
from datetime import datetime, time
from app.core.config import settings
from app.core.logic import generate_alternative_slots

logger = logging.getLogger(__name__)

class BackendClient:
    """Cliente para comunicarse con el backend de GastroBot"""
    
    def __init__(self):
        self.base_url = settings.BACKEND_BASE_URL.rstrip('/')
        self.timeout = settings.BACKEND_TIMEOUT
        self.retry_attempts = settings.BACKEND_RETRY_ATTEMPTS
        
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Realiza una petición HTTP al backend con reintentos"""
        
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient() as client:
            for attempt in range(self.retry_attempts):
                try:
                    logger.info(f"Llamando {method} {url} (intento {attempt + 1})")
                    
                    response = await client.request(
                        method=method,
                        url=url,
                        json=data,
                        params=params,
                        timeout=self.timeout
                    )
                    
                    response.raise_for_status()
                    return response.json()
                    
                except httpx.TimeoutException:
                    logger.warning(f"Timeout en {url} (intento {attempt + 1})")
                    if attempt == self.retry_attempts - 1:
                        return {
                            "exito": False,
                            "mensaje": "El sistema está tardando en responder. Por favor, intenta de nuevo."
                        }
                        
                except httpx.HTTPStatusError as e:
                    logger.error(f"Error HTTP {e.response.status_code} en {url}")
                    if e.response.status_code >= 500:
                        if attempt == self.retry_attempts - 1:
                            return {
                                "exito": False,
                                "mensaje": "El sistema está experimentando problemas. Por favor, intenta más tarde."
                            }
                    else:
                        try:
                            error_data = e.response.json()
                            return error_data
                        except:
                            return {
                                "exito": False,
                                "mensaje": f"Error en el servidor: {e.response.status_code}"
                            }
                            
                except Exception as e:
                    logger.error(f"Error inesperado llamando a {url}: {e}")
                    if attempt == self.retry_attempts - 1:
                        return {
                            "exito": False,
                            "mensaje": "Ha ocurrido un error inesperado. Por favor, intenta de nuevo."
                        }
        
        return {"exito": False, "mensaje": "No se pudo conectar con el servidor"}
    
    async def check_availability(
        self,
        fecha: str,
        hora: str,
        comensales: int,
        duracion_min: int = None
    ) -> Dict[str, Any]:
        """Verifica disponibilidad de mesas"""
        
        if duracion_min is None:
            duracion_min = settings.DEFAULT_DURATION_MIN
            
        result = await self._make_request(
            method="POST",
            endpoint="/buscar-mesa",
            data={
                "fecha": fecha,
                "hora": hora,
                "personas": comensales,
                "duracion": duracion_min
            }
        )
        
        # Si no hay disponibilidad, generar alternativas
        if not result.get("exito") or not result.get("mesa_disponible"):
            alternativas = await generate_alternative_slots(
                fecha, hora, comensales, duracion_min
            )
            result["alternativas"] = alternativas
            
        return result
    
    async def create_reservation(
        self,
        nombre: str,
        telefono: str,
        fecha: str,
        hora: str,
        comensales: int,
        zona: Optional[str] = None,
        alergias: Optional[str] = None,
        comentarios: Optional[str] = None
    ) -> Dict[str, Any]:
        """Crea una nueva reserva"""
        
        # Limpiar el teléfono de WhatsApp
        telefono_limpio = telefono.replace("whatsapp:", "").replace("+", "")
        
        # Primero buscar mesa disponible
        availability = await self.check_availability(
            fecha, hora, comensales, settings.DEFAULT_DURATION_MIN
        )
        
        if not availability.get("exito") or not availability.get("mesa_disponible"):
            return {
                "exito": False,
                "mensaje": "No hay mesas disponibles para esa hora",
                "alternativas": availability.get("alternativas", [])
            }
        
        # Asegurar que todos los valores son strings/números válidos
        mesa_info = availability["mesa_disponible"]
        mesa_id = int(mesa_info.get("id", 1))  # Asegurar que es entero
        
        # Crear la reserva con valores seguros
        data = {
            "nombre": str(nombre),
            "telefono": str(telefono_limpio),
            "email": "",  # String vacío, no None
            "fecha": str(fecha),
            "hora": str(hora),
            "personas": int(comensales),  # Asegurar que es entero
            "mesa_id": mesa_id,  # Asegurar que es entero
            "duracion": int(settings.DEFAULT_DURATION_MIN),  # Asegurar que es entero
            "notas": str(comentarios) if comentarios else "",  # Convertir None a ""
            "alergias": str(alergias) if alergias else "",  # Convertir None a ""
            "zona_preferida": str(zona) if zona else ""  # Convertir None a ""
        }
        
        # Log para debug
        logger.info(f"Enviando datos de reserva: {data}")
        logger.info(f"Tipos de datos: {[(k, type(v).__name__) for k, v in data.items()]}")
        
        result = await self._make_request(
            method="POST",
            endpoint="/crear-reserva",
            data=data
        )
        
        return result
    
    async def modify_reservation(
        self,
        id_reserva: Optional[int] = None,
        nombre: Optional[str] = None,
        telefono: Optional[str] = None,
        fecha_antigua: Optional[str] = None,
        hora_antigua: Optional[str] = None,
        cambios: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Modifica una reserva existente"""
        
        if not cambios:
            return {
                "exito": False,
                "mensaje": "No se especificaron cambios"
            }
        
        # Limpiar teléfono
        if telefono:
            telefono_limpio = telefono.replace("whatsapp:", "").replace("+", "").replace(" ", "")
        else:
            telefono_limpio = None
        
        # Si no tenemos ID, buscar la reserva
        if not id_reserva:
            espejo = await self._make_request(
                method="GET",
                endpoint="/espejo"
            )
            
            if espejo.get("exito"):
                reservas = espejo.get("espejo", {}).get("reservas", [])
                logger.info(f"📋 Total reservas en sistema: {len(reservas)}")
                
                # Buscar por coincidencia
                for reserva in reservas:
                    # Log detallado para debug
                    logger.info(f"Comparando con reserva: {reserva}")
                    
                    # Limpiar teléfono de la reserva para comparar
                    tel_reserva = str(reserva.get("telefono", "")).replace("+", "").replace(" ", "")
                    
                    # Comparación flexible
                    match = True
                    
                    # Comparar nombre (ignorar mayúsculas)
                    if nombre:
                        nombre_reserva = reserva.get("nombre", "").lower()
                        if nombre.lower() not in nombre_reserva and nombre_reserva not in nombre.lower():
                            match = False
                            logger.info(f"  ❌ Nombre no coincide: '{nombre}' vs '{reserva.get('nombre')}'")
                    
                    # Comparar teléfono (flexible)
                    if telefono_limpio and tel_reserva:
                        # Comparar los últimos 9 dígitos
                        tel_limpio_digits = ''.join(filter(str.isdigit, telefono_limpio))[-9:]
                        tel_reserva_digits = ''.join(filter(str.isdigit, tel_reserva))[-9:]
                        
                        if tel_limpio_digits != tel_reserva_digits:
                            match = False
                            logger.info(f"  ❌ Teléfono no coincide: '{tel_limpio_digits}' vs '{tel_reserva_digits}'")
                        else:
                            logger.info(f"  ✅ Teléfono coincide: {tel_limpio_digits}")
                    
                    # Comparar fecha si se proporciona
                    if fecha_antigua and reserva.get("fecha") != fecha_antigua:
                        match = False
                        logger.info(f"  ❌ Fecha no coincide: '{fecha_antigua}' vs '{reserva.get('fecha')}'")
                    
                    # Comparar hora si se proporciona
                    if hora_antigua and reserva.get("hora") != hora_antigua:
                        match = False
                        logger.info(f"  ❌ Hora no coincide: '{hora_antigua}' vs '{reserva.get('hora')}'")
                    
                    if match:
                        id_reserva = reserva.get("id")
                        logger.info(f"✅ RESERVA ENCONTRADA! ID: {id_reserva}")
                        break
                
                if not id_reserva:
                    # Mostrar todas las reservas para debug
                    logger.warning("No se encontró coincidencia. Reservas actuales:")
                    for r in reservas[:5]:  # Mostrar solo las primeras 5
                        logger.warning(f"  - {r.get('nombre')} | {r.get('telefono')} | {r.get('fecha')} | {r.get('hora')}")
            
            if not id_reserva:
                return {
                    "exito": False,
                    "mensaje": "No encuentro tu reserva. ¿Puedes decirme el nombre y fecha de la reserva?"
                }
        
        # Modificar la reserva
        logger.info(f"Modificando reserva ID {id_reserva} con cambios: {cambios}")
        
        result = await self._make_request(
            method="PUT",
            endpoint=f"/modificar-reserva/{id_reserva}",
            data=cambios
        )
        
        return result
        
    async def cancel_reservation(
        self,
        id_reserva: Optional[int] = None,
        nombre: Optional[str] = None,
        telefono: Optional[str] = None,
        fecha: Optional[str] = None,
        hora: Optional[str] = None,
        motivo: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cancela una reserva"""
        
        # Si no tenemos ID, buscar la reserva
        if not id_reserva:
            espejo = await self._make_request(
                method="GET",
                endpoint="/espejo"
            )
            
            if espejo.get("exito"):
                reservas = espejo.get("espejo", {}).get("reservas", [])
                
                for reserva in reservas:
                    match = True
                    if nombre and reserva.get("nombre") != nombre:
                        match = False
                    if telefono and reserva.get("telefono") != telefono:
                        match = False
                    if fecha and reserva.get("fecha") != fecha:
                        match = False
                    if hora and reserva.get("hora") != hora:
                        match = False
                        
                    if match:
                        id_reserva = reserva.get("id")
                        break
                        
            if not id_reserva:
                return {
                    "exito": False,
                    "mensaje": "No se encontró la reserva a cancelar"
                }
        
        result = await self._make_request(
            method="DELETE",
            endpoint=f"/cancelar-reserva/{id_reserva}",
            data={"motivo": motivo or "Cancelado por el cliente"}
        )
        
        return result
    
    async def get_menu(self, categoria: Optional[str] = None) -> Dict[str, Any]:
        """Obtiene el menú del restaurante"""
        
        result = await self._make_request(
            method="GET",
            endpoint="/ver-menu"
        )
        
        if categoria and result.get("exito"):
            menu = result.get("menu", {})
            categorias = menu.get("categorias", [])
            
            # Filtrar por categoría
            categoria_filtrada = None
            for cat in categorias:
                if cat.get("nombre", "").lower() == categoria.lower():
                    categoria_filtrada = cat
                    break
                    
            if categoria_filtrada:
                result["menu"] = {"categorias": [categoria_filtrada]}
            else:
                result["mensaje"] = f"No se encontró la categoría '{categoria}'"
                
        return result
    
    async def get_hours(self, fecha: Optional[str] = None) -> Dict[str, Any]:
        """Obtiene los horarios del restaurante"""
        
        params = {}
        if fecha:
            params["fecha"] = fecha
            
        result = await self._make_request(
            method="GET",
            endpoint="/consultar-horario",
            params=params
        )
        
        return result
    
    async def get_policies(self) -> Dict[str, Any]:
        """Obtiene las políticas del restaurante"""
        
        # Usar el espejo para obtener políticas
        espejo = await self._make_request(
            method="GET",
            endpoint="/espejo"
        )
        
        if espejo.get("exito"):
            politicas = espejo.get("espejo", {}).get("politicas", {})
            return {
                "exito": True,
                "politicas": politicas
            }
            
        return {
            "exito": False,
            "mensaje": "No se pudieron obtener las políticas"
        }

# Instancia global
backend_client = BackendClient()