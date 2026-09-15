"""
Thin golden evals — Phase 5 harness (mocked).

Purpose of THIS file (vs test_mock.py / test_smoke.py):
  - test_mock.py  → API wiring + response shape (Azure mocked once)
  - test_smoke.py → real HTTP to a running server (Kind / port-forward)
  - test_evals.py → golden prompts + contains / not_contains scorers

What these mocks prove:
  Harness works in CI (parametrize → /v1/chat → scorers). No Azure, no tokens.

What they do NOT prove:
  Real model quality. Fake text is built FROM must_contain, so "Paris" asserts
  are almost guaranteed. Grade the model only with @pytest.mark.live (no mock)
  or httpx against a live BASE_URL.

Known nits / gaps (for you to address):
  - must_not_contain is weak under the mock (forbidden words are never inserted)
  - Some facts are fuzzy for lab use (e.g. "biggest city" → Tokyo)
  - Shape/token asserts overlap test_mock.py; keep them light — scorers are the point
  - Not wired into CI yet (mock_test.yml still runs test_mock.py only)
  - No gate-proof test that scorers FAIL on bad text
  - README note on harness vs live still optional

Keep TestClient here (in-process). httpx→localhost is for smoke/live only;
mocker.patch("main.chat") would not affect a separate server process.

Run:
  pytest tests/test_evals.py -v
  pytest tests/test_evals.py::test_golden_test_cases[capital-france] -v
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# Case shape: (messages, must_contain, must_not_contain) + id=slug for -k / node ids
# Example — capital-france:
#   ask "capital of France?" → expect "Paris" in text, not "London"
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
    return (all(word.lower() in text_l for word in must_contain) and 
            all(word.lower() not in text_l for word in must_not_contain))

def test_scorer_missing_must_contain():
    assert not pass_scorer("The capital is London", ["Paris"], ["London"])

def test_scorer_must_not_contain_found():
    assert not pass_scorer("Paris is great, also London is great", ["Paris"], ["London"])

def test_scorer_passes():
    assert pass_scorer("The capital is Paris.", ["Paris"], ["London"])


@pytest.mark.parametrize("messages,must_contain, must_not_contain", GOLDEN_TEST_CASES)
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
    text = response_json["completion"]["text"]
    text_l = text.lower()

    assert r.status_code == 200

    # Core golden scorers (case-insensitive — safer when you later score live replies).
    assert all(word.lower() in text_l for word in must_contain)
    assert all(word.lower() not in text_l for word in must_not_contain)

    # Light shape checks (full contract coverage lives in test_mock.py).
    assert "completion" in response_json
    assert response_json["completion"]["model"] == "fake-model"
