from typing import Dict, Any, List, Optional
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

def get_tool_definitions() -> List[Dict[str, Any]]:
    """Devuelve las definiciones de tools para OpenAI"""
    return [
        {
            "type": "function",
            "function": {
                "name": "check_availability",
                "description": "Verifica disponibilidad de mesas para una fecha y hora específicas",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "fecha": {
                            "type": "string",
                            "description": "Fecha en formato YYYY-MM-DD"
                        },
                        "hora": {
                            "type": "string",
                            "description": "Hora en formato HH:MM"
                        },
                        "comensales": {
                            "type": "integer",
                            "description": "Número de personas",
                            "minimum": 1,
                            "maximum": 20
                        },
                        "duracion_min": {
                            "type": "integer",
                            "description": "Duración de la reserva en minutos",
                            "default": 90
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
                            "description": "Nombre del cliente"
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
                "description": "Modifica una reserva existente",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "id_reserva": {
                            "type": "integer",
                            "description": "ID de la reserva a modificar"
                        },
                        "nombre": {
                            "type": "string",
                            "description": "Nombre del cliente (para buscar si no hay ID)"
                        },
                        "telefono": {
                            "type": "string",
                            "description": "Teléfono del cliente (para buscar si no hay ID)"
                        },
                        "fecha_antigua": {
                            "type": "string",
                            "description": "Fecha original de la reserva"
                        },
                        "hora_antigua": {
                            "type": "string",
                            "description": "Hora original de la reserva"
                        },
                        "cambios": {
                            "type": "object",
                            "properties": {
                                "fecha": {"type": "string"},
                                "hora": {"type": "string"},
                                "comensales": {"type": "integer"},
                                "zona": {"type": "string"},
                                "alergias": {"type": "string"},
                                "comentarios": {"type": "string"}
                            },
                            "additionalProperties": False
                        }
                    },
                    "required": ["cambios"],
                    "additionalProperties": False
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "cancel_reservation",
                "description": "Cancela una reserva existente",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "id_reserva": {
                            "type": "integer",
                            "description": "ID de la reserva"
                        },
                        "nombre": {
                            "type": "string",
                            "description": "Nombre del cliente"
                        },
                        "telefono": {
                            "type": "string",
                            "description": "Teléfono del cliente"
                        },
                        "fecha": {
                            "type": "string",
                            "description": "Fecha de la reserva"
                        },
                        "hora": {
                            "type": "string",
                            "description": "Hora de la reserva"
                        },
                        "motivo": {
                            "type": "string",
                            "description": "Motivo de la cancelación"
                        }
                    },
                    "additionalProperties": False
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_menu",
                "description": "Obtiene el menú completo del restaurante",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "categoria": {
                            "type": "string",
                            "description": "Categoría específica del menú"
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
                "description": "Obtiene las políticas del restaurante",
                "parameters": {
                    "type": "object",
                    "properties": {},
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
            return await backend_client.check_availability(
                fecha=arguments.get("fecha"),
                hora=arguments.get("hora"),
                comensales=arguments.get("comensales"),
                duracion_min=arguments.get("duracion_min", settings.DEFAULT_DURATION_MIN)
            )
            
        elif function_name == "create_reservation":
            # Actualizar estado con los datos de la reserva
            for key, value in arguments.items():
                if value is not None:
                    conversation_state["filled_fields"] = conversation_state.get("filled_fields", {})
                    conversation_state["filled_fields"][key] = value
            
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
                
            return result
            
        elif function_name == "modify_reservation":
            result = await backend_client.modify_reservation(
                id_reserva=arguments.get("id_reserva"),
                nombre=arguments.get("nombre"),
                telefono=arguments.get("telefono"),
                fecha_antigua=arguments.get("fecha_antigua"),
                hora_antigua=arguments.get("hora_antigua"),
                cambios=arguments.get("cambios", {})
            )
            
            if result.get("exito"):
                conversation_state["current_reservation"] = result.get("reserva", {})
                
            return result
            
        elif function_name == "cancel_reservation":
            return await backend_client.cancel_reservation(
                id_reserva=arguments.get("id_reserva"),
                nombre=arguments.get("nombre"),
                telefono=arguments.get("telefono"),
                fecha=arguments.get("fecha"),
                hora=arguments.get("hora"),
                motivo=arguments.get("motivo")
            )
            
        elif function_name == "get_menu":
            return await backend_client.get_menu(
                categoria=arguments.get("categoria")
            )
            
        elif function_name == "get_hours":
            return await backend_client.get_hours(
                fecha=arguments.get("fecha")
            )
            
        elif function_name == "get_policies":
            return await backend_client.get_policies()
            
        else:
            return {
                "exito": False,
                "error": f"Función no reconocida: {function_name}"
            }
            
    except ImportError as e:
        logger.error(f"Error importando backend_client: {e}")
        return {
            "exito": False,
            "error": "Backend client no disponible",
            "mensaje": "El sistema de reservas no está disponible en este momento"
        }
    except Exception as e:
        logger.error(f"Error ejecutando {function_name}: {e}", exc_info=True)
        return {
            "exito": False,
            "error": str(e),
            "mensaje": "Ha ocurrido un error procesando tu solicitud"
        }