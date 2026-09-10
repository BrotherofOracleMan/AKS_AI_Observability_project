from fastapi.testclient import TestClient
from openai_client import fake_chat_completion
from main import app
from models import ChatRequest
import pytest

client = TestClient(app)

def test_chat_stub(mocker):

    fake_response = fake_chat_completion()
    mock_chat = mocker.patch("main.chat", return_value=fake_response)
    
    r = client.post("/v1/chat", json={"messages": [{"role": "user", "content": "hello"}]})
    response_json = r.json()
   
    assert r.status_code == 200
    assert response_json["provider_message_id"] == fake_response["provider_message_id"]
    assert response_json["completion"]["text"] == fake_response["completion"]["text"]
    assert response_json["completion"]["model"] == fake_response["completion"]["model"]
    assert response_json["completion"]["prompt_tokens"] == fake_response["completion"]["prompt_tokens"]
    assert response_json["completion"]["completion_tokens"] == fake_response["completion"]["completion_tokens"]
    assert response_json["completion"]["total_tokens"] == fake_response["completion"]["total_tokens"]

    mock_chat.assert_called_once_with(ChatRequest(messages=[{"role": "user", "content": "hello"}]))
