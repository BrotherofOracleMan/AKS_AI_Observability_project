from fastapi import FastAPI
from pydantic import BaseModel, Field
from openai_client import get_response
app = FastAPI(title="AKS AI Observability")


class ChatMessage(BaseModel):
    role: str
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/chat")
def chat(request: ChatRequest):
    # Phase 0 stub — Phase 1 will call Azure OpenAI here
    last_user = next(
        (m.content for m in reversed(request.messages) if m.role == "user"),
        request.messages[-1].content,
    )
    return {
        "content": f"[stub] You said: {last_user}",
        "model": "stub-echo",
    }
