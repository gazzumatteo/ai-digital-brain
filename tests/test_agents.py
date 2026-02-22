"""Tests for agent creation functions."""

from digital_brain.agents.conversation import create_conversation_agent
from digital_brain.agents.predictive import create_predictive_agent
from digital_brain.agents.reflection import create_reflection_agent


class TestAgentCreation:
    def test_conversation_agent(self):
        agent = create_conversation_agent(model="gemini-2.0-flash")
        assert agent.name == "conversation_agent"
        assert len(agent.tools) == 2

    def test_reflection_agent(self):
        agent = create_reflection_agent(model="gemini-2.0-flash")
        assert agent.name == "reflection_agent"
        assert len(agent.tools) == 4

    def test_predictive_agent(self):
        agent = create_predictive_agent(model="gemini-2.0-flash")
        assert agent.name == "predictive_agent"
        assert len(agent.tools) == 2

    def test_conversation_agent_has_output_key(self):
        agent = create_conversation_agent(model="gemini-2.0-flash")
        assert agent.output_key == "last_response"

    def test_reflection_agent_has_output_key(self):
        agent = create_reflection_agent(model="gemini-2.0-flash")
        assert agent.output_key == "reflection_summary"
