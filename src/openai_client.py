# TODO — build openai_client.py
# [x] Create AzureOpenAI client from config
# [ ] Extract a chat() helper (messages in → content + usage out)
# [ ] Accept list[{role, content}]
# [ ] Return prompt / completion / total tokens
# [ ] Move the script smoke test under if __name__ == "__main__"
# [ ] (later) error mapping + wire into main.py / tests

from config import config
from openai import AzureOpenAI

client = AzureOpenAI(
    api_key=config.azure_openai_api_key,
    azure_endpoint=config.azure_openai_endpoint,
    api_version=config.azure_openai_api_version
)


completion = client.chat.completions.create(
    model=config.azure_openai_model,
    messages=[
        {
            "role": "user",
            "content": "How do I output all files in a directory using Python?",
        },
    ],
)
print(completion.to_json())
