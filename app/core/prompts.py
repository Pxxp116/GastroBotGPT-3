from typing import Dict, Any
from datetime import datetime
from app.core.config import settings

def get_system_prompt(conversation_state: Dict[str, Any]) -> str:
    """Genera el prompt del sistema basado en el estado actual"""
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    prompt = f"""Eres un asistente de reservas para GastroBot, un sistema profesional de gestión de reservas de restaurante.

INFORMACIÓN DEL SISTEMA:
- Fecha y hora actual: {current_time}
- Duración estándar de reserva: {settings.DEFAULT_DURATION_MIN} minutos
- Zona horaria: {settings.TIMEZONE}

PRINCIPIOS FUNDAMENTALES:
1. MANTENER CONTEXTO: No reiniciar flujos. Si el usuario ya proporcionó información, no volver a pedirla.
2. EFICIENCIA: Pedir solo los datos faltantes, no repetir preguntas.
3. VERDAD ABSOLUTA: Responder SOLO con datos del backend. Si algo no existe, decir "No consta en el sistema".
4. CONFIRMACIÓN: Antes de ejecutar crear/modificar/cancelar, resumir y pedir confirmación.

ESTADO ACTUAL DE LA CONVERSACIÓN:
- Intent detectado: {conversation_state.get('intent', 'No definido')}
- Campos completados: {conversation_state.get('filled_fields', {})}
- Campos faltantes: {conversation_state.get('missing_fields', [])}
- Reserva actual: {conversation_state.get('current_reservation', {})}

REGLAS DE INTERACCIÓN:
1. Tono cercano y profesional (máximo 2-3 frases por respuesta)
2. Si faltan datos obligatorios, pedirlos de forma natural
3. Si el usuario cambia algo (ej: "mejor a las 20:00"), actualizar sin repetir todo
4. Para confirmaciones, enmascarar datos sensibles (teléfono: ***1234)
5. Si no hay disponibilidad, ofrecer alternativas automáticamente

FLUJOS PRINCIPALES:

CREAR RESERVA:
- Necesarios: nombre, teléfono, fecha, hora, comensales
- Opcionales: zona, alergias, comentarios
- Proceso: verificar disponibilidad → confirmar datos → crear

MODIFICAR RESERVA:
- Identificar reserva (ID o datos del cliente)
- Preguntar qué cambiar
- Verificar disponibilidad si cambia fecha/hora
- Confirmar cambios → modificar

CANCELAR RESERVA:
- Identificar reserva
- Confirmar cancelación
- Ejecutar

CONSULTAS:
- Menú: mostrar categorías y platos con precios
- Horarios: mostrar horario del día solicitado
- Políticas: mostrar políticas relevantes

MANEJO DE ERRORES:
- Si el backend devuelve error, comunicarlo claramente
- Siempre ofrecer alternativas o siguiente paso
- No inventar información ni excusas

Recuerda: eres eficiente, preciso y mantienes el contexto de la conversación."""

    return prompt

def format_confirmation_message(action: str, data: Dict[str, Any]) -> str:
    """Formatea mensaje de confirmación antes de ejecutar acción"""
    
    if action == "crear":
        return f"""📝 Confirmo estos datos para tu reserva:
- Fecha: {data.get('fecha')}
- Hora: {data.get('hora')}
- Personas: {data.get('comensales')}
- Nombre: {data.get('nombre')}
- Zona: {data.get('zona', 'Sin preferencia')}
- Duración: {data.get('duracion_min', settings.DEFAULT_DURATION_MIN)} minutos

¿Confirmas la reserva?"""
    
    elif action == "modificar":
        return f"""✏️ Voy a modificar tu reserva con estos cambios:
{format_changes(data.get('cambios', {}))}

¿Confirmo los cambios?"""
    
    elif action == "cancelar":
        return f"""❌ Voy a cancelar la reserva de {data.get('nombre', 'tu reserva')}.

¿Confirmas la cancelación?"""
    
    return "¿Confirmas esta acción?"

def format_changes(changes: Dict[str, Any]) -> str:
    """Formatea los cambios para mostrar"""
    lines = []
    for key, value in changes.items():
        if value is not None:
            label = {
                "fecha": "• Nueva fecha",
                "hora": "• Nueva hora",
                "comensales": "• Número de personas",
                "zona": "• Zona",
                "alergias": "• Alergias"
            }.get(key, f"• {key.title()}")
            lines.append(f"{label}: {value}")
    
    return "\n".join(lines) if lines else "Sin cambios especificados"

def format_error_message(error: str) -> str:
    """Formatea mensaje de error para el usuario"""
    
    error_messages = {
        "timeout": "El sistema está tardando en responder. Por favor, intenta de nuevo en unos momentos.",
        "connection": "No puedo conectar con el sistema. Por favor, intenta más tarde.",
        "not_found": "No encuentro esa información en el sistema.",
        "invalid_data": "Los datos proporcionados no son válidos. Por favor, verifica la información.",
        "no_availability": "No hay disponibilidad para esa fecha y hora. ¿Te muestro alternativas?"
    }
    
    # Buscar mensaje personalizado
    for key, message in error_messages.items():
        if key in error.lower():
            return message
    
    # Mensaje genérico
    return "Ha ocurrido un error. Por favor, intenta de nuevo o contacta con el restaurante."

def format_alternatives(alternatives: list) -> str:
    """Formatea las alternativas disponibles"""
    
    if not alternatives:
        return "No hay alternativas disponibles cercanas a esa hora."
    
    lines = ["🕐 Horarios alternativos disponibles:"]
    for i, alt in enumerate(alternatives[:3], 1):
        lines.append(f"{i}. {alt['hora']} - Mesa para {alt['capacidad']} personas")
    
    return "\n".join(lines)