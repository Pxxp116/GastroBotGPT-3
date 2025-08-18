from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager
from app.api.whatsapp import router as whatsapp_router
from app.api.chat import router as chat_router
from app.core.config import settings
from app.core.state import state_store

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación"""
    logger.info("🚀 Iniciando GastroBot Orchestrator...")
    logger.info(f"📍 Backend URL: {settings.BACKEND_BASE_URL}")
    logger.info(f"🤖 Modelo OpenAI: {settings.OPENAI_MODEL}")
    
    # Inicializar estado si usa Redis
    await state_store.initialize()
    
    yield
    
    # Limpiar recursos
    await state_store.cleanup()
    logger.info("👋 GastroBot Orchestrator detenido")

# Crear aplicación FastAPI
app = FastAPI(
    title="GastroBot Orchestrator",
    description="Orquestador inteligente para reservas de restaurante",
    version="1.0.0",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(chat_router, prefix="/api")
app.include_router(whatsapp_router, prefix="/api")

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "gastrobot-orchestrator",
        "backend": settings.BACKEND_BASE_URL,
        "model": settings.OPENAI_MODEL
    }