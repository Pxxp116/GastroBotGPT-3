from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, time
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

async def generate_alternative_slots(
    fecha: str,
    hora: str,
    comensales: int,
    duracion_min: int
) -> List[Dict[str, Any]]:
    """Genera slots alternativos cuando no hay disponibilidad"""
    
    alternatives = []
    
    try:
        # Parsear fecha y hora
        fecha_obj = datetime.strptime(fecha, "%Y-%m-%d")
        hora_obj = datetime.strptime(hora, "%H:%M").time()
        
        # Generar alternativas ±30 y ±60 minutos
        time_offsets = [-60, -30, 30, 60]
        
        for offset in time_offsets:
            # Calcular nueva hora
            new_datetime = datetime.combine(fecha_obj, hora_obj) + timedelta(minutes=offset)
            
            # Validar horario de apertura (ejemplo: 13:00 - 16:00 y 20:00 - 23:00)
            new_time = new_datetime.time()
            if is_valid_restaurant_time(new_time):
                alternatives.append({
                    "fecha": new_datetime.strftime("%Y-%m-%d"),
                    "hora": new_datetime.strftime("%H:%M"),
                    "capacidad": comensales,
                    "duracion": duracion_min,
                    "diferencia_minutos": offset
                })
        
    except Exception as e:
        logger.error(f"Error generando alternativas: {e}")
    
    return alternatives[:3]  # Máximo 3 alternativas

def is_valid_restaurant_time(check_time: time) -> bool:
    """Verifica si una hora está dentro del horario del restaurante"""
    
    # Horarios típicos (ajustar según configuración real)
    lunch_start = time(13, 0)
    lunch_end = time(16, 0)
    dinner_start = time(20, 0)
    dinner_end = time(23, 0)
    
    return (
        (lunch_start <= check_time <= lunch_end) or
        (dinner_start <= check_time <= dinner_end)
    )

def validate_reservation_data(data: Dict[str, Any]) -> tuple[bool, List[str]]:
    """Valida los datos de una reserva"""
    
    errors = []
    required_fields = ["nombre", "telefono", "fecha", "hora", "comensales"]
    
    # Verificar campos requeridos
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f"Falta el campo: {field}")
    
    # Validar formato de fecha
    if "fecha" in data:
        try:
            fecha = datetime.strptime(data["fecha"], "%Y-%m-%d")
            if fecha.date() < datetime.now().date():
                errors.append("La fecha no puede ser en el pasado")
        except ValueError:
            errors.append("Formato de fecha inválido (usar YYYY-MM-DD)")
    
    # Validar formato de hora
    if "hora" in data:
        try:
            datetime.strptime(data["hora"], "%H:%M")
        except ValueError:
            errors.append("Formato de hora inválido (usar HH:MM)")
    
    # Validar número de comensales
    if "comensales" in data:
        if not isinstance(data["comensales"], int) or data["comensales"] < 1 or data["comensales"] > 20:
            errors.append("Número de comensales debe ser entre 1 y 20")
    
    # Validar teléfono (básico)
    if "telefono" in data:
        telefono = str(data["telefono"]).strip()
        if len(telefono) < 9:
            errors.append("Teléfono inválido")
    
    return len(errors) == 0, errors

def extract_intent_from_message(message: str) -> Optional[str]:
    """Intenta extraer el intent del mensaje del usuario"""
    
    message_lower = message.lower()
    
    # Palabras clave para cada intent
    create_keywords = ["reservar", "reserva", "mesa para", "quiero una mesa", "hacer una reserva"]
    modify_keywords = ["cambiar", "modificar", "mover", "cambiar la reserva", "modificar reserva"]
    cancel_keywords = ["cancelar", "anular", "eliminar reserva", "quitar reserva"]
    menu_keywords = ["menú", "carta", "platos", "qué tienen", "comida", "bebidas"]
    hours_keywords = ["horario", "abierto", "cerrado", "qué hora", "horarios"]
    
    # Detectar intent
    for keyword in create_keywords:
        if keyword in message_lower:
            return "crear"
    
    for keyword in modify_keywords:
        if keyword in message_lower:
            return "modificar"
    
    for keyword in cancel_keywords:
        if keyword in message_lower:
            return "cancelar"
    
    for keyword in menu_keywords:
        if keyword in message_lower:
            return "consultar_menu"
    
    for keyword in hours_keywords:
        if keyword in message_lower:
            return "consultar_horario"
    
    return None

def mask_sensitive_data(text: str) -> str:
    """Enmascara datos sensibles en el texto"""
    
    import re
    
    # Enmascarar teléfonos (mantener últimos 4 dígitos)
    phone_pattern = r'\b(\d{3,})\d{4}\b'
    text = re.sub(phone_pattern, r'***\1', text)
    
    # Enmascarar emails
    email_pattern = r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    text = re.sub(email_pattern, r'***@\2', text)
    
    return text

def calculate_duration_from_guests(comensales: int) -> int:
    """Calcula duración estimada basada en número de comensales"""
    
    if comensales <= 2:
        return 90  # 1.5 horas para parejas
    elif comensales <= 4:
        return 120  # 2 horas para grupos pequeños
    elif comensales <= 8:
        return 150  # 2.5 horas para grupos medianos
    else:
        return 180  # 3 horas para grupos grandes