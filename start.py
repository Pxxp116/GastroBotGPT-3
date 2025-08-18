#!/usr/bin/env python
"""
Startup script for GastroBot Orchestrator
Handles Railway's PORT environment variable
"""

import os
import sys
import uvicorn
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Iniciar el servidor con el puerto correcto"""
    # Obtener puerto de Railway o usar 8000 por defecto
    port = int(os.environ.get("PORT", 8000))
    
    # Configuración para Railway
    host = "0.0.0.0"
    
    logger.info(f"🚀 Starting GastroBot Orchestrator on {host}:{port}")
    
    # Configuración de uvicorn
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level="info",
        access_log=True,
        # Para producción, desactivar reload
        reload=False
    )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)