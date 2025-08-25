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
        
        # Formatear respuesta para WhatsApp con soporte de imágenes
        response_text, media_urls = format_whatsapp_message_with_media(result)
        
        # Construir TwiML con soporte para media
        if media_urls:
            # Incluir imágenes en el mensaje
            media_elements = '\n'.join([f'    <Media>{url}</Media>' for url in media_urls[:5]])  # Límite de 5 imágenes
            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>
        <Body>{response_text}</Body>
{media_elements}
    </Message>
</Response>"""
        else:
            # Mensaje de solo texto
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

def format_whatsapp_message_with_media(result: dict) -> tuple[str, list]:
    """Formatea el mensaje para WhatsApp incluyendo URLs de media si están disponibles"""
    message = result.get("message", "")
    action = result.get("action")
    media_urls = []
    
    # Verificar si hay información de imágenes en la respuesta
    if "platos_con_imagen" in result:
        # Se solicitaron imágenes del menú
        platos = result.get("platos_con_imagen", [])
        if platos:
            for plato in platos[:5]:  # Límite de 5 imágenes para WhatsApp
                if plato.get("imagen_url"):
                    media_urls.append(plato["imagen_url"])
                    # Agregar descripción del plato al mensaje
                    message += f"\n\n🍽️ **{plato['nombre']}**\n"
                    if plato.get("descripcion"):
                        message += f"{plato['descripcion']}\n"
                    if plato.get("precio"):
                        message += f"💰 Precio: €{plato['precio']}"
    
    # Verificar si hay una imagen específica de un plato
    elif "plato_con_imagen" in result:
        plato = result.get("plato_con_imagen")
        if plato and plato.get("tiene_imagen") and plato.get("imagen_url"):
            media_urls.append(plato["imagen_url"])
            # El mensaje ya debería incluir la descripción del plato
    
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
    
    return message, media_urls

def format_whatsapp_message(result: dict) -> str:
    """Formatea el mensaje para WhatsApp (versión legacy sin imágenes)"""
    message, _ = format_whatsapp_message_with_media(result)
    return message