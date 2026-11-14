
"""Test the post-finish feedback logic without calling the AI Gateway."""

import builtins
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

AGENT_PATH = Path(__file__).resolve().parent / "agent.py"

spec = importlib.util.spec_from_file_location("task2_feedback_agent", AGENT_PATH)
agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)


class MockLLM:
    def __init__(self, *args, **kwargs):
        self.calls = 0
        self.messages = []

    def chat(self, messages, **kwargs):
        self.calls += 1
        self.messages.append([dict(m) for m in messages])

        if self.calls == 1:
            return '{"action":"finish","message":"Done"}'
        return '{"action":"finish","message":"Revised"}'

    def usage_summary(self):
        return "Mock model: no gateway calls"


def fake_execute(action, state):
    if action["action"] == "finish":
        state["finished"] = True
        state["checks_passed"] = True
        state["site_written"] = True
        return {"success": True}
    return {"error": "Unexpected action"}


inputs = iter(["Make the heading clearer", ""])

mock_llm = MockLLM()

with patch.object(agent, "LLMClient", return_value=mock_llm), \
     patch.object(agent, "execute_action", side_effect=fake_execute), \
     patch.object(builtins, "input", side_effect=lambda _: next(inputs)):
    agent.run_agent()

assert mock_llm.calls == 2, f"Expected 2 model calls, got {mock_llm.calls}"

second_call = mock_llm.messages[1]
assert any(
    "Make the heading clearer" in m["content"]
    for m in second_call
), "Human feedback was not passed to the model"

print("\nPASS: Feedback accepted after finish.")
print("PASS: Agent continued after human feedback.")
print("PASS: No real AI Gateway calls were made.")

