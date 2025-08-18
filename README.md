# 🍽️ GastroBot Orchestrator

Sistema inteligente de orquestación para GastroBot que utiliza OpenAI Responses API con function calling para gestionar reservas de restaurante manteniendo el contexto conversacional.

## 🌟 Características

- **Gestión de Estado Conversacional**: Mantiene el contexto entre mensajes sin reiniciar flujos
- **Function Calling**: Integración con OpenAI para decisiones inteligentes sobre qué función llamar
- **Backend Integration**: Comunicación completa con el backend de GastroBot existente
- **Validaciones Inteligentes**: No inventa datos, solo responde con información del backend
- **Sugerencias Automáticas**: Ofrece alternativas cuando no hay disponibilidad
- **Persistencia Flexible**: Soporte para almacenamiento en memoria o Redis

## 📋 Requisitos

- Python 3.11+
- Docker y Docker Compose
- Cuenta de OpenAI con acceso a API
- Backend de GastroBot funcionando

## 🚀 Instalación Rápida

### Con Docker (Recomendado)

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd gastrobot-orchestrator