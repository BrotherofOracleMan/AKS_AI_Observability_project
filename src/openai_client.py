from config import config
from openai import AzureOpenAI

client = AzureOpenAI(
    api_key=config.azure_openai_api_key,
    azure_endpoint=config.azure_openai_endpoint,
    api_version=config.azure_openai_api_version
)


def chat(messages: list[dict[str, str]]) -> dict[str, str]:
    completion = client.chat.completions.create(
        model=config.azure_openai_model,
        messages=messages,
    )

    total_tokens = completion.usage.total_tokens
    prompt_tokens = completion.usage.prompt_tokens
    completion_tokens = completion.usage.completion_tokens
    completion_text = completion.choices[0].message.content

    return {
        "completion_text": completion_text,
        "model": config.azure_openai_model,
        "usage":
        {
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "prompt_tokens": prompt_tokens,
        }
    }

if __name__ == "__main__":
    print(chat([{"role": "user", "content": "How do I output all files in a directory using Python?"}]))
