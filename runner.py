#!/usr/bin/env python
import os
import sys

print("=" * 50)
print("GastroBot Orchestrator - Starting")
print("=" * 50)

# Mostrar todas las variables de entorno (para debug)
print("Environment variables:")
for key, value in os.environ.items():
    if key == "PORT":
        print(f"  {key} = {value}")
    elif "PASS" not in key.upper() and "KEY" not in key.upper() and "SECRET" not in key.upper():
        print(f"  {key} = {value[:50]}..." if len(value) > 50 else f"  {key} = {value}")

# Obtener puerto
port = os.environ.get("PORT", "8000")
print(f"\nPORT environment variable: '{port}'")

try:
    port = int(port)
    print(f"Parsed port: {port}")
except ValueError as e:
    print(f"ERROR: Could not parse PORT '{port}' as integer: {e}")
    print("Using default port 8000")
    port = 8000

print("=" * 50)

# Importar y ejecutar
try:
    import uvicorn
    print(f"Starting Uvicorn on 0.0.0.0:{port}")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
except ImportError as e:
    print(f"ERROR: Could not import required modules: {e}")
    print("Trying alternative start method...")
    os.system(f"python -m uvicorn app.main:app --host 0.0.0.0 --port {port}")
except Exception as e:
    print(f"CRITICAL ERROR: {e}")
    sys.exit(1)