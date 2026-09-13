import pytest


GOLDEN_TEST_CASES = [
    # ID, MESSAGES, MUST CONTAIN, MUST NOT CONTAIN
    pytest.param([{"role": "user", "content": "What is the capital of France?"}], ["Paris"], ["London"], id="capital-france"),
    pytest.param([{"role": "user", "content": "Who was the first president of the United States?"}], ["George Washington"], ["Abraham Lincoln"], id="first-us-president"),
    pytest.param([{"role": "user", "content": "What is 2 + 2?"}], ["4"], ["3"], id="basic-math"),
    pytest.param([{"role": "user", "content": "What is the biggest city in the world?"}], ["Tokyo"], ["London"], id="biggest-city"),
    pytest.param([{"role": "user", "content": "What is the biggest animal in the world?"}], ["Blue Whale"], ["Dog"], id="biggest-animal"),
    pytest.param([{"role": "user", "content": "What is the biggest country in the world?"}], ["Russia"], ["United States"], id="biggest-country"),
]

@pytest.mark.parametetrize("messages,must_contain,must_not_contain", GOLDEN_TEST_CASES)
def test_golden_test_cases(messages,must_contain,must_not_contain):
    pass