from abc import ABC, abstractmethod

from app.requests.analyze_funnel_request import AnalyzeFunnelRequest
from app.responses.analyze_funnel_response import AnalyzeFunnelResponse


class FunnelAnalysisServiceInterface(ABC):
    @abstractmethod
    async def analyze(self, request: AnalyzeFunnelRequest) -> AnalyzeFunnelResponse:
        """Run the "Cerebro Estratégico" agent on the provided funnel metrics."""
        raise NotImplementedError
