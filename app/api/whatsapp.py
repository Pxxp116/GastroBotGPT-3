from fastapi import APIRouter, Form, Response, Request
from typing import Optional
import logging
import json

from app.api.chat import ChatRequest
from app.core.state import state_store, ConversationState
from app.core.openai_client import orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/webhook/whatsapp")
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    To: str = Form(None),
    MessageSid: str = Form(None),
    ProfileName: str = Form(None)
):
    """
    Webhook para recibir mensajes de WhatsApp via Twilio
    """
    try:
        logger.info(f"📱 WhatsApp mensaje de {From}: {Body}")
        
        # Usar el número como conversation_id
        conversation_id = From.replace("whatsapp:", "").replace("+", "")
        
        # Obtener o crear estado
        state = await state_store.get(conversation_id)
        if not state:
            state = ConversationState(conversation_id)
            state.update_field("telefono", From.replace("whatsapp:", ""))
            if ProfileName:
                state.update_field("nombre", ProfileName)
        
        # Añadir mensaje al historial
        state.add_to_history("user", Body)
        
        # Procesar con OpenAI
        result = await orchestrator.process_message(
            user_message=Body,
            conversation_state=state.to_dict(),
            conversation_history=state.history
        )
        
        # Guardar estado actualizado
        if result["message"]:
            state.add_to_history("assistant", result["message"])
        await state_store.save(state)
        
        # Formatear respuesta para WhatsApp
        response_text = format_whatsapp_message(result)
        
        # Responder con TwiML
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{response_text}</Message>
</Response>"""
        
        logger.info(f"✅ Respuesta: {response_text[:100]}...")
        
        return Response(content=twiml, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"❌ Error en webhook: {e}", exc_info=True)
        
        # Respuesta de error
        error_twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>Disculpa, hubo un error procesando tu mensaje. Por favor intenta de nuevo o escribe "ayuda".</Message>
</Response>"""
        
        return Response(content=error_twiml, media_type="application/xml")

@router.get("/webhook/whatsapp")
async def whatsapp_webhook_get():
    """Verificación de webhook por Twilio"""
    return {"status": "ok"}

def format_whatsapp_message(result: dict) -> str:
    """Formatea el mensaje para WhatsApp"""
    message = result.get("message", "")
    action = result.get("action")
    
    # Si hay una acción de reserva, formatear especialmente
    if action and action.get("accion") == "crear":
        datos = action.get("datos_clave", {})
        message += f"\n\n📋 *Resumen de tu reserva:*\n"
        message += f"📅 Fecha: {datos.get('fecha', 'N/A')}\n"
        message += f"🕐 Hora: {datos.get('hora', 'N/A')}\n"
        message += f"👥 Personas: {datos.get('comensales', 'N/A')}\n"
        
    # Limitar longitud para WhatsApp
    if len(message) > 1500:
        message = message[:1497] + "..."
    
    return message