import httpx
import pytest
from config import config


@pytest.mark.live
def test_health():
    r = httpx.get(f"{config.base_url}/health", timeout=10)
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.live
def test_chat():
    messages = [{"role": "user", "content": "What is the capital of France?"}]
    body = {
        "model": config.azure_openai_model,
        "messages": messages,
    }
    headers = {
        "Content-Type": "application/json",
    }
    r = httpx.post(
        f"{config.base_url}/v1/chat",
        json=body,
        headers=headers,
        timeout=30,
    )
    print(r.json())
    assert r.status_code == 200
    body = r.json()
    assert "provider_message_id" in body
    assert body["completion"]["text"] is not None
