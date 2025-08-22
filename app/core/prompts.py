from typing import Dict, Any
from datetime import datetime
from app.core.config import settings

async def get_system_prompt(conversation_state: Dict[str, Any], backend_client=None) -> str:
    """Genera el prompt del sistema basado en el estado actual"""
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Obtener duración dinámica del backend si está disponible
    duration_min = settings.DEFAULT_DURATION_MIN  # Fallback
    if backend_client:
        try:
            duration_min = await backend_client.get_duration_from_policies(force_refresh=True)
        except Exception:
            pass  # Use fallback
    
    prompt = f"""Eres un asistente de reservas para GastroBot, un sistema profesional de gestión de reservas de restaurante.

INFORMACIÓN DEL SISTEMA:
- Fecha y hora actual: {current_time}
- Duración estándar de reserva: {duration_min} minutos
- Zona horaria: {settings.TIMEZONE}

PRINCIPIOS FUNDAMENTALES:
1. MANTENER CONTEXTO: No reiniciar flujos. Si el usuario ya proporcionó información, no volver a pedirla.
2. EFICIENCIA: Pedir solo los datos faltantes, no repetir preguntas.
3. VERDAD ABSOLUTA: Responder SOLO con datos del backend. Si algo no existe, decir "No consta en el sistema".
4. CONFIRMACIÓN: Antes de ejecutar crear/modificar/cancelar, resumir y pedir confirmación.
5. **IDENTIFICACIÓN OBLIGATORIA**: Para modificar o cancelar, SIEMPRE pedir primero el CÓDIGO DE RESERVA.

ESTADO ACTUAL DE LA CONVERSACIÓN:
- Intent detectado: {conversation_state.get('intent', 'No definido')}
- Campos completados: {conversation_state.get('filled_fields', {})}
- Campos faltantes: {conversation_state.get('missing_fields', [])}
- Reserva actual: {conversation_state.get('current_reservation', {})}

REGLAS DE INTERACCIÓN:
1. Tono cercano y profesional (máximo 2-3 frases por respuesta)
2. Si faltan datos obligatorios, pedirlos de forma natural
3. Si el usuario cambia algo (ej: "mejor a las 20:00"), actualizar sin repetir todo
4. Para confirmaciones, mostrar código de reserva claramente
5. Si no hay disponibilidad, ofrecer alternativas automáticamente

FLUJOS PRINCIPALES:

CREAR RESERVA:
- Necesarios: nombre, teléfono, fecha, hora, comensales
- Opcionales: zona, alergias, comentarios
- Proceso: verificar disponibilidad → confirmar datos → crear → PROPORCIONAR CÓDIGO

MODIFICAR RESERVA:
⚠️ REGLA CRÍTICA: SIEMPRE pedir primero el CÓDIGO DE RESERVA
- Diálogo correcto:
  Usuario: "Quiero modificar mi reserva"
  Asistente: "Por favor, proporciona tu código de reserva (lo encuentras en tu confirmación)"
  Usuario: "ABC123"
  Asistente: "Perfecto, ¿qué deseas modificar?"
- NUNCA intentar buscar por nombre/teléfono/fecha
- Si no tiene código: "Sin el código no puedo modificar tu reserva. ¿Tienes tu confirmación?"
- Verificar disponibilidad si cambia fecha/hora
- Confirmar cambios → modificar

CANCELAR RESERVA:
⚠️ REGLA CRÍTICA: SIEMPRE pedir primero el CÓDIGO DE RESERVA
- Diálogo correcto:
  Usuario: "Quiero cancelar mi reserva"
  Asistente: "Para cancelar necesito tu código de reserva"
  Usuario: "XYZ789"
  Asistente: "¿Confirmas que deseas cancelar la reserva XYZ789?"
- NUNCA intentar cancelar sin código
- Si no tiene código: "Necesito el código de tu reserva para cancelarla"
- Confirmar cancelación → ejecutar

CONSULTAS:
- Disponibilidad: verificar y mostrar opciones
- Menú: mostrar categorías y platos con precios
- Horarios: mostrar horario del día solicitado
- Políticas: mostrar políticas relevantes

MANEJO DE ERRORES Y SUGERENCIAS DE HORARIOS:
- Si el backend devuelve error, comunicarlo claramente
- Si no se encuentra reserva con el código: "No encuentro una reserva con ese código. Verifica que esté correcto"
- Siempre ofrecer alternativas o siguiente paso
- No inventar información ni excusas

⚠️ MANEJO ESPECIAL DE HORARIOS FUERA DE SERVICIO:
Cuando check_availability devuelve información sobre horarios no válidos:
- USA SIEMPRE los datos EXACTOS que devuelve el backend (duración, horarios, sugerencias)
- NUNCA uses ejemplos hardcodeados, usa los datos reales de la respuesta
- Si el backend devuelve mensaje_sugerencia, úsalo directamente
- Si hay sugerencia de hora alternativa, ofrécela como opción
- ESTRUCTURA recomendada:
  1. Explicar por qué no es válida la hora solicitada (usando datos reales)
  2. Ofrecer la alternativa sugerida por el sistema
  3. Preguntar si acepta la alternativa
- IMPORTANTE: Los datos de duración y horarios pueden cambiar dinámicamente
- NUNCA inventes horarios de cierre ni duraciones

FORMATO DE CÓDIGOS:
- Los códigos de reserva son alfanuméricos de 8 caracteres (ej: ABC12345)
- Siempre mostrarlos en MAYÚSCULAS
- En confirmaciones, destacarlos: "Tu código de reserva es: **ABC12345**"

Recuerda: 
- Para modificar/cancelar: CÓDIGO OBLIGATORIO, no buscar por otros datos
- Mantener contexto de la conversación
- Ser eficiente y preciso"""
    
    return prompt

