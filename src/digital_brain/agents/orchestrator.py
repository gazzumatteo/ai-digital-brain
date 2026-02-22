"""DigitalBrainOrchestrator — Ties agents together with session management."""

from __future__ import annotations

import logging
from typing import AsyncIterator

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, Session
from google.genai import types

from digital_brain.agents.conversation import create_conversation_agent
from digital_brain.agents.predictive import create_predictive_agent
from digital_brain.agents.reflection import create_reflection_agent
from digital_brain.config import Settings, get_settings

logger = logging.getLogger(__name__)

APP_NAME = "digital_brain"


class DigitalBrainOrchestrator:
    """Manages the lifecycle of Digital Brain agents and sessions."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._session_service = InMemorySessionService()

        model = self._settings.llm.model
        self._conversation_agent = create_conversation_agent(model=model)
        self._reflection_agent = create_reflection_agent(model=model)
        self._predictive_agent = create_predictive_agent(model=model)

        self._conversation_runner = Runner(
            agent=self._conversation_agent,
            app_name=APP_NAME,
            session_service=self._session_service,
        )
        self._reflection_runner = Runner(
            agent=self._reflection_agent,
            app_name=APP_NAME,
            session_service=self._session_service,
        )
        self._predictive_runner = Runner(
            agent=self._predictive_agent,
            app_name=APP_NAME,
            session_service=self._session_service,
        )

    async def get_or_create_session(
        self, user_id: str, session_id: str | None = None
    ) -> Session:
        """Get existing session or create a new one."""
        sid = session_id or f"session_{user_id}"
        existing = await self._session_service.get_session(
            app_name=APP_NAME, user_id=user_id, session_id=sid,
        )
        if existing:
            return existing
        return await self._session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=sid,
            state={"user_id": user_id},
        )

    async def chat(
        self,
        user_id: str,
        message: str,
        session_id: str | None = None,
        enable_prediction: bool = True,
    ) -> str:
        """Send a message to the Conversation Agent and return the response.

        Optionally runs the Predictive Agent first to pre-load context.
        """
        session = await self.get_or_create_session(user_id, session_id)

        # --- Predictive pre-loading (optional) ---
        if enable_prediction:
            try:
                await self._run_predictive(user_id, session)
            except Exception:
                logger.warning("Predictive pre-loading failed, continuing without it", exc_info=True)

        # --- Conversation ---
        content = types.Content(role="user", parts=[types.Part(text=message)])

        response_text = ""
        for event in self._conversation_runner.run(
            user_id=user_id,
            session_id=session.id,
            new_message=content,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                response_text = event.content.parts[0].text

        return response_text or "No response generated."

    async def reflect(self, user_id: str) -> str:
        """Run the Reflection Agent for a user (memory consolidation)."""
        session = await self.get_or_create_session(user_id, f"reflection_{user_id}")

        settings = self._settings
        prompt = (
            f"Perform memory consolidation for user {user_id}. "
            f"Minimum memories for insight: {settings.reflection.min_memories}."
        )
        content = types.Content(role="user", parts=[types.Part(text=prompt)])

        response_text = ""
        for event in self._reflection_runner.run(
            user_id=user_id,
            session_id=session.id,
            new_message=content,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                response_text = event.content.parts[0].text

        logger.info("Reflection completed for user %s", user_id)
        return response_text or "Reflection completed with no summary."

    async def _run_predictive(self, user_id: str, session: Session) -> None:
        """Run the Predictive Agent and inject pre-loaded context into session state."""
        pred_session = await self.get_or_create_session(user_id, f"predict_{user_id}")

        prompt = f"Predict and pre-load context for user {user_id}."
        content = types.Content(role="user", parts=[types.Part(text=prompt)])

        preloaded = ""
        for event in self._predictive_runner.run(
            user_id=user_id,
            session_id=pred_session.id,
            new_message=content,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                preloaded = event.content.parts[0].text

        if preloaded:
            # Inject pre-loaded context into the conversation session state
            session.state["preloaded_context"] = preloaded
            logger.debug("Pre-loaded context for user %s: %s", user_id, preloaded[:200])
