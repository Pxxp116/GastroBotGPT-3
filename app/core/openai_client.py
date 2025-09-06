import json
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
from app.core.config import settings
from app.core.tools import get_tool_definitions, execute_tool_call
from app.core.prompts import get_system_prompt, format_error_message

logger = logging.getLogger(__name__)

class OpenAIOrchestrator:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        
    async def process_message(
        self,
        user_message: str,
        conversation_state: Dict[str, Any],
        conversation_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Procesa un mensaje del usuario y devuelve la respuesta del asistente
        """
        try:
            # Construir mensajes para OpenAI
            messages = await self._build_messages(
                user_message, 
                conversation_state, 
                conversation_history
            )
            
            # Obtener tools disponibles
            tools = get_tool_definitions()
            
            # Llamar a OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=settings.OPENAI_MAX_TOKENS,
                temperature=settings.OPENAI_TEMPERATURE
            )
            
            # Procesar respuesta
            assistant_message = response.choices[0].message
            result = {
                "message": assistant_message.content or "",
                "tool_calls": [],
                "action": None
            }
            
            # Procesar tool calls si existen
            if assistant_message.tool_calls:
                for tool_call in assistant_message.tool_calls:
                    tool_result = await self._execute_tool(
                        tool_call,
                        conversation_state
                    )
                    result["tool_calls"].append(tool_result)
                    
                    # Detectar tipo de acción
                    if tool_call.function.name in ["create_reservation", "modify_reservation", "cancel_reservation"]:
                        result["action"] = self._build_action_object(
                            tool_call.function.name,
                            tool_result
                        )
                        if tool_call.function.name == "create_reservation":
                            logger.info(f"✅ Reserva creada exitosamente: {tool_result}")
                
                # Detectar si debería haber creado reserva pero no lo hizo
                if conversation_state.get("repeated_check_warning") and conversation_state.get("ready_to_create"):
                    has_create = any(tc.function.name == "create_reservation" for tc in assistant_message.tool_calls)
                    if not has_create:
                        logger.warning("⚠️ ADVERTENCIA: Se detectó verificación repetida pero NO se creó reserva")
                        logger.warning(f"Estado: ready_to_create={conversation_state.get('ready_to_create')}, "
                                     f"repeated_check={conversation_state.get('repeated_check_warning')}")
                
                # Si hubo tool calls, obtener respuesta final del modelo
                if result["tool_calls"]:
                    final_response = await self._get_final_response(
                        messages,
                        assistant_message,
                        result["tool_calls"]
                    )
                    result["message"] = final_response
            
            return result
            
        except Exception as e:
            logger.error(f"Error en OpenAI orchestrator: {e}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error args: {e.args}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "message": format_error_message(str(e)),
                "tool_calls": [],
                "action": None
            }
    
    async def _build_messages(
        self,
        user_message: str,
        conversation_state: Dict[str, Any],
        conversation_history: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """Construye el array de mensajes para OpenAI"""
        try:
            logger.info("Building messages - start")
            messages = []
            
            # System prompt con duración dinámica
            from app.core.backend_client import backend_client
            # Sanitizar conversation_state para logging seguro
            safe_state = {}
            try:
                for key, value in conversation_state.items():
                    safe_state[key] = str(value) if value is not None else 'None'
            except:
                safe_state = {'error': 'Could not serialize conversation_state'}
            logger.info(f"Getting system prompt with conversation_state: {safe_state}")
            system_prompt = await get_system_prompt(conversation_state, backend_client)
            logger.info(f"System prompt generated successfully, length: {len(system_prompt) if system_prompt else 0}")
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        except Exception as e:
            logger.error(f"Error in _build_messages during system_prompt: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
        
        try:
            # Historial relevante (últimos N mensajes)
            logger.info("Adding conversation history")
            history_limit = 10
            for msg in conversation_history[-history_limit:]:
                messages.append(msg)
            
            # Mensaje actual del usuario
            logger.info(f"Adding user message: {user_message}")
            messages.append({
                "role": "user",
                "content": user_message
            })
            
            logger.info(f"Messages built successfully, total: {len(messages)}")
            return messages
            
        except Exception as e:
            logger.error(f"Error in _build_messages during history/user message: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    async def _execute_tool(
        self,
        tool_call: Any,
        conversation_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Ejecuta una tool call"""
        try:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            
            logger.info(f"Ejecutando tool: {function_name} con args: {arguments}")
            
            result = await execute_tool_call(
                function_name,
                arguments,
                conversation_state
            )
            
            return {
                "tool_call_id": tool_call.id,
                "function_name": function_name,
                "arguments": arguments,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error ejecutando tool {tool_call.function.name}: {e}")
            return {
                "tool_call_id": tool_call.id,
                "function_name": tool_call.function.name,
                "arguments": {},
                "result": {"error": str(e)}
            }
    
    async def _get_final_response(
        self,
        original_messages: List[Dict[str, Any]],
        assistant_message: Any,
        tool_results: List[Dict[str, Any]]
    ) -> str:
        """Obtiene respuesta final después de ejecutar tools"""
        messages = original_messages.copy()
        
        # Añadir mensaje del asistente con tool calls
        messages.append({
            "role": "assistant",
            "content": assistant_message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                } for tc in assistant_message.tool_calls
            ]
        })
        
        # Añadir resultados de tools
        for result in tool_results:
            messages.append({
                "role": "tool",
                "tool_call_id": result["tool_call_id"],
                "content": json.dumps(result["result"], ensure_ascii=False)
            })
        
        # Obtener respuesta final
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=settings.OPENAI_MAX_TOKENS,
            temperature=settings.OPENAI_TEMPERATURE
        )
        
        return response.choices[0].message.content
    
    def _build_action_object(
        self,
        action_type: str,
        tool_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Construye el objeto de acción para el frontend"""
        if not tool_result.get("result", {}).get("exito"):
            return None
        
        action_map = {
            "create_reservation": "crear",
            "modify_reservation": "modificar",
            "cancel_reservation": "cancelar"
        }
        
        result_data = tool_result["result"]
        reservation_data = result_data.get("reserva", {})
        
        return {
            "accion": action_map.get(action_type),
            "id_reserva": reservation_data.get("id"),
            "resumen": result_data.get("mensaje", ""),
            "datos_clave": {
                "fecha": reservation_data.get("fecha"),
                "hora": reservation_data.get("hora"),
                "comensales": reservation_data.get("personas"),
                "mesa": reservation_data.get("mesa_id"),
                "zona": reservation_data.get("zona"),
                "duracion_min": reservation_data.get("duracion", settings.DEFAULT_DURATION_MIN)
            }
        }

orchestrator = OpenAIOrchestrator()