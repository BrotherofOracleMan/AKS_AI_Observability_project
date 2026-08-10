from config import config
from openai import AzureOpenAI
from models import ChatRequest

client = AzureOpenAI(
    api_key=config.azure_openai_api_key,
    azure_endpoint=config.azure_openai_endpoint,
    api_version=config.azure_openai_api_version
)


def chat(request: ChatRequest) -> dict[str, str]:
    completion = client.chat.completions.create(
        model=config.azure_openai_model,
        messages=request.messages,
    )

    total_tokens = completion.usage.total_tokens
    prompt_tokens = completion.usage.prompt_tokens
    completion_tokens = completion.usage.completion_tokens
    completion_text = completion.choices[0].message.content
    id = completion.id

    return {
        "provider_message_id": id,
        "completion": {
            "text": completion_text,
            "model": config.azure_openai_model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }
    }

def fake_chat_completion() -> dict[str, str]:
    return {
        "provider_message_id": "fake-message-id",
        "completion": {
            "text": "This is a fake response",
            "model": "fake-model",
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "total_tokens": 2,
        }
    }

if __name__ == "__main__":
    print(chat([{"role": "user", "content": "How do I output all files in a directory using Python?"}]))
