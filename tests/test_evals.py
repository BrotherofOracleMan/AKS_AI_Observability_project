"""Phase 5 thin evals: golden cases + contains/not_contains scorers (mocked Azure).

Harness for CI — does not grade the live model. Optional later: @pytest.mark.live.
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

GOLDEN_TEST_CASES = [
    pytest.param(
        [{"role": "user", "content": "What is the capital of France?"}],
        ["Paris"],
        ["London"],
        id="capital-france",
    ),
    pytest.param(
        [{"role": "user", "content": "Who was the first president of the United States?"}],
        ["George Washington"],
        ["Abraham Lincoln"],
        id="first-us-president",
    ),
    pytest.param(
        [{"role": "user", "content": "What is 2 + 2?"}],
        ["4"],
        ["3"],
        id="basic-math",
    ),
    pytest.param(
        [{"role": "user", "content": "What is the biggest city in the world by population?"}],
        ["Tokyo"],
        ["London"],
        id="biggest-city",
    ),
    pytest.param(
        [{"role": "user", "content": "What is the biggest mammal in the world?"}],
        ["Blue Whale"],
        ["Dog"],
        id="biggest-animal",
    ),
    pytest.param(
        [{"role": "user", "content": "What is the biggest country in the world by area?"}],
        ["Russia"],
        ["United States"],
        id="biggest-country",
    ),
]


def pass_scorer(text, must_contain, must_not_contain):
    text_l = text.lower()
    return all(word.lower() in text_l for word in must_contain) and all(
        word.lower() not in text_l for word in must_not_contain
    )


def test_scorer_missing_must_contain():
    assert not pass_scorer("The capital is London", ["Paris"], ["London"])


def test_scorer_must_not_contain_found():
    assert not pass_scorer(
        "Paris is great, also London is great", ["Paris"], ["London"]
    )


def test_scorer_passes():
    assert pass_scorer("The capital is Paris.", ["Paris"], ["London"])


@pytest.mark.parametrize("messages,must_contain,must_not_contain", GOLDEN_TEST_CASES)
def test_golden_test_cases(mocker, messages, must_contain, must_not_contain):
    mocker.patch(
        "main.chat",
        return_value={
            "provider_message_id": "fake-message-id",
            "completion": {
                "text": "This is a response that contains the words "
                + ",".join(must_contain),
                "model": "fake-model",
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
        },
    )

    r = client.post("/v1/chat", json={"messages": messages})
    response_json = r.json()

    assert r.status_code == 200
    assert pass_scorer(
        response_json["completion"]["text"], must_contain, must_not_contain
    )
    assert "completion" in response_json
