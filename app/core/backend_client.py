"""
Cliente para comunicación con el backend de GastroBot
Versión corregida con manejo obligatorio de códigos de reserva
"""

import httpx
import logging
from typing import Dict, Any, Optional
from app.core.config import settings
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Cache global para la duración - MUY AGRESIVO
_duration_cache = {
    "value": 120,  # FORZAR 120 MINUTOS INMEDIATAMENTE
    "timestamp": datetime.now() - timedelta(hours=2),  # Forzar que esté expirado
    "ttl_minutes": 60  # Cache por 1 hora para ser agresivo
}

class BackendClient:
    """Cliente para interactuar con el backend de reservas"""
    
    def __init__(self):
        self.base_url = settings.BACKEND_BASE_URL
        self.timeout = settings.BACKEND_TIMEOUT
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            follow_redirects=True
        )
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def _normalize_phone(self, phone: str) -> str:
        """Normaliza formato de teléfono para comparaciones"""
        if not phone:
            return ""
        # Eliminar todo excepto dígitos
        digits = re.sub(r'[^\d]', '', str(phone))
        # Tomar los últimos 9 dígitos (formato español sin código de país)
        return digits[-9:] if len(digits) >= 9 else digits
    
    def _validate_reservation_code(self, code: str) -> bool:
        """Valida formato del código de reserva"""
        if not code:
            return False
        code = code.strip().upper()
        # Código debe ser alfanumérico de 8 caracteres
        return len(code) == 8 and code.isalnum()
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Realiza una petición HTTP al backend"""
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.info(f"Llamando {method} {url} (intento 1)")
            
            if data:
                logger.info(f"Datos enviados: {data}")
            
            response = await self.client.request(
                method=method,
                url=url,
                json=data,
                params=params
            )
            
            logger.info(f"Respuesta recibida: {response.status_code}")
            
            if response.status_code >= 400:
                logger.error(f"Error HTTP {response.status_code}: {response.text}")
                return {
                    "exito": False,
                    "mensaje": f"Error del servidor: {response.status_code}"
                }
            
            result = response.json()
            
            # Log del resultado para debug
            if not result.get("exito"):
                logger.warning(f"Operación fallida: {result.get('mensaje')}")
            
            return result
            
        except httpx.TimeoutException:
            logger.error(f"Timeout llamando a {url}")
            return {
                "exito": False,
                "mensaje": "El servidor tardó demasiado en responder"
            }
        except httpx.RequestError as e:
            logger.error(f"Error de conexión: {e}")
            return {
                "exito": False,
                "mensaje": "Error de conexión con el servidor"
            }
        except Exception as e:
            logger.error(f"Error inesperado: {e}", exc_info=True)
            return {
                "exito": False,
                "mensaje": "Error procesando la solicitud"
            }
    
    async def get_duration_from_policies(self, force_refresh: bool = False) -> int:
        """
        Obtiene la duración de reserva con cache agresivo
        
        Args:
            force_refresh: Si True, fuerza actualización del cache ignorando TTL
        """
        global _duration_cache
        
        # Verificar si el cache es válido Y no se fuerza refresh
        now = datetime.now()
        if (not force_refresh and _duration_cache["value"] and 
            _duration_cache["timestamp"] and 
            (now - _duration_cache["timestamp"]).total_seconds() < (_duration_cache["ttl_minutes"] * 60)):
            logger.info(f"Usando duración desde cache: {_duration_cache['value']} minutos")
            return _duration_cache["value"]
        
        # Actualizar cache cuando sea viejo o se fuerce
        try:
            if force_refresh:
                logger.info("Forzando actualización de duración desde backend")
            else:
                logger.info("Cache expirado, obteniendo duración desde backend")
            result = await self._make_request(
                method="GET",
                endpoint="/admin/politicas"
            )
            
            if result.get("exito") and result.get("politicas"):
                duracion = (result["politicas"].get("tiempo_mesa_minutos") or 
                           result["politicas"].get("duracion_estandar_min") or
                           120)  # Default a 120 no 90
                
                # Actualizar cache
                _duration_cache["value"] = duracion
                _duration_cache["timestamp"] = now
                
                logger.info(f"Duración actualizada en cache: {duracion} minutos")
                return duracion
            
            logger.warning("No se pudieron obtener políticas, usando cache o default")
            return _duration_cache["value"] or 120
            
        except Exception as e:
            logger.warning(f"Error obteniendo duración, usando cache o default: {e}")
            return _duration_cache["value"] or 120
    
    def invalidate_duration_cache(self):
        """Invalida el cache de duración forzando una actualización en la próxima consulta"""
        global _duration_cache
        _duration_cache["timestamp"] = datetime.now() - timedelta(hours=2)  # Forzar expiración
        logger.info("Cache de duración invalidado")
    
    async def get_fresh_restaurant_hours(self, fecha: str) -> Dict[str, Any]:
        """
        Obtiene horarios frescos del restaurante para una fecha específica
        Usado para generar sugerencias con datos actualizados
        """
        try:
            result = await self._make_request(
                method="GET",
                endpoint="/admin/horarios"
            )
            
            if result.get("exito") and result.get("horarios"):
                # Encontrar horario para la fecha específica
                fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
                dia_semana = fecha_dt.weekday()  # 0=Lunes, 6=Domingo
                
                # Mapear días de la semana
                dias_map = {0: 'lunes', 1: 'martes', 2: 'miercoles', 3: 'jueves', 
                           4: 'viernes', 5: 'sabado', 6: 'domingo'}
                dia_nombre = dias_map.get(dia_semana, 'lunes')
                
                horarios = result["horarios"]
                dia_horario = None
                
                # Buscar horario específico del día
                for horario in horarios:
                    if horario.get("dia_semana", "").lower() == dia_nombre:
                        dia_horario = horario
                        break
                
                if dia_horario and not dia_horario.get("cerrado", False):
                    return {
                        "apertura": dia_horario.get("hora_apertura", "13:00"),
                        "cierre": dia_horario.get("hora_cierre", "23:00"),
                        "cerrado": False
                    }
                else:
                    return {"cerrado": True}
            
            # Fallback a horarios por defecto si no hay datos
            return {"apertura": "13:00", "cierre": "23:00", "cerrado": False}
            
        except Exception as e:
            logger.error(f"Error obteniendo horarios frescos: {e}")
            # Fallback a horarios por defecto
            return {"apertura": "13:00", "cierre": "23:00", "cerrado": False}

    async def check_availability(
        self,
        fecha: str,
        hora: str,
        comensales: int
    ) -> Dict[str, Any]:
        """Verifica disponibilidad para una fecha y hora"""
        
        logger.info(f"Verificando disponibilidad: {fecha} {hora} para {comensales} personas")
        
        # Obtener duración dinámica del backend (forzar actualización para sugerencias precisas)
        duracion = await self.get_duration_from_policies(force_refresh=True)
        
        result = await self._make_request(
            method="POST",
            endpoint="/buscar-mesa",
            data={
                "fecha": fecha,
                "hora": hora,
                "personas": comensales,
                "duracion": duracion
            }
        )
        
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
        comentarios: Optional[str] = None,
        email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Crea una nueva reserva"""
        
        # Limpiar y validar teléfono
        telefono_limpio = self._normalize_phone(telefono)
        if len(telefono_limpio) < 9:
            return {
                "exito": False,
                "mensaje": "El número de teléfono no es válido"
            }
        
        # Verificar disponibilidad primero
        availability = await self.check_availability(fecha, hora, comensales)
        
        if not availability.get("exito") or not availability.get("mesa_disponible"):
            # Invalidar cache si el horario fue rechazado (podría indicar datos obsoletos)
            motivo = availability.get("mensaje", "")
            if "duración" in motivo.lower() or "terminaría después" in motivo.lower():
                logger.info("Invalidando cache por posible incompatibilidad de duración")
                self.invalidate_duration_cache()
            
            # Si hay sugerencia de horario, usar esa información
            if availability.get("sugerencia") or availability.get("alternativa"):
                sugerencia = availability.get("sugerencia") or availability.get("alternativa")
                mensaje = availability.get("mensaje", "No hay disponibilidad para esa hora")
                
                if sugerencia and sugerencia.get("hora"):
                    mensaje += f". Te sugiero la hora {sugerencia['hora']}"
                    if sugerencia.get("mensaje"):
                        mensaje += f" ({sugerencia['mensaje']})"
                
                return {
                    "exito": False,
                    "mensaje": mensaje,
                    "sugerencia": sugerencia,
                    "alternativas": availability.get("alternativas", []),
                    "horario_rechazado": {
                        "fecha": fecha,
                        "hora": hora,
                        "motivo": availability.get("mensaje", "Fuera de horario")
                    }
                }
            
            return {
                "exito": False,
                "mensaje": availability.get("mensaje", "No hay mesas disponibles para esa hora"),
                "alternativas": availability.get("alternativas", [])
            }
        
        # Obtener información de la mesa
        mesa_info = availability["mesa_disponible"]
        mesa_id = int(mesa_info.get("id", 1))
        
        # Obtener duración dinámica del backend (forzar actualización para datos precisos)
        duracion = await self.get_duration_from_policies(force_refresh=True)
        
        # Crear la reserva con valores seguros
        data = {
            "nombre": str(nombre),
            "telefono": str(telefono_limpio),
            "email": str(email) if email else "",
            "fecha": str(fecha),
            "hora": str(hora),
            "personas": int(comensales),
            "mesa_id": mesa_id,
            "duracion": int(duracion),
            "notas": str(comentarios) if comentarios else "",
            "alergias": str(alergias) if alergias else "",
            "zona_preferida": str(zona) if zona else ""
        }
        
        logger.info(f"Creando reserva con datos: {data}")
        
        result = await self._make_request(
            method="POST",
            endpoint="/crear-reserva",
            data=data
        )
        
        # Si la creación fue exitosa, asegurar que incluye el código
        if result.get("exito") and result.get("reserva"):
            if not result.get("codigo_reserva"):
                result["codigo_reserva"] = result["reserva"].get("codigo_reserva", "")
            
            logger.info(f"Reserva creada con código: {result.get('codigo_reserva')}")
        
        return result
    
    async def modify_reservation(
        self,
        codigo_reserva: Optional[str] = None,
        id_reserva: Optional[int] = None,
        cambios: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Modifica una reserva existente
        REQUIERE código de reserva o ID
        """
        
        if not cambios:
            return {
                "exito": False,
                "mensaje": "No se especificaron cambios"
            }
        
        # Validar que tenemos identificador
        if not codigo_reserva and not id_reserva:
            return {
                "exito": False,
                "mensaje": "📋 Para modificar tu reserva necesito tu código de confirmación.\n" +
                         "Lo encuentras en el mensaje que recibiste al hacer la reserva (8 caracteres).",
                "requiere_codigo": True
            }
        
        # Si tenemos código, validarlo
        if codigo_reserva:
            if not self._validate_reservation_code(codigo_reserva):
                return {
                    "exito": False,
                    "mensaje": "❌ El código de reserva no es válido. Debe tener 8 caracteres (ej: ABC12345).",
                    "codigo_invalido": True
                }
            
            codigo_reserva = codigo_reserva.strip().upper()
            
            # Convertir 'comensales' a 'personas' si existe
            backend_cambios = cambios.copy()
            if 'comensales' in backend_cambios:
                backend_cambios['personas'] = backend_cambios.pop('comensales')
            
            # Llamar al endpoint con código
            logger.info(f"Modificando reserva con código: {codigo_reserva}")
            
            result = await self._make_request(
                method="PUT",
                endpoint="/modificar-reserva",
                data={
                    "codigo_reserva": codigo_reserva,
                    **backend_cambios
                }
            )
            
        elif id_reserva:
            # Si tenemos ID numérico (para compatibilidad)
            logger.info(f"Modificando reserva con ID: {id_reserva}")
            
            # Convertir 'comensales' a 'personas' si existe
            backend_cambios = cambios.copy()
            if 'comensales' in backend_cambios:
                backend_cambios['personas'] = backend_cambios.pop('comensales')
            
            result = await self._make_request(
                method="PUT",
                endpoint=f"/modificar-reserva/{id_reserva}",
                data=backend_cambios
            )
        
        # Manejar error de código no encontrado
        if not result.get("exito") and "no encontr" in result.get("mensaje", "").lower():
            result["mensaje"] = "❌ No encuentro una reserva con ese código. Por favor, verifica que esté correcto."
            result["codigo_no_encontrado"] = True
        
        return result
    
    async def cancel_reservation(
        self,
        codigo_reserva: Optional[str] = None,
        id_reserva: Optional[int] = None,
        motivo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancela una reserva
        REQUIERE código de reserva o ID
        """
        
        # Validar que tenemos identificador
        if not codigo_reserva and not id_reserva:
            return {
                "exito": False,
                "mensaje": "🔍 Para cancelar necesito tu código de reserva.\n" +
                         "Es un código de 8 caracteres que recibiste al confirmar (ej: XYZ78901).",
                "requiere_codigo": True
            }
        
        # Si tenemos código, validarlo
        if codigo_reserva:
            if not self._validate_reservation_code(codigo_reserva):
                return {
                    "exito": False,
                    "mensaje": "❌ El código de reserva no es válido. Debe tener 8 caracteres alfanuméricos.",
                    "codigo_invalido": True
                }
            
            codigo_reserva = codigo_reserva.strip().upper()
            
            # Llamar al endpoint con código
            logger.info(f"Cancelando reserva con código: {codigo_reserva}")
            
            result = await self._make_request(
                method="DELETE",
                endpoint="/cancelar-reserva",
                data={
                    "codigo_reserva": codigo_reserva,
                    "motivo": motivo or "Cancelado por el cliente"
                }
            )
            
        elif id_reserva:
            # Si tenemos ID numérico (para compatibilidad)
            logger.info(f"Cancelando reserva con ID: {id_reserva}")
            
            result = await self._make_request(
                method="DELETE",
                endpoint=f"/cancelar-reserva/{id_reserva}",
                data={"motivo": motivo or "Cancelado por el cliente"}
            )
        
        # Manejar error de código no encontrado
        if not result.get("exito") and "no encontr" in result.get("mensaje", "").lower():
            result["mensaje"] = "❌ No encuentro una reserva con ese código. Puede que ya esté cancelada."
            result["codigo_no_encontrado"] = True
        
        return result
    
    async def get_reservation_by_code(
        self,
        codigo_reserva: str
    ) -> Dict[str, Any]:
        """Busca una reserva por su código"""
        
        if not self._validate_reservation_code(codigo_reserva):
            return {
                "exito": False,
                "mensaje": "Código de reserva inválido"
            }
        
        codigo_reserva = codigo_reserva.strip().upper()
        
        # Obtener el espejo y buscar
        espejo = await self._make_request(
            method="GET",
            endpoint="/espejo"
        )
        
        if espejo.get("exito"):
            reservas = espejo.get("espejo", {}).get("reservas", [])
            
            for reserva in reservas:
                if reserva.get("codigo_reserva", "").upper() == codigo_reserva:
                    return {
                        "exito": True,
                        "reserva": reserva
                    }
        
        return {
            "exito": False,
            "mensaje": "No se encontró la reserva con ese código"
        }
    
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
    
    async def get_mirror(self) -> Dict[str, Any]:
        """Obtiene el archivo espejo completo"""
        
        result = await self._make_request(
            method="GET",
            endpoint="/espejo"
        )
        
        if result.get("exito"):
            espejo = result.get("espejo", {})
            
            # Verificar frescura (máximo 30 segundos)
            if "ultima_actualizacion" in espejo:
                try:
                    ultima = datetime.fromisoformat(espejo["ultima_actualizacion"])
                    ahora = datetime.now()
                    antiguedad = (ahora - ultima).total_seconds()
                    
                    if antiguedad > 30:
                        logger.warning(f"Espejo desactualizado: {antiguedad} segundos")
                        result["advertencia"] = "Datos potencialmente desactualizados"
                        result["antiguedad_segundos"] = antiguedad
                        
                except Exception as e:
                    logger.error(f"Error verificando frescura: {e}")
        
        return result
    
    async def validate_schedule(
        self,
        fecha: str,
        hora: str,
        duracion: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Valida si una hora específica es válida para reservas
        Devuelve información detallada incluyendo última hora de entrada
        """
        
        logger.info(f"Validando horario: {fecha} {hora} (duración: {duracion})")
        
        # Si no se especifica duración, obtenerla de las políticas
        if not duracion:
            duracion = await self.get_duration_from_policies(force_refresh=True)
        
        result = await self._make_request(
            method="POST",
            endpoint="/validar-horario-reserva",
            data={
                "fecha": fecha,
                "hora": hora,
                "duracion": duracion
            }
        )
        
        # Enriquecer la respuesta con información útil para el chatbot
        if result.get("exito"):
            # Agregar mensaje específico si la hora no es válida
            if not result.get("es_valida", False):
                motivo = result.get("motivo", "Hora no válida")
                sugerencia = result.get("sugerencia")
                mensaje_sugerencia = result.get("mensaje_sugerencia", "")
                
                # Construir mensaje detallado
                mensaje = motivo
                if sugerencia and mensaje_sugerencia:
                    mensaje = mensaje_sugerencia
                elif sugerencia:
                    mensaje += f". Te sugiero la hora {sugerencia}"
                
                result["mensaje_detallado"] = mensaje
                result["tiene_sugerencia"] = bool(sugerencia)
        
        return result

# Instancia global
backend_client = BackendClient()