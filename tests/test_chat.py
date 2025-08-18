import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import json

from app.main import app

client = TestClient(app)

@pytest.fixture
def mock_backend():
    with patch('app.core.backend_client.backend_client') as mock:
        yield mock

@pytest.fixture
def mock_openai():
    with patch('app.core.openai_client.OpenAI') as mock:
        yield mock

def test_health_check():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_chat_create_reservation_happy_path(mock_backend, mock_openai):
    """Test crear reserva - flujo completo exitoso"""
    
    # Mock respuestas del backend
    mock_backend.check_availability = AsyncMock(return_value={
        "exito": True,
        "mesa_disponible": {"id": 1, "numero": 5, "capacidad": 4}
    })
    
    mock_backend.create_reservation = AsyncMock(return_value={
        "exito": True,
        "mensaje": "Reserva creada correctamente",
        "reserva": {
            "id": 123,
            "nombre": "Juan Pérez",
            "fecha": "2024-12-15",
            "hora": "21:00",
            "personas": 4,
            "mesa_id": 1
        }
    })
    
    # Solicitud de chat
    response = client.post("/api/chat", json={
        "conversation_id": "test-123",
        "user_message": "Quiero reservar mesa para 4 personas mañana a las 21:00"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "assistant_message" in data
    assert data["conversation_id"] == "test-123"

def test_chat_modify_reservation_without_losing_state(mock_backend):
    """Test modificar reserva sin perder contexto"""
    
    # Primera interacción - crear reserva
    response1 = client.post("/api/chat", json={
        "conversation_id": "test-456",
        "user_message": "Tengo una reserva a nombre de María García para hoy a las 20:00"
    })
    assert response1.status_code == 200
    
    # Segunda interacción - modificar sin repetir datos
    mock_backend.modify_reservation = AsyncMock(return_value={
        "exito": True,
        "mensaje": "Reserva modificada",
        "reserva": {"id": 456, "hora": "21:00"}
    })
    
    response2 = client.post("/api/chat", json={
        "conversation_id": "test-456",
        "user_message": "Mejor cámbiala a las 21:00"
    })
    
    assert response2.status_code == 200
    data = response2.json()
    
    # Verificar que mantuvo el contexto
    state_response = client.get("/api/chat/test-456/state")
    state = state_response.json()
    assert state["filled_fields"].get("nombre") == "María García"

def test_chat_restaurant_closed_hours(mock_backend):
    """Test horario cerrado del restaurante"""
    
    mock_backend.check_availability = AsyncMock(return_value={
        "exito": False,
        "mensaje": "El restaurante está cerrado a esa hora",
        "alternativas": [
            {"fecha": "2024-12-15", "hora": "20:00", "capacidad": 2},
            {"fecha": "2024-12-15", "hora": "21:00", "capacidad": 2}
        ]
    })
    
    response = client.post("/api/chat", json={
        "conversation_id": "test-789",
        "user_message": "Mesa para 2 a las 17:00"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "alternativas" in data["assistant_message"].lower() or "cerrado" in data["assistant_message"].lower()

def test_chat_menu_query_no_invention(mock_backend):
    """Test consulta de menú - no inventar platos"""
    
    mock_backend.get_menu = AsyncMock(return_value={
        "exito": True,
        "menu": {
            "categorias": [
                {
                    "nombre": "Entrantes",
                    "platos": [
                        {"nombre": "Ensalada César", "precio": 12.50},
                        {"nombre": "Croquetas", "precio": 8.00}
                    ]
                }
            ]
        }
    })
    
    response = client.post("/api/chat", json={
        "conversation_id": "test-menu",
        "user_message": "¿Tienen pizza en el menú?"
    })
    
    assert response.status_code == 200
    data = response.json()
    # No debe inventar que hay pizza si no está en el menú
    assert "pizza" not in data["assistant_message"].lower() or "no" in data["assistant_message"].lower()

@pytest.mark.asyncio
async def test_state_persistence():
    """Test que el estado persiste entre llamadas"""
    from app.core.state import state_store, ConversationState
    
    # Crear estado
    state = ConversationState("test-persist")
    state.update_field("nombre", "Carlos")
    state.update_field("telefono", "666777888")
    
    # Guardar
    await state_store.save(state)
    
    # Recuperar
    retrieved_state = await state_store.get("test-persist")
    
    assert retrieved_state is not None
    assert retrieved_state.filled_fields["nombre"] == "Carlos"
    assert retrieved_state.filled_fields["telefono"] == "666777888"
    
    # Limpiar
    await state_store.delete("test-persist")