"""Interface for the new ads video Director Creative service."""

from abc import ABC, abstractmethod

from app.requests.video_studio_draft_request import VideoStudioDraftRequest
from app.responses.video_studio_draft_response import VideoStudioDraftReadyPayload


class VideoStudioServiceInterface(ABC):
    @abstractmethod
    async def run_director(self, request: VideoStudioDraftRequest) -> VideoStudioDraftReadyPayload:
        """Run the Director Creative pipeline synchronously and return the structured payload.

        Internally:
          1. Loads the agent_config from agent-config service.
          2. Renders the prompt locally with all variables (including
             creative_patterns_json from metadata).
          3. Calls Gemini direct (no LangChain) with structured output forced.
          4. Validates the parsed output against business rules.
          5. Persists the call in prompt_logs (log_type="video_director") with
             draft_reference_id in metadata.
          6. Returns the validated payload.

        Raises:
            VideoStudioError: if any step fails after retries. Caller is
            responsible for the callback / state update on the ecommerce side.
        """

    @abstractmethod
    async def run_and_callback(self, request: VideoStudioDraftRequest) -> None:
        """Wrapper that runs the director and POSTs the result to callback_url.

        Used by the async endpoint. Never raises — errors are sent to the
        callback as `status="error"` payloads.
        """
