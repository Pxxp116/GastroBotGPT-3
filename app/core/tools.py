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
                            "description": "Zona preferida (terraza, salon, barra)",
                            "enum": ["terraza", "salon", "barra"],
                            "default": None
                        },
                        "alergias": {
                            "type": "string",
                            "description": "Alergias o restricciones alimentarias",
                            "default": None
                        },
                        "comentarios": {
                            "type": "string",
                            "description": "Comentarios adicionales",
                            "default": None
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
                "name": "get_menu",
                "description": "Obtiene el menú completo del restaurante",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "categoria": {
                            "type": "string",
                            "description": "Categoría específica del menú",
                            "default": None
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
                            "description": "Fecha específica (YYYY-MM-DD)",
                            "default": None
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