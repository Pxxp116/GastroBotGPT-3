from typing import Dict, Any, List, Optional  # ← AÑADE ESTA LÍNEA
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
                "name": "get_menu",
                "description": "Obtiene el menú completo del restaurante",
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
        if function_name == "check_availability":
            return await backend_client.check_availability(**arguments)
            
        elif function_name == "get_menu":
            return await backend_client.get_menu()
            
        elif function_name == "get_policies":
            return await backend_client.get_policies()
            
        else:
            return {"error": f"Función no reconocida: {function_name}"}
            
    except Exception as e:
        logger.error(f"Error ejecutando {function_name}: {e}")
        return {"error": str(e)}