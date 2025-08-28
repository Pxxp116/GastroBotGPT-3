"""
Definición y ejecución de herramientas para el chatbot
Versión corregida con manejo de códigos de reserva obligatorios
"""

from typing import Dict, Any, List
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

def get_tool_definitions() -> List[Dict[str, Any]]:
    """Define las herramientas disponibles para el asistente"""
    
    return [
        {
            "type": "function",
            "function": {
                "name": "check_availability",
                "description": "Verifica disponibilidad de mesas para una fecha y hora específica",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "fecha": {
                            "type": "string",
                            "description": "Fecha para verificar (YYYY-MM-DD)"
                        },
                        "hora": {
                            "type": "string",
                            "description": "Hora para verificar (HH:MM)"
                        },
                        "comensales": {
                            "type": "integer",
                            "description": "Número de personas",
                            "minimum": 1,
                            "maximum": 20
                        },
                        "duracion_min": {
                            "type": "integer",
                            "description": "Duración estimada en minutos",
                            "default": 120
                        }
                    },
                    "required": ["fecha", "hora", "comensales"],
                    "additionalProperties": False
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_reservation",
                "description": "Crea una nueva reserva en el sistema",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "nombre": {
                            "type": "string",
                            "description": "Nombre completo del cliente"
                        },
                        "telefono": {
                            "type": "string",
                            "description": "Teléfono del cliente"
                        },
                        "fecha": {
                            "type": "string",
                            "description": "Fecha de la reserva (YYYY-MM-DD)"
                        },
                        "hora": {
                            "type": "string",
                            "description": "Hora de la reserva (HH:MM)"
                        },
                        "comensales": {
                            "type": "integer",
                            "description": "Número de personas",
                            "minimum": 1,
                            "maximum": 20
                        },
                        "zona": {
                            "type": "string",
                            "description": "Zona preferida (terraza, salon, barra)"
                        },
                        "alergias": {
                            "type": "string",
                            "description": "Alergias o restricciones alimentarias"
                        },
                        "comentarios": {
                            "type": "string",
                            "description": "Comentarios adicionales"
                        }
                    },
                    "required": ["nombre", "telefono", "fecha", "hora", "comensales"],
                    "additionalProperties": False
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "modify_reservation",
                "description": "Modifica una reserva existente. REQUIERE el código de reserva obligatoriamente",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "codigo_reserva": {
                            "type": "string",
                            "description": "Código de reserva de 8 caracteres (OBLIGATORIO - siempre pedir al cliente)"
                        },
                        "cambios": {
                            "type": "object",
                            "properties": {
                                "fecha": {"type": "string", "description": "Nueva fecha (YYYY-MM-DD)"},
                                "hora": {"type": "string", "description": "Nueva hora (HH:MM)"},
                                "comensales": {"type": "integer", "description": "Nuevo número de personas"},
                                "zona": {"type": "string", "description": "Nueva zona preferida"},
                                "alergias": {"type": "string", "description": "Nuevas alergias"},
                                "comentarios": {"type": "string", "description": "Nuevos comentarios"}
                            },
                            "additionalProperties": False
                        }
                    },
                    "required": ["codigo_reserva", "cambios"],
                    "additionalProperties": False
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "cancel_reservation",
                "description": "Cancela una reserva existente. REQUIERE el código de reserva obligatoriamente",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "codigo_reserva": {
                            "type": "string",
                            "description": "Código de reserva de 8 caracteres (OBLIGATORIO - siempre pedir al cliente)"
                        },
                        "motivo": {
                            "type": "string",
                            "description": "Motivo de la cancelación (opcional)"
                        }
                    },
                    "required": ["codigo_reserva"],
                    "additionalProperties": False
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_reservation_info",
                "description": "Obtiene información de una reserva por su código",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "codigo_reserva": {
                            "type": "string",
                            "description": "Código de reserva de 8 caracteres"
                        }
                    },
                    "required": ["codigo_reserva"],
                    "additionalProperties": False
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_menu",
                "description": "Obtiene el menú del restaurante, con opción de incluir imágenes de los platos",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "categoria": {
                            "type": "string",
                            "description": "Categoría específica del menú (entrantes, principales, postres, bebidas)"
                        },
                        "mostrar_imagenes": {
                            "type": "boolean",
                            "description": "Si true, incluye las URLs de imágenes de los platos cuando estén disponibles. SOLO usar cuando el usuario pida explícitamente ver fotos/imágenes",
                            "default": False
                        },
                        "nombre_plato": {
                            "type": "string",
                            "description": "Nombre específico del plato para buscar su imagen (opcional, para búsquedas específicas)"
                        }
                    },
                    "additionalProperties": False
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_hours",
                "description": "Obtiene los horarios del restaurante",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "fecha": {
                            "type": "string",
                            "description": "Fecha específica (YYYY-MM-DD)"
                        }
                    },
                    "additionalProperties": False
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_policies",
                "description": "Obtiene las políticas del restaurante (cancelaciones, grupos, etc)",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_restaurant_info",
                "description": "Obtiene información específica del restaurante (nombre, políticas como fumadores, información general). USAR SIEMPRE antes de responder preguntas sobre el restaurante",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tipo_consulta": {
                            "type": "string",
                            "enum": ["general", "politicas"],
                            "description": "Tipo de información: 'general' para nombre/dirección/teléfono, 'politicas' para políticas específicas como fumadores"
                        },
                        "tipo_politica": {
                            "type": "string",
                            "description": "Para consultas de política específica: 'fumadores', 'cancelacion', 'ninos', 'mascotas', etc."
                        }
                    },
                    "required": ["tipo_consulta"],
                    "additionalProperties": False
                }
            }
        }
    ]

