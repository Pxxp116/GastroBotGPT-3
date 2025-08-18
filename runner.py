#!/usr/bin/env python3
import os
import sys

# Añadir el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print(f"Runner.py executing from: {__file__}", flush=True)
print(f"Working directory: {os.getcwd()}", flush=True)
print(f"Python path: {sys.path}", flush=True)

# Obtener puerto
port = int(os.environ.get("PORT", 8000))
print(f"Starting on port: {port}", flush=True)

# Intentar importar de varias formas
try:
    from app.main import app
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
except ImportError as e:
    print(f"Import error: {e}", flush=True)
    # Intento alternativo
    os.system(f"python -m uvicorn app.main:app --host 0.0.0.0 --port {port}")