from fastapi import APIRouter, Form, Response
from typing import Optional
import logging
import json
from datetime import datetime

from app.api.chat import chat
from app.core.state import state_store, ConversationState
from app.core.openai_client import orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/webhook/whatsapp")
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    To: str = Form(...),
    MessageSid: str = Form(None),
    ProfileName: str = Form(None),
    WaId: str = Form(None)
):
    """
    Webhook para recibir mensajes de WhatsApp via Twilio
    """
    try:
        logger.info(f"📱 WhatsApp mensaje de {From}: {Body}")
        
        # Usar el número de teléfono como conversation_id
        conversation_id = From.replace("whatsapp:", "").replace("+", "")
        
        # Obtener o crear estado
        state = await state_store.get(conversation_id)
        if not state:
            state = ConversationState(conversation_id)
            # Guardar info del usuario
            state.update_field("telefono", From.replace("whatsapp:", ""))
            state.update_field("nombre_whatsapp", ProfileName or "Cliente")
        
        # Añadir mensaje al historial
        state.add_to_history("user", Body)
        
        # Procesar con OpenAI
        result = await orchestrator.process_message(
            user_message=Body,
            conversation_state=state.to_dict(),
            conversation_history=state.history
        )
        
        # Actualizar estado
        if result["message"]:
            state.add_to_history("assistant", result["message"])
        await state_store.save(state)
        
        # Formatear respuesta para WhatsApp
        response_text = format_whatsapp_response(result)
        
        # Responder con TwiML
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{response_text}</Message>
</Response>"""
        
        logger.info(f"✅ Respuesta WhatsApp: {response_text[:100]}...")
        
        return Response(content=twiml, media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error en webhook WhatsApp: {e}", exc_info=True)
        
        error_twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>Disculpa, hubo un error procesando tu mensaje. Por favor intenta de nuevo.</Message>
</Response>"""
        
        return Response(content=error_twiml, media_type="application/xml")

@router.get("/webhook/whatsapp/status")
async def whatsapp_status():
    """Health check para Twilio"""
    return {"status": "active", "service": "gastrobot-whatsapp"}

def format_whatsapp_response(result: dict) -> str:
    """
    Formatea la respuesta para WhatsApp con emojis y estructura
    """
    message = result.get("message", "")
    action = result.get("action")
    
    # Añadir emojis según el contexto
    if action:
        if action["accion"] == "crear":
            message = f"✅ {message}\n\n"
            message += f"📅 Fecha: {action['datos_clave']['fecha']}\n"
            message += f"🕐 Hora: {action['datos_clave']['hora']}\n"
            message += f"👥 Personas: {action['datos_clave']['comensales']}\n"
            message += f"⏱ Duración: {action['datos_clave']['duracion_min']} min"
            
        elif action["accion"] == "modificar":
            message = f"✏️ {message}"
            
        elif action["accion"] == "cancelar":
            message = f"❌ {message}"
    
    # Limitar longitud para WhatsApp (1600 caracteres max)
    if len(message) > 1500:
        message = message[:1497] + "..."
    
    return message

# Funciones auxiliares para formateo WhatsApp
def format_menu_whatsapp(menu_data: dict) -> str:
    """Formatea el menú para WhatsApp"""
    lines = ["🍽 *MENÚ DEL RESTAURANTE*\n"]
    
    for categoria in menu_data.get("categorias", []):
        lines.append(f"\n*{categoria['nombre'].upper()}*")
        for plato in categoria.get("platos", []):
            lines.append(f"• {plato['nombre']} - {plato['precio']}€")
            if plato.get("descripcion"):
                lines.append(f"  _{plato['descripcion']}_")
    
    return "\n".join(lines)

def format_availability_whatsapp(slots: list) -> str:
    """Formatea disponibilidad para WhatsApp"""
    if not slots:
        return "No hay mesas disponibles para esa hora 😔"
    
    lines = ["📅 *Horarios disponibles:*\n"]
    for i, slot in enumerate(slots[:5], 1):
        lines.append(f"{i}. {slot['hora']} - Mesa para {slot['capacidad']} personas")
    
    lines.append("\n_Responde con el número de tu preferencia_")
    return "\n".join(lines)