async def execute_tool_call(
    function_name: str,
    arguments: Dict[str, Any],
    conversation_state: Dict[str, Any]
) -> Dict[str, Any]:
    """Ejecuta una llamada a tool y devuelve el resultado"""
    
    logger.info(f"Ejecutando {function_name} con argumentos: {arguments}")
    
    try:
        # Importar backend_client aquí para evitar import circular
        from app.core.backend_client import backend_client
        
        if function_name == "check_availability":
            # Detectar verificaciones repetidas
            import time
            current_time = time.time()
            last_check = conversation_state.get("last_availability_check", {})
            
            # Si es la misma verificación en menos de 30 segundos, es probable un loop
            if (last_check.get("fecha") == arguments.get("fecha") and
                last_check.get("hora") == arguments.get("hora") and
                last_check.get("comensales") == arguments.get("comensales") and
                last_check.get("timestamp", 0) > current_time - 30):
                
                logger.warning(f"Verificación repetida detectada: {arguments}")
                # Añadir flag de advertencia
                conversation_state["repeated_check_warning"] = True
            
            # Guardar esta verificación
            conversation_state["last_availability_check"] = {
                "fecha": arguments.get("fecha"),
                "hora": arguments.get("hora"),
                "comensales": arguments.get("comensales"),
                "timestamp": current_time
            }
            
            result = await backend_client.check_availability(
                fecha=arguments.get("fecha"),
                hora=arguments.get("hora"),
                comensales=arguments.get("comensales")
            )
            
            # Si hay disponibilidad, marcar que estamos listos para crear
            if result.get("exito") and result.get("mesa_disponible"):
                conversation_state["ready_to_create"] = True
                conversation_state["pending_reservation_data"] = arguments
            
            return result
            
        elif function_name == "create_reservation":
            # Actualizar estado con los datos de la reserva
            for key, value in arguments.items():
                if value is not None:
                    conversation_state["filled_fields"] = conversation_state.get("filled_fields", {})
                    conversation_state["filled_fields"][key] = value
            
            # Limpiar flag de última verificación para evitar loops
            if "last_availability_check" in conversation_state:
                del conversation_state["last_availability_check"]
            
            result = await backend_client.create_reservation(
                nombre=arguments.get("nombre"),
                telefono=arguments.get("telefono"),
                fecha=arguments.get("fecha"),
                hora=arguments.get("hora"),
                comensales=arguments.get("comensales"),
                zona=arguments.get("zona"),
                alergias=arguments.get("alergias"),
                comentarios=arguments.get("comentarios")
            )
            
            if result.get("exito"):
                conversation_state["current_reservation"] = result.get("reserva", {})
                # Guardar código de reserva en el estado
                if result.get("codigo_reserva"):
                    conversation_state["last_reservation_code"] = result["codigo_reserva"]
                
            return result
            
        elif function_name == "modify_reservation":
            # Extraer código de reserva
            codigo_reserva = arguments.get("codigo_reserva")
            
            # Si no hay código, devolver error inmediato
            if not codigo_reserva:
                return {
                    "exito": False,
                    "mensaje": "📋 Para modificar tu reserva necesito tu código de confirmación.\nLo encuentras en el mensaje que recibiste al hacer la reserva (8 caracteres).",
                    "requiere_codigo": True
                }
            
            # Llamar al backend con el formato correcto
            result = await backend_client.modify_reservation(
                codigo_reserva=codigo_reserva,
                cambios=arguments.get("cambios", {})
            )
            
            if result.get("exito"):
                conversation_state["current_reservation"] = result.get("reserva", {})
                
            return result
            
        elif function_name == "cancel_reservation":
            # Extraer código de reserva
            codigo_reserva = arguments.get("codigo_reserva")
            
            # Si no hay código, devolver error inmediato
            if not codigo_reserva:
                return {
                    "exito": False,
                    "mensaje": "🔍 Para cancelar necesito tu código de reserva.\nEs un código de 8 caracteres que recibiste al confirmar (ej: XYZ78901).",
                    "requiere_codigo": True
                }
            
            # Llamar al backend con el formato correcto
            result = await backend_client.cancel_reservation(
                codigo_reserva=codigo_reserva,
                motivo=arguments.get("motivo")
            )
            
            if result.get("exito"):
                # Limpiar reserva actual del estado
                conversation_state["current_reservation"] = {}
                
            return result
            
        elif function_name == "get_reservation_info":
            codigo_reserva = arguments.get("codigo_reserva")
            
            if not codigo_reserva:
                return {
                    "exito": False,
                    "mensaje": "Necesito el código de reserva para buscar la información."
                }
            
            return await backend_client.get_reservation_by_code(codigo_reserva)
            
        elif function_name == "get_menu":
            return await backend_client.get_menu(
                categoria=arguments.get("categoria"),
                mostrar_imagenes=arguments.get("mostrar_imagenes", False),
                nombre_plato=arguments.get("nombre_plato")
            )
            
        elif function_name == "get_hours":
            return await backend_client.get_hours(
                fecha=arguments.get("fecha")
            )
            
        elif function_name == "get_policies":
            return await backend_client.get_policies()
        
        elif function_name == "get_restaurant_info":
            return await backend_client.get_restaurant_info(
                tipo_consulta=arguments.get("tipo_consulta", "general"),
                tipo_politica=arguments.get("tipo_politica")
            )
            
        else:
            return {
                "exito": False,
                "error": f"Función no reconocida: {function_name}",
                "mensaje": "Esta operación no está disponible"
            }
            
    except ImportError as e:
        logger.error(f"Error importando backend_client: {e}")
        return {
            "exito": False,
            "error": "Backend client no disponible",
            "mensaje": "El sistema de reservas no está disponible en este momento"
        }
    except TypeError as e:
        logger.error(f"Error de tipo en {function_name}: {e}", exc_info=True)
        return {
            "exito": False,
            "error": f"Error de parámetros: {str(e)}",
            "mensaje": "Ha ocurrido un error con los datos proporcionados"
        }
    except Exception as e:
        logger.error(f"Error ejecutando {function_name}: {e}", exc_info=True)
        return {
            "exito": False,
            "error": str(e),
            "mensaje": "Ha ocurrido un error procesando tu solicitud"
        }

