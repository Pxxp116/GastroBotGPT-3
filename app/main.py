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

# Crear aplicación
app = FastAPI(
    title="GastroBot Orchestrator",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health checks
@app.get("/")
async def root():
    return {"message": "GastroBot Orchestrator", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "gastrobot-orchestrator"}

# Importar routers
try:
    from app.api.chat import router as chat_router
    app.include_router(chat_router, prefix="/api")
    logger.info("✅ Chat router loaded")
except ImportError as e:
    logger.error(f"❌ Could not load chat router: {e}")

try:
    from app.api.whatsapp import router as whatsapp_router
    app.include_router(whatsapp_router, prefix="/api")
    logger.info("✅ WhatsApp router loaded")
except ImportError as e:
    logger.warning(f"⚠️ WhatsApp router not available: {e}")

@app.on_event("startup")
async def startup_event():
    logger.info(f"🚀 GastroBot started on port {os.environ.get('PORT', 'unknown')}")
    logger.info(f"📱 WhatsApp webhook ready at /api/webhook/whatsapp")