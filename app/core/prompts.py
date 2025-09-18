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
    
    # Sanitizar variables para evitar errores de formato
    safe_current_time = str(current_time) if current_time else 'No definido'
    safe_duration_min = str(duration_min) if duration_min else '120'
    safe_timezone = str(settings.TIMEZONE) if settings.TIMEZONE else 'Europe/Madrid'
    
    # Sanitizar valores del conversation_state
    safe_intent = str(conversation_state.get('intent', 'No definido'))
    safe_filled_fields = str(conversation_state.get('filled_fields', {}))
    safe_missing_fields = str(conversation_state.get('missing_fields', []))
    safe_current_reservation = str(conversation_state.get('current_reservation', {}))
    safe_ready_to_create = str(conversation_state.get('ready_to_create', False))
    safe_repeated_check = str(conversation_state.get('repeated_check_warning', False))
    
    # Construir prompt usando concatenación segura en lugar de f-string
    prompt = "Eres un asistente inteligente para GastroBot, un sistema profesional de gestión de restaurantes que maneja reservas Y PEDIDOS.\n\n"
    
    prompt += "INFORMACIÓN DEL SISTEMA:\n"
    prompt += "- Fecha y hora actual: " + safe_current_time + "\n"
    prompt += "- Duración estándar de reserva: " + safe_duration_min + " minutos\n"
    prompt += "- Zona horaria: " + safe_timezone + "\n\n"
    
    prompt += "PRINCIPIOS FUNDAMENTALES:\n"
    prompt += "1. MANTENER CONTEXTO: No reiniciar flujos. Si el usuario ya proporcionó información, no volver a pedirla.\n"
    prompt += "2. EFICIENCIA: Pedir solo los datos faltantes, no repetir preguntas.\n"
    prompt += "3. VERDAD ABSOLUTA: Responder SOLO con datos del backend. Si algo no existe, decir \"No consta en el sistema\".\n"
    prompt += "4. CONFIRMACIÓN: Antes de ejecutar crear/modificar/cancelar, resumir y pedir confirmación.\n"
    prompt += "5. **IDENTIFICACIÓN OBLIGATORIA**: Para modificar o cancelar, SIEMPRE pedir primero el CÓDIGO DE RESERVA.\n\n"
    
    prompt += "ESTADO ACTUAL DE LA CONVERSACIÓN:\n"
    prompt += "- Intent detectado: " + safe_intent + "\n"
    prompt += "- Campos completados: " + safe_filled_fields + "\n"
    prompt += "- Campos faltantes: " + safe_missing_fields + "\n"
    prompt += "- Reserva actual: " + safe_current_reservation + "\n"
    prompt += "- Listo para crear: " + safe_ready_to_create + "\n"
    prompt += "- Advertencia verificación repetida: " + safe_repeated_check + "\n\n"
    
    prompt += "REGLAS DE INTERACCIÓN:\n"
    prompt += "1. Tono cercano y profesional (máximo 2-3 frases por respuesta)\n"
    prompt += "2. Si faltan datos obligatorios, pedirlos de forma natural\n"
    prompt += "3. Para confirmaciones, mostrar código de reserva claramente\n"
    prompt += "4. Si no hay disponibilidad, ofrecer alternativas automáticamente\n\n"
    
    prompt += "REGLAS CRÍTICAS:\n"
    prompt += "- ANTES de decir que no hay disponibilidad → USAR check_availability\n"
    prompt += "- ANTES de responder sobre información del restaurante → USAR get_restaurant_info\n"
    prompt += "- NUNCA hagas suposiciones sobre disponibilidad sin verificar\n\n"
    
    prompt += "FLUJO DE RESERVA:\n"
    prompt += "1. Recopilar datos: nombre, teléfono, fecha, hora, comensales\n"
    prompt += "2. Verificar disponibilidad con check_availability\n"
    prompt += "3. Si confirma → LLAMAR create_reservation\n\n"

    prompt += "FLUJO DE PEDIDOS:\n"
    prompt += "1. Cuando el cliente quiera pedir comida → USAR get_menu para mostrar opciones\n"
    prompt += "2. Recopilar: nombre cliente, teléfono, platos con cantidades\n"
    prompt += "3. Calcular total (suma de precio_unitario * cantidad)\n"
    prompt += "4. Confirmar pedido con el cliente\n"
    prompt += "5. Si confirma → LLAMAR create_order\n"
    prompt += "6. Proporcionar ID único del pedido (8 caracteres)\n\n"

    prompt += "CÓDIGOS:\n"
    prompt += "- Reservas: Alfanuméricos 8 caracteres (ABC12345)\n"
    prompt += "- Pedidos: Alfanuméricos 8 caracteres (PED12ABC)\n"
    prompt += "Para modificar/cancelar: CÓDIGO OBLIGATORIO\n\n"

    prompt += "IMPORTANTE PARA PEDIDOS:\n"
    prompt += "- Siempre mostrar el menú primero con get_menu\n"
    prompt += "- Confirmar cada plato con su precio antes de proceder\n"
    prompt += "- Calcular y mostrar el total antes de confirmar\n"
    prompt += "- Proporcionar el ID único del pedido al finalizar\n"
    prompt += "- Estados del pedido: pendiente → en_preparacion → entregado\n\n"

    prompt += "Mantener contexto y ser eficiente."
    
    return prompt