async def format_confirmation_message(action: str, data: Dict[str, Any], backend_client=None) -> str:
    """Formatea mensaje de confirmación antes de ejecutar acción"""
    
    if action == "crear":
        # Obtener duración dinámica del backend si está disponible
        duration_min = settings.DEFAULT_DURATION_MIN  # Fallback
        if backend_client:
            try:
                duration_min = await backend_client.get_duration_from_policies(force_refresh=True)
            except Exception:
                pass  # Use fallback
        
        return f"""📝 Confirmo estos datos para tu reserva:
- Fecha: {data.get('fecha')}
- Hora: {data.get('hora')}
- Personas: {data.get('comensales')}
- Nombre: {data.get('nombre')}
- Teléfono: {mask_phone(data.get('telefono', ''))}
- Zona: {data.get('zona', 'Sin preferencia')}
- Duración: {data.get('duracion_min', duration_min)} minutos

¿Confirmas la reserva?"""
    
    elif action == "modificar":
        return f"""✏️ Voy a modificar tu reserva {data.get('codigo_reserva', '')} con estos cambios:
{format_changes(data.get('cambios', {}))}

¿Confirmo los cambios?"""
    
    elif action == "cancelar":
        return f"""❌ Voy a cancelar la reserva con código: {data.get('codigo_reserva', '')}

¿Confirmas la cancelación? (Esta acción no se puede deshacer)"""
    
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
                "alergias": "• Alergias",
                "comentarios": "• Comentarios"
            }.get(key, f"• {key.title()}")
            lines.append(f"{label}: {value}")
    
    return "\n".join(lines) if lines else "Sin cambios especificados"

def format_success_message(action: str, result: Dict[str, Any]) -> str:
    """Formatea mensaje de éxito después de ejecutar acción"""
    
    codigo = result.get('codigo_reserva', '')
    
    if action == "crear":
        return f"""✅ ¡Reserva confirmada!

**CÓDIGO DE RESERVA: {codigo}**
(Guarda este código para modificar o cancelar)

Detalles:
- Mesa {result.get('mesa', {}).get('numero', 'asignada')}
- {result.get('fecha')} a las {result.get('hora')}
- {result.get('personas')} personas

Te esperamos. ¡Gracias por tu reserva!"""
    
    elif action == "modificar":
        return f"""✅ Reserva modificada correctamente

Tu código sigue siendo: **{codigo}**

Nuevos datos confirmados:
{format_changes(result.get('cambios_realizados', {}))}"""
    
    elif action == "cancelar":
        return f"""✅ Reserva cancelada

La reserva {codigo} ha sido cancelada correctamente.
Esperamos verte pronto en otra ocasión."""
    
    return result.get('mensaje', 'Operación completada correctamente')

def format_error_message(error: str, context: str = None) -> str:
    """Formatea mensaje de error para el usuario"""
    
    error_messages = {
        "codigo_no_encontrado": "No encuentro una reserva con ese código. Por favor, verifica que esté correcto.",
        "sin_codigo": "Necesito tu código de reserva para continuar. Lo encuentras en tu confirmación.",
        "timeout": "El sistema está tardando en responder. Por favor, intenta de nuevo en unos momentos.",
        "connection": "No puedo conectar con el sistema. Por favor, intenta más tarde.",
        "not_found": "No encuentro esa información en el sistema.",
        "invalid_data": "Los datos proporcionados no son válidos. Por favor, verifica la información.",
        "no_availability": "No hay disponibilidad para esa fecha y hora. ¿Te muestro alternativas?",
        "invalid_code": "El código de reserva debe tener 8 caracteres. Ejemplo: ABC12345"
    }
    
    # Buscar mensaje personalizado
    for key, message in error_messages.items():
        if key in error.lower():
            return message
    
    # Mensaje según contexto
    if context == "modificar":
        return "Para modificar tu reserva necesito el código que recibiste al crearla."
    elif context == "cancelar":
        return "Para cancelar tu reserva necesito el código de confirmación."
    
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

def mask_phone(phone: str) -> str:
    """Enmascara el número de teléfono para privacidad"""
    if len(phone) < 4:
        return "***"
    return f"***{phone[-4:]}"

def validate_reservation_code(code: str) -> bool:
    """Valida el formato del código de reserva"""
    if not code:
        return False
    # Código debe ser alfanumérico de 8 caracteres
    code = code.strip().upper()
    return len(code) == 8 and code.isalnum()

def format_request_code_message(action: str) -> str:
    """Mensaje para solicitar código de reserva"""
    
    if action == "modificar":
        return """Para modificar tu reserva necesito tu código de confirmación.
Lo encuentras en el mensaje que recibiste al hacer la reserva (8 caracteres, ej: ABC12345)."""
    
    elif action == "cancelar":
        return """Para cancelar necesito tu código de reserva.
Es un código de 8 caracteres que recibiste al confirmar (ej: XYZ78901)."""
    
    return "Por favor, proporciona tu código de reserva (8 caracteres)."