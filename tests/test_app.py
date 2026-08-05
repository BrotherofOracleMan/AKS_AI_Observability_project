from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_chat_stub():
    r = client.post(
        "/v1/chat",
        json={"messages": [{"role": "user", "content": "hello"}]},
    )
    assert r.status_code == 200
    assert r.json()["content"] == "[stub] You said: hello"


def test_chat_rejects_empty_messages():
    r = client.post("/v1/chat", json={"messages": []})
    assert r.status_code == 422
