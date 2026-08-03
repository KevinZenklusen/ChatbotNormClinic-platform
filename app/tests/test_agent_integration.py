from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from langchain_core.messages import AIMessage


client = TestClient(app)


@patch("app.routes.agent.cadena_guardian")
@patch("app.routes.agent.agent")
def test_chat_endpoint(
    mock_agent,
    mock_guardian
):

    mock_guardian.ainvoke = AsyncMock()

    mock_guardian.ainvoke.return_value = type(
        "Resp",
        (),
        {"content": "segura"}
    )

    respuesta_msg = AIMessage(content="OK")

    mock_agent.ainvoke = AsyncMock()

    mock_agent.ainvoke.return_value = {
        "messages": [respuesta_msg]
    }

    response = client.post(
        "/agent/",
        json={
            "consulta": "Hola",
            "session_id": "1",
            "user_id": "1"
        }
    )

    assert response.status_code == 200


def test_endpoint_payload_invalido():

    response = client.post(
        "/agent/",
        json={}
    )

    assert response.status_code == 422