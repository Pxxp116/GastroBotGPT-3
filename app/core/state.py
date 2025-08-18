import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)

class ConversationState:
    """Representa el estado de una conversación"""
    
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.intent = None  # crear, modificar, cancelar, consultar
        self.filled_fields = {}
        self.missing_fields = []
        self.current_reservation = {}
        self.history = []
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
    def update_intent(self, intent: str):
        """Actualiza el intent detectado"""
        self.intent = intent
        self.updated_at = datetime.utcnow()
        
    def update_field(self, field: str, value: Any):
        """Actualiza un campo específico"""
        self.filled_fields[field] = value
        if field in self.missing_fields:
            self.missing_fields.remove(field)
        self.updated_at = datetime.utcnow()
        
    def set_missing_fields(self, fields: list):
        """Establece campos faltantes"""
        self.missing_fields = fields
        self.updated_at = datetime.utcnow()
        
    def add_to_history(self, role: str, content: str):
        """Añade mensaje al historial"""
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        # Limitar historial
        if len(self.history) > settings.MAX_CONVERSATION_LENGTH:
            self.history = self.history[-settings.MAX_CONVERSATION_LENGTH:]
        self.updated_at = datetime.utcnow()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el estado a diccionario"""
        return {
            "conversation_id": self.conversation_id,
            "intent": self.intent,
            "filled_fields": self.filled_fields,
            "missing_fields": self.missing_fields,
            "current_reservation": self.current_reservation,
            "history": self.history,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationState':
        """Crea estado desde diccionario"""
        state = cls(data["conversation_id"])
        state.intent = data.get("intent")
        state.filled_fields = data.get("filled_fields", {})
        state.missing_fields = data.get("missing_fields", [])
        state.current_reservation = data.get("current_reservation", {})
        state.history = data.get("history", [])
        state.created_at = datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat()))
        state.updated_at = datetime.fromisoformat(data.get("updated_at", datetime.utcnow().isoformat()))
        return state

class StateStore(ABC):
    """Interfaz abstracta para almacenamiento de estado"""
    
    @abstractmethod
    async def get(self, conversation_id: str) -> Optional[ConversationState]:
        pass
    
    @abstractmethod
    async def save(self, state: ConversationState):
        pass
    
    @abstractmethod
    async def delete(self, conversation_id: str):
        pass
    
    @abstractmethod
    async def initialize(self):
        pass
    
    @abstractmethod
    async def cleanup(self):
        pass

class InMemoryStateStore(StateStore):
    """Almacenamiento en memoria"""
    
    def __init__(self):
        self.states: Dict[str, ConversationState] = {}
        
    async def get(self, conversation_id: str) -> Optional[ConversationState]:
        state = self.states.get(conversation_id)
        if state:
            # Verificar TTL
            if (datetime.utcnow() - state.updated_at).seconds > settings.STATE_TTL_SECONDS:
                await self.delete(conversation_id)
                return None
        return state
    
    async def save(self, state: ConversationState):
        self.states[state.conversation_id] = state
        
    async def delete(self, conversation_id: str):
        if conversation_id in self.states:
            del self.states[conversation_id]
            
    async def initialize(self):
        logger.info("Inicializado almacenamiento en memoria")
        
    async def cleanup(self):
        # Limpiar estados antiguos
        now = datetime.utcnow()
        to_delete = []
        for conv_id, state in self.states.items():
            if (now - state.updated_at).seconds > settings.STATE_TTL_SECONDS:
                to_delete.append(conv_id)
        
        for conv_id in to_delete:
            await self.delete(conv_id)
        
        logger.info(f"Limpiados {len(to_delete)} estados antiguos")

class RedisStateStore(StateStore):
    """Almacenamiento en Redis"""
    
    def __init__(self):
        self.redis_client = None
        
    async def initialize(self):
        if settings.REDIS_URL:
            self.redis_client = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Conectado a Redis para almacenamiento de estado")
        else:
            logger.warning("REDIS_URL no configurado, usando almacenamiento en memoria")
            
    async def get(self, conversation_id: str) -> Optional[ConversationState]:
        if not self.redis_client:
            return None
            
        key = f"conversation:{conversation_id}"
        data = await self.redis_client.get(key)
        
        if data:
            return ConversationState.from_dict(json.loads(data))
        return None
    
    async def save(self, state: ConversationState):
        if not self.redis_client:
            return
            
        key = f"conversation:{state.conversation_id}"
        data = json.dumps(state.to_dict(), ensure_ascii=False)
        
        await self.redis_client.setex(
            key,
            settings.STATE_TTL_SECONDS,
            data
        )
    
    async def delete(self, conversation_id: str):
        if not self.redis_client:
            return
            
        key = f"conversation:{conversation_id}"
        await self.redis_client.delete(key)
    
    async def cleanup(self):
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Conexión Redis cerrada")

# Instancia global del store
if settings.REDIS_URL:
    state_store = RedisStateStore()
else:
    state_store = InMemoryStateStore()