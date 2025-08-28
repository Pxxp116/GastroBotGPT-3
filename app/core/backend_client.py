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

# Cache global para la duración - MÍNIMO para garantizar frescura
_duration_cache = {
    "value": 120,  # Valor por defecto inicial
    "timestamp": datetime.now() - timedelta(hours=24),  # Iniciar como expirado
    "ttl_minutes": 1  # Cache por solo 1 minuto para máxima frescura
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
        Obtiene la duración de reserva con cache mínimo para garantizar frescura
        SIEMPRE se debe usar la configuración más reciente del Dashboard
        
        Args:
            force_refresh: Si True, fuerza actualización del cache ignorando TTL
        """
        global _duration_cache
        
        # Cache muy corto (1 minuto) para garantizar datos frescos
        now = datetime.now()
        cache_age_seconds = (now - _duration_cache["timestamp"]).total_seconds() if _duration_cache["timestamp"] else float('inf')
        
        # Solo usar cache si es muy reciente (< 1 minuto) Y no se fuerza refresh
        if (not force_refresh and _duration_cache["value"] and 
            cache_age_seconds < 60):  # Solo 60 segundos de cache
            logger.info(f"[CACHE] Duración desde cache ({int(cache_age_seconds)}s antiguo): {_duration_cache['value']} minutos")
            return _duration_cache["value"]
        
        # Actualizar cache - siempre consultar BD para máxima frescura
        try:
            if force_refresh:
                logger.info("[FRESH] Forzando actualización de duración desde backend")
            else:
                logger.info(f"[FRESH] Cache expirado ({int(cache_age_seconds)}s), obteniendo duración desde backend")
            
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
                
                logger.info(f"[FRESH] Duración actualizada desde BD: {duracion} minutos (cache válido por 60s)")
                return duracion
            
            logger.warning("No se pudieron obtener políticas, usando cache o default")
            return _duration_cache["value"] or 120
            
        except Exception as e:
            logger.warning(f"Error obteniendo duración, usando cache o default: {e}")
            return _duration_cache["value"] or 120
    
    def invalidate_duration_cache(self):
        """Invalida el cache de duración forzando una actualización en la próxima consulta"""
        global _duration_cache
        _duration_cache["timestamp"] = datetime.now() - timedelta(hours=24)  # Forzar expiración inmediata
        logger.info("[CACHE] Cache de duración invalidado - próxima consulta obtendrá valor fresco")
    
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
        
        logger.info(f"[CHECK] Verificando disponibilidad: {fecha} {hora} para {comensales} personas")
        
        # CRÍTICO: Siempre obtener duración fresca para validaciones y sugerencias
        # Esto garantiza que las sugerencias usen la configuración actual del Dashboard
        duracion = await self.get_duration_from_policies(force_refresh=True)
        logger.info(f"[CHECK] Usando duración actualizada: {duracion} minutos")
        
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
        
        if not availability.get("exito"):
            # Error del backend (validación de horarios, etc.)
            logger.error(f"Error en check_availability: {availability.get('mensaje', 'Error desconocido')}")
            
            # Invalidar cache si el horario fue rechazado (podría indicar datos obsoletos)
            motivo = availability.get("mensaje", "")
            if "duración" in motivo.lower() or "terminaría después" in motivo.lower():
                logger.info("Invalidando cache por posible incompatibilidad de duración")
                self.invalidate_duration_cache()
            
            return {
                "exito": False,
                "mensaje": availability.get("mensaje", "Error al verificar disponibilidad"),
                "sugerencia": availability.get("sugerencia"),
                "alternativas": availability.get("alternativas", [])
            }
        
        if not availability.get("mesa_disponible"):
            # No hay mesa disponible - analizar el motivo y ofrecer alternativas claras
            logger.info(f"Sin mesa para {hora}, analizando alternativas y conflictos")
            
            alternativas = availability.get("alternativas", [])
            sugerencia_texto = availability.get("sugerencia", "")
            conflicto_detectado = availability.get("conflicto_detectado", False)
            detalles_conflicto = availability.get("detalles_conflicto", "")
            
            # Construir mensaje informativo basado en el tipo de problema
            if conflicto_detectado and detalles_conflicto:
                # Hay un conflicto específico identificado
                mensaje = f"❌ No puedo reservar a las {hora} porque hay un conflicto: {detalles_conflicto}"
            else:
                # Sin disponibilidad general
                mensaje = f"❌ Lo siento, no hay disponibilidad para {personas} personas el {fecha} a las {hora}"
            
            # Agregar información de horario si está fuera del rango válido
            horario_rest = availability.get("horario_restaurante", {})
            if horario_rest.get("ultima_entrada_calculada"):
                ultima_entrada = horario_rest["ultima_entrada_calculada"]
                duracion = horario_rest.get("duracion_reserva", 120)
                
                # Verificar si la hora solicitada es después de la última entrada
                [h_sol, m_sol] = hora.split(':')
                [h_ult, m_ult] = ultima_entrada.split(':')
                minutos_sol = int(h_sol) * 60 + int(m_sol)
                minutos_ult = int(h_ult) * 60 + int(m_ult)
                
                if minutos_sol > minutos_ult:
                    mensaje = f"❌ No puedo reservar a las {hora}. Con una duración de {duracion} minutos, la última hora de entrada es {ultima_entrada}"
            
            # Construir sugerencias mejoradas con información de liberación
            if alternativas and len(alternativas) > 0:
                # Ordenar por cercanía si tienen diferencia_minutos
                if alternativas[0].get("diferencia_minutos") is not None:
                    alternativas.sort(key=lambda x: x.get("diferencia_minutos", 999))
                
                primera = alternativas[0]
                hora_sugerida = primera.get("hora_alternativa") or primera.get("hora")
                mesas_disp = primera.get("mesas_disponibles", 1)
                es_liberacion = primera.get("es_liberacion_mesa", False)
                diferencia = primera.get("diferencia_minutos", 0)
                
                # MEJORADO: Mensaje específico según si es liberación de mesa
                if es_liberacion:
                    # Mesa se libera en ese momento
                    if diferencia <= 30:
                        mensaje += f"\n\n🔓 **La mesa se libera a las {hora_sugerida}** (justo cuando termina la reserva anterior)"
                    else:
                        mensaje += f"\n\n🔓 **Próxima mesa disponible a las {hora_sugerida}** (cuando se libera)"
                else:
                    # Mesa está libre en ese horario
                    if diferencia <= 30:
                        mensaje += f"\n\n✅ **Hay disponibilidad a las {hora_sugerida}** ({diferencia} minutos después)"
                    else:
                        mensaje += f"\n\n✅ Te sugiero las **{hora_sugerida}** (hay {mesas_disp} mesa{'s' if mesas_disp > 1 else ''} disponible{'s' if mesas_disp > 1 else ''})"
                
                # Añadir más opciones si hay
                if len(alternativas) > 1:
                    otras_opciones = []
                    for alt in alternativas[1:4]:  # Máximo 3 alternativas adicionales
                        h = alt.get("hora_alternativa") or alt.get("hora")
                        m = alt.get("mesas_disponibles", 1)
                        es_lib = alt.get("es_liberacion_mesa", False)
                        
                        if es_lib:
                            otras_opciones.append(f"{h} (se libera)")
                        else:
                            otras_opciones.append(f"{h} ({m} mesa{'s' if m > 1 else ''})")
                    
                    mensaje += f"\n\n📅 Otros horarios: {', '.join(otras_opciones)}"
                
                mensaje += "\n\n¿Te gustaría reservar en alguno de estos horarios?"
            else:
                # No hay alternativas en el día
                mensaje += "\n\n📅 No encuentro disponibilidad en este día. ¿Prefieres que busque en otro día?"
            
            return {
                "exito": False,
                "mensaje": mensaje,
                "sugerencia": sugerencia_texto,
                "alternativas": alternativas,
                "horario_rechazado": {
                    "fecha": fecha,
                    "hora": hora,
                    "motivo": detalles_conflicto if conflicto_detectado else "Sin mesas disponibles"
                },
                "tiene_alternativas": len(alternativas) > 0,
                "conflicto_detectado": conflicto_detectado,
                "detalles_conflicto": detalles_conflicto
            }
        
        # Obtener información de la mesa
        mesa_info = availability["mesa_disponible"]
        mesa_id = int(mesa_info.get("id", 1))
        
        # CRÍTICO: Obtener duración actualizada para la creación de reserva
        # Siempre usar la configuración más reciente del Dashboard
        duracion = await self.get_duration_from_policies(force_refresh=True)
        logger.info(f"[CREATE] Usando duración actualizada para crear reserva: {duracion} minutos")
        
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
            "zona_preferida": str(zona) if zona else "",
            "origen": "gpt"  # Identificar que la reserva viene del bot GPT
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
    
    async def get_menu(
        self, 
        categoria: Optional[str] = None,
        mostrar_imagenes: bool = False,
        nombre_plato: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtiene el menú del restaurante con opción de incluir imágenes
        
        Args:
            categoria: Categoría específica a filtrar
            mostrar_imagenes: Si True, incluye las URLs de imágenes cuando estén disponibles
            nombre_plato: Nombre específico del plato para buscar (útil para imágenes)
        """
        
        result = await self._make_request(
            method="GET",
            endpoint="/ver-menu"
        )
        
        if not result.get("exito"):
            return result
        
        menu = result.get("menu", {})
        categorias = menu.get("categorias", [])
        
        # Si se busca un plato específico
        if nombre_plato:
            plato_encontrado = None
            categoria_plato = None
            
            for cat in categorias:
                platos = cat.get("platos", [])
                for plato in platos:
                    # Búsqueda flexible por nombre
                    if nombre_plato.lower() in plato.get("nombre", "").lower():
                        plato_encontrado = plato
                        categoria_plato = cat.get("nombre")
                        break
                if plato_encontrado:
                    break
            
            if plato_encontrado:
                # Validar que la URL de imagen sea válida (no blob:, data:, etc.)
                imagen_url = plato_encontrado.get("imagen_url", "")
                es_url_valida = (
                    imagen_url and 
                    not imagen_url.startswith("blob:") and 
                    not imagen_url.startswith("data:") and
                    (imagen_url.startswith("http://") or imagen_url.startswith("https://"))
                )
                
                # Si se pidieron imágenes y el plato tiene imagen válida
                if mostrar_imagenes and es_url_valida:
                    result["plato_con_imagen"] = {
                        "nombre": plato_encontrado["nombre"],
                        "descripcion": plato_encontrado.get("descripcion", ""),
                        "precio": plato_encontrado.get("precio"),
                        "categoria": categoria_plato,
                        "imagen_url": imagen_url,
                        "tiene_imagen": True
                    }
                else:
                    result["plato_con_imagen"] = {
                        "nombre": plato_encontrado["nombre"],
                        "descripcion": plato_encontrado.get("descripcion", ""),
                        "precio": plato_encontrado.get("precio"),
                        "categoria": categoria_plato,
                        "tiene_imagen": False,
                        "mensaje": f"Lo siento, no hay una imagen disponible de {plato_encontrado['nombre']} en este momento. Te puedo ayudar con la descripción: {plato_encontrado.get('descripcion', 'Plato de nuestra carta')}"
                    }
            else:
                result["mensaje"] = f"No se encontró el plato '{nombre_plato}'"
                result["plato_con_imagen"] = None
        
        # Filtrar por categoría si se especifica
        if categoria:
            categoria_filtrada = None
            for cat in categorias:
                if cat.get("nombre", "").lower() == categoria.lower():
                    categoria_filtrada = cat
                    break
            
            if categoria_filtrada:
                categorias = [categoria_filtrada]
            else:
                result["mensaje"] = f"No se encontró la categoría '{categoria}'"
                return result
        
        # Si se pidieron imágenes, filtrar solo platos con imagen_url válida
        if mostrar_imagenes:
            platos_con_imagen = []
            for cat in categorias:
                platos = cat.get("platos", [])
                for plato in platos:
                    imagen_url = plato.get("imagen_url", "")
                    # Validar que sea una URL HTTP/HTTPS válida
                    if (imagen_url and 
                        not imagen_url.startswith("blob:") and 
                        not imagen_url.startswith("data:") and
                        (imagen_url.startswith("http://") or imagen_url.startswith("https://"))):
                        platos_con_imagen.append({
                            "nombre": plato["nombre"],
                            "descripcion": plato.get("descripcion", ""),
                            "precio": plato.get("precio"),
                            "categoria": cat.get("nombre"),
                            "imagen_url": imagen_url
                        })
            
            result["platos_con_imagen"] = platos_con_imagen[:5]  # Límite de 5 para WhatsApp
            result["total_con_imagen"] = len(platos_con_imagen)
            
            if not platos_con_imagen:
                result["mensaje"] = "No hay imágenes disponibles para los platos en este momento"
        
        result["menu"] = {"categorias": categorias}
        return result
    
    async def get_dish_image(self, nombre_plato: str) -> Dict[str, Any]:
        """
        Busca la imagen de un plato específico
        
        Args:
            nombre_plato: Nombre del plato a buscar
            
        Returns:
            Diccionario con información del plato e imagen si está disponible
        """
        
        # Usar get_menu con los parámetros adecuados
        result = await self.get_menu(
            mostrar_imagenes=True,
            nombre_plato=nombre_plato
        )
        
        if result.get("plato_con_imagen"):
            return {
                "exito": True,
                "plato": result["plato_con_imagen"]
            }
        else:
            return {
                "exito": False,
                "mensaje": result.get("mensaje", f"No se encontró el plato '{nombre_plato}'")
            }
    
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
    
    async def get_restaurant_info(
        self,
        tipo_consulta: str = "general",
        tipo_politica: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtiene información del restaurante con fallback automático
        
        Args:
            tipo_consulta: 'general' para info básica, 'politicas' para políticas específicas
            tipo_politica: tipo específico de política (ej: 'fumadores')
        """
        
        logger.info(f"Consultando información del restaurante: {tipo_consulta}, política: {tipo_politica}")
        
        # Endpoint principal según el tipo de consulta
        endpoint_principal = "/admin/restaurante" if tipo_consulta == "general" else "/admin/politicas"
        usa_fallback = False
        
        try:
            # Intentar endpoint principal primero
            logger.info(f"[RESTAURANT_INFO] Consultando endpoint principal: {endpoint_principal}")
            result = await self._make_request(
                method="GET",
                endpoint=endpoint_principal
            )
            
            # Si el endpoint principal falla o devuelve 404, usar espejo
            if not result.get("exito") or "404" in str(result.get("mensaje", "")):
                logger.warning(f"[RESTAURANT_INFO] Endpoint principal falló, usando espejo como fallback")
                usa_fallback = True
                
                # Obtener datos del espejo
                espejo_result = await self._make_request(
                    method="GET",
                    endpoint="/espejo"
                )
                
                if espejo_result.get("exito"):
                    espejo_data = espejo_result.get("espejo", {})
                    
                    if tipo_consulta == "general":
                        # Información general del restaurante
                        restaurante = espejo_data.get("restaurante", {})
                        result = {
                            "exito": True,
                            "restaurante": restaurante,
                            "fuente": "espejo",
                            "fallback_usado": True
                        }
                    elif tipo_consulta == "politicas":
                        # Políticas del restaurante
                        politicas = espejo_data.get("politicas", {})
                        result = {
                            "exito": True,
                            "politicas": politicas,
                            "fuente": "espejo", 
                            "fallback_usado": True
                        }
                else:
                    logger.error("[RESTAURANT_INFO] Tanto endpoint principal como espejo fallaron")
                    return {
                        "exito": False,
                        "mensaje": "No se pudo obtener información del restaurante en este momento",
                        "error_tipo": "system_unavailable"
                    }
            else:
                # Endpoint principal exitoso
                result["fuente"] = "principal"
                result["fallback_usado"] = False
        
        except Exception as e:
            logger.error(f"[RESTAURANT_INFO] Error consultando información: {e}")
            return {
                "exito": False,
                "mensaje": "Error al consultar información del restaurante",
                "error": str(e)
            }
        
        # Procesar y formatear la respuesta según el tipo de consulta
        if result.get("exito"):
            if tipo_consulta == "general":
                # Extraer información general
                restaurante = result.get("restaurante", {})
                info_formateada = {
                    "nombre": restaurante.get("nombre", ""),
                    "telefono": restaurante.get("telefono", ""),
                    "direccion": restaurante.get("direccion", ""),
                    "email": restaurante.get("email", ""),
                    "web": restaurante.get("web", restaurante.get("sitio_web", "")),
                    "tipo_cocina": restaurante.get("tipo_cocina", ""),
                    "descripcion": restaurante.get("descripcion", "")
                }
                
                # Log de fallback si aplica
                if usa_fallback:
                    logger.warning(f"[RESTAURANT_INFO] Información obtenida del espejo (fallback): {info_formateada.get('nombre', 'Sin nombre')}")
                else:
                    logger.info(f"[RESTAURANT_INFO] Información obtenida del endpoint principal: {info_formateada.get('nombre', 'Sin nombre')}")
                
                return {
                    "exito": True,
                    "informacion": info_formateada,
                    "fuente": result.get("fuente"),
                    "fallback_usado": usa_fallback
                }
                
            elif tipo_consulta == "politicas":
                # Extraer políticas específicas
                politicas = result.get("politicas", {})
                
                if tipo_politica:
                    # Consulta específica de política
                    if tipo_politica == "fumadores":
                        fumadores_permitidos = politicas.get("fumadores_terraza", None)
                        if fumadores_permitidos is not None:
                            politica_info = {
                                "tipo": "fumadores",
                                "permitido": bool(fumadores_permitidos),
                                "detalles": "Se permite fumar en la terraza" if fumadores_permitidos else "No se permite fumar"
                            }
                        else:
                            politica_info = {
                                "tipo": "fumadores",
                                "permitido": None,
                                "detalles": "Política de fumadores no configurada"
                            }
                    else:
                        # Otras políticas
                        politica_info = {
                            "tipo": tipo_politica,
                            "valor": politicas.get(tipo_politica),
                            "detalles": f"Información sobre {tipo_politica}"
                        }
                    
                    # Log de fallback si aplica
                    if usa_fallback:
                        logger.warning(f"[RESTAURANT_INFO] Política {tipo_politica} obtenida del espejo (fallback): {politica_info}")
                    else:
                        logger.info(f"[RESTAURANT_INFO] Política {tipo_politica} obtenida del endpoint principal: {politica_info}")
                    
                    return {
                        "exito": True,
                        "politica": politica_info,
                        "fuente": result.get("fuente"),
                        "fallback_usado": usa_fallback
                    }
                else:
                    # Todas las políticas
                    logger.info(f"[RESTAURANT_INFO] Todas las políticas obtenidas de {'espejo' if usa_fallback else 'endpoint principal'}")
                    return {
                        "exito": True,
                        "politicas": politicas,
                        "fuente": result.get("fuente"),
                        "fallback_usado": usa_fallback
                    }
        
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
        
        # CRÍTICO: Siempre obtener duración actualizada para validaciones
        if not duracion:
            duracion = await self.get_duration_from_policies(force_refresh=True)
            logger.info(f"[VALIDATE] Obtenida duración fresca para validación: {duracion} minutos")
        
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