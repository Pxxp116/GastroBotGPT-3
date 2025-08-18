from typing import Dict, Any, List
import logging
from app.core.backend_client import backend_client
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
                            "default": settings.DEFAULT_DURATION_MIN
                        }
                    },
                    "required": ["fecha", "hora", "comensales"],
                    "additionalProperties": False
                },
                "strict": True
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
                            "type": ["string", "null"],
                            "description": "Zona preferida (terraza, salon, barra)",
                            "enum": ["terraza", "salon", "barra", null]
                        },
                        "alergias": {
                            "type": ["string", "null"],
                            "description": "Alergias o restricciones alimentarias"
                        },
                        "comentarios": {
                            "type": ["string", "null"],
                            "description": "Comentarios adicionales"
                        }
                    },
                    "required": ["nombre", "telefono", "fecha", "hora", "comensales"],
                    "additionalProperties": False
                },
                "strict": True
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
                            "type": ["integer", "null"],
                            "description": "ID de la reserva a modificar"
                        },
                        "nombre": {
                            "type": ["string", "null"],
                            "description": "Nombre del cliente (para buscar si no hay ID)"
                        },
                        "telefono": {
                            "type": ["string", "null"],
                            "description": "Teléfono del cliente (para buscar si no hay ID)"
                        },
                        "fecha_antigua": {
                            "type": ["string", "null"],
                            "description": "Fecha original de la reserva"
                        },
                        "hora_antigua": {
                            "type": ["string", "null"],
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
                },
                "strict": True
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
                            "type": ["integer", "null"],
                            "description": "ID de la reserva"
                        },
                        "nombre": {
                            "type": ["string", "null"],
                            "description": "Nombre del cliente"
                        },
                        "telefono": {
                            "type": ["string", "null"],
                            "description": "Teléfono del cliente"
                        },
                        "fecha": {
                            "type": ["string", "null"],
                            "description": "Fecha de la reserva"
                        },
                        "hora": {
                            "type": ["string", "null"],
                            "description": "Hora de la reserva"
                        },
                        "motivo": {
                            "type": ["string", "null"],
                            "description": "Motivo de la cancelación"
                        }
                    },
                    "additionalProperties": False
                },
                "strict": True
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
                            "type": ["string", "null"],
                            "description": "Categoría específica del menú"
                        }
                    },
                    "additionalProperties": False
                },
                "strict": True
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
                            "type": ["string", "null"],
                            "description": "Fecha específica (YYYY-MM-DD)"
                        }
                    },
                    "additionalProperties": False
                },
                "strict": True
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
                },
                "strict": True
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
        if function_name == "check_availability":
            return await backend_client.check_availability(**arguments)
            
        elif function_name == "create_reservation":
            # Actualizar estado con los datos de la reserva
            for key, value in arguments.items():
                if value is not None:
                    conversation_state.filled_fields[key] = value
            
            result = await backend_client.create_reservation(**arguments)
            
            if result.get("exito"):
                conversation_state.current_reservation = result.get("reserva", {})
                
            return result
            
        elif function_name == "modify_reservation":
            result = await backend_client.modify_reservation(**arguments)
            
            if result.get("exito"):
                conversation_state.current_reservation = result.get("reserva", {})
                
            return result
            
        elif function_name == "cancel_reservation":
            return await backend_client.cancel_reservation(**arguments)
            
        elif function_name == "get_menu":
            return await backend_client.get_menu(**arguments)
            
        elif function_name == "get_hours":
            return await backend_client.get_hours(**arguments)
            
        elif function_name == "get_policies":
            return await backend_client.get_policies()
            
        else:
            return {"error": f"Función no reconocida: {function_name}"}
            
    except Exception as e:
        logger.error(f"Error ejecutando {function_name}: {e}")
        return {"error": str(e)}