async def format_confirmation_message(action: str, data: Dict[str, Any], backend_client=None) -> str:
    """Formatea mensaje de confirmación antes de ejecutar acción"""

    if action == "crear_pedido":
        nombre = data.get('cliente_nombre', '')
        telefono = mask_phone(data.get('cliente_telefono', ''))
        detalles = data.get('detalles_pedido', [])
        total = data.get('total', 0)

        mensaje = f"""🛒 Confirmo estos datos para tu pedido:
- Cliente: {nombre}
- Teléfono: {telefono}

📋 Detalle del pedido:"""

        for item in detalles:
            plato = item.get('plato', '')
            cantidad = item.get('cantidad', 0)
            precio = item.get('precio_unitario', 0)
            subtotal = cantidad * precio
            mensaje += f"\n  • {cantidad}x {plato} - €{precio:.2f} c/u = €{subtotal:.2f}"

        mensaje += f"\n\n💰 TOTAL: €{total:.2f}"
        mensaje += "\n\n¿Confirmas tu pedido? Responde SÍ para procesar."

        return mensaje

    elif action == "crear":
        # Obtener duración dinámica del backend si está disponible
        duration_min = settings.DEFAULT_DURATION_MIN  # Fallback
        if backend_client:
            try:
                duration_min = await backend_client.get_duration_from_policies(force_refresh=True)
            except Exception:
                pass  # Use fallback
        
        # Sanitizar datos para evitar errores de formato
        fecha = data.get('fecha', '')
        hora = data.get('hora', '')
        comensales = data.get('comensales', '')
        nombre = data.get('nombre', '')
        telefono = mask_phone(data.get('telefono', ''))
        zona = data.get('zona', 'Sin preferencia')
        duracion = data.get('duracion_min', duration_min)
        
        return f"""📝 Confirmo estos datos para tu reserva:
- Fecha: {fecha}
- Hora: {hora}
- Personas: {comensales}
- Nombre: {nombre}
- Teléfono: {telefono}
- Zona: {zona}
- Duración: {duracion} minutos

¿Confirmas la reserva?"""
    
    elif action == "modificar":
        codigo_reserva = data.get('codigo_reserva', '')
        cambios = format_changes(data.get('cambios', {}))
        return f"""✏️ Voy a modificar tu reserva {codigo_reserva} con estos cambios:
{cambios}

¿Confirmo los cambios?"""
    
    elif action == "cancelar":
        codigo_reserva = data.get('codigo_reserva', '')
        return f"""❌ Voy a cancelar la reserva con código: {codigo_reserva}

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
        mesa_info = result.get('mesa', {})
        mesa_numero = mesa_info.get('numero', 'asignada') if isinstance(mesa_info, dict) else 'asignada'
        fecha = result.get('fecha', '')
        hora = result.get('hora', '')  
        personas = result.get('personas', '')
        
        return f"""✅ ¡Reserva confirmada!

**CÓDIGO DE RESERVA: {codigo}**
(Guarda este código para modificar o cancelar)

Detalles:
- Mesa {mesa_numero}
- {fecha} a las {hora}
- {personas} personas

Te esperamos. ¡Gracias por tu reserva!"""
    
    elif action == "modificar":
        cambios_realizados = format_changes(result.get('cambios_realizados', {}))
        return f"""✅ Reserva modificada correctamente

Tu código sigue siendo: **{codigo}**

Nuevos datos confirmados:
{cambios_realizados}"""
    
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
        hora = alt.get('hora', '') if isinstance(alt, dict) else ''
        capacidad = alt.get('capacidad', '') if isinstance(alt, dict) else ''
        lines.append(f"{i}. {hora} - Mesa para {capacidad} personas")
    
    return "\n".join(lines)

def mask_phone(phone: str) -> str:
    """Enmascara el número de teléfono para privacidad"""
    if not phone or not isinstance(phone, str) or len(phone) < 4:
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