def validate_tool_arguments(
    function_name: str,
    arguments: Dict[str, Any]
) -> tuple[bool, str]:
    """
    Valida los argumentos antes de ejecutar la herramienta
    Retorna (es_valido, mensaje_error)
    """
    
    if function_name == "modify_reservation":
        codigo = arguments.get("codigo_reserva")
        if not codigo:
            return False, "El código de reserva es obligatorio para modificar"
        if len(codigo.strip()) != 8:
            return False, "El código de reserva debe tener 8 caracteres"
        if not arguments.get("cambios"):
            return False, "Debe especificar qué desea modificar"
            
    elif function_name == "cancel_reservation":
        codigo = arguments.get("codigo_reserva")
        if not codigo:
            return False, "El código de reserva es obligatorio para cancelar"
        if len(codigo.strip()) != 8:
            return False, "El código de reserva debe tener 8 caracteres"
            
    elif function_name == "create_reservation":
        required = ["nombre", "telefono", "fecha", "hora", "comensales"]
        missing = [field for field in required if not arguments.get(field)]
        if missing:
            return False, f"Faltan datos obligatorios: {', '.join(missing)}"
            
    elif function_name == "check_availability":
        required = ["fecha", "hora", "comensales"]
        missing = [field for field in required if not arguments.get(field)]
        if missing:
            return False, f"Faltan datos para verificar disponibilidad: {', '.join(missing)}"
    
    return True, ""

def extract_reservation_code_from_message(message: str) -> str:
    """
    Intenta extraer un código de reserva del mensaje del usuario
    Busca patrones de 8 caracteres alfanuméricos
    """
    import re
    
    # Buscar patrón de 8 caracteres alfanuméricos
    pattern = r'\b[A-Z0-9]{8}\b'
    matches = re.findall(pattern, message.upper())
    
    if matches:
        return matches[0]
    
    return None