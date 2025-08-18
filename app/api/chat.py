from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any
import logging
from pydantic import BaseModel, Field
from datetime import datetime

from app.core.state import state_store, ConversationState
from app.core.openai_client import orchestrator
from app.core.config import settings
from app.core.logic import extract_intent_from_message

logger = logging.getLogger(__name__)

router = APIRouter()

class ChatRequest(BaseModel):
    conversation_id: str = Field(..., description="ID único de la conversación")
    user_message: str = Field(..., description="Mensaje del usuario", max_length=settings.MAX_MESSAGE_LENGTH)

class ChatResponse(BaseModel):
    conversation_id: str
    assistant_message: str
    timestamp: str
    action: Dict[str, Any] = None

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Endpoint principal para procesar mensajes del chat
    """
    try:
        logger.info(f"📨 Nueva solicitud - Conversación: {request.conversation_id}")
        logger.info(f"Mensaje usuario: {request.user_message}")
        
        # Obtener o crear estado de conversación
        state = await state_store.get(request.conversation_id)
        
        if not state:
            state = ConversationState(request.conversation_id)
            logger.info("Nueva conversación iniciada")
        
        # Detectar intent si no está definido
        if not state.intent:
            intent = extract_intent_from_message(request.user_message)
            if intent:
                state.update_intent(intent)
                logger.info(f"Intent detectado: {intent}")
        
        # Añadir mensaje del usuario al historial
        state.add_to_history("user", request.user_message)
        
        # Procesar con OpenAI
        result = await orchestrator.process_message(
            user_message=request.user_message,
            conversation_state=state.to_dict(),
            conversation_history=state.history
        )
        
        # Actualizar estado con la respuesta
        if result["message"]:
            state.add_to_history("assistant", result["message"])
        
        # Si hubo tool calls exitosas, actualizar estado
        for tool_call in result.get("tool_calls", []):
            if tool_call.get("function_name") == "create_reservation" and tool_call.get("result", {}).get("exito"):
                state.current_reservation = tool_call["result"].get("reserva", {})
            elif tool_call.get("function_name") in ["modify_reservation", "cancel_reservation"]:
                if tool_call.get("result", {}).get("exito"):
                    state.current_reservation = {}  # Limpiar reserva actual
        
        # Guardar estado actualizado
        await state_store.save(state)
        
        # Preparar respuesta
        response = ChatResponse(
            conversation_id=request.conversation_id,
            assistant_message=result["message"],
            timestamp=datetime.utcnow().isoformat(),
            action=result.get("action")
        )
        
        logger.info(f"✅ Respuesta generada: {result['message'][:100]}...")
        if result.get("action"):
            logger.info(f"🎯 Acción detectada: {result['action']['accion']}")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Error procesando chat: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando mensaje: {str(e)}"
        )

@router.get("/chat/{conversation_id}/state")
async def get_conversation_state(conversation_id: str):
    """
    Obtiene el estado actual de una conversación (para debug)
    """
    state = await state_store.get(conversation_id)
    
    if not state:
        raise HTTPException(
            status_code=404,
            detail="Conversación no encontrada"
        )
    
    return state.to_dict()

@router.delete("/chat/{conversation_id}")
async def clear_conversation(conversation_id: str):
    """
    Limpia el estado de una conversación
    """
    await state_store.delete(conversation_id)
    
    return {
        "message": "Conversación eliminada",
        "conversation_id": conversation_id
    }