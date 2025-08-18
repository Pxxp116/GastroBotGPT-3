#!/usr/bin/env python
"""
Startup script for GastroBot Orchestrator
Handles Railway's PORT environment variable
"""

import os
import sys
import uvicorn
import logging

# Configurar logging ANTES de importar la app
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)

def main():
    """Iniciar el servidor con el puerto correcto"""
    # Obtener puerto de Railway o usar 8000 por defecto
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    
    logger.info(f"🚀 Starting GastroBot Orchestrator")
    logger.info(f"📍 Host: {host}")
    logger.info(f"🔌 Port: {port}")
    logger.info(f"🔗 Health check will be available at http://{host}:{port}/health")
    
    # Log environment variables (sin mostrar secrets)
    logger.info("📋 Environment variables loaded:")
    logger.info(f"  - BACKEND_BASE_URL: {os.environ.get('BACKEND_BASE_URL', 'NOT SET')}")
    logger.info(f"  - OPENAI_API_KEY: {'SET' if os.environ.get('OPENAI_API_KEY') else 'NOT SET'}")
    logger.info(f"  - PORT: {port}")
    
    try:
        # Configuración de uvicorn
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            log_level="info",
            access_log=True,
            reload=False,
            # Importante para Railway
            workers=1,
            loop="asyncio",
            interface="asgi3"
        )
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    try:
        logger.info("🎬 Initiating startup sequence...")
        main()
    except KeyboardInterrupt:
        logger.info("⏹ Shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 Critical error during startup: {e}", exc_info=True)
        sys.exit(1)