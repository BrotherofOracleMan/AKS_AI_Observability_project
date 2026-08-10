from pydantic import BaseModel, Field

class ChatMessage(BaseModel):
    role: str
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)