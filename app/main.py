from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Crear aplicación FastAPI
app = FastAPI(
    title="GastroBot Orchestrator",
    description="Orquestador inteligente para reservas de restaurante",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check SIMPLE primero
@app.get("/")
async def root():
    return {"message": "GastroBot Orchestrator is running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "gastrobot-orchestrator",
        "port": os.environ.get("PORT", "unknown"),
        "environment": "railway"
    }

# Importar y añadir routers DESPUÉS
try:
    from app.api.chat import router as chat_router
    app.include_router(chat_router, prefix="/api")
    logger.info("✅ Chat router loaded")
except Exception as e:
    logger.error(f"❌ Could not load chat router: {e}")

# Log de inicio
logger.info("🚀 GastroBot Orchestrator initialized")