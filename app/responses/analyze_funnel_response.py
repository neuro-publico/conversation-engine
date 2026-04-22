from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class AnalysisSummary(BaseModel):
    headline: str = Field(description="Short contundent title (6-8 words) summarizing the ad's state")
    overall_health_score: int = Field(description="Score 1-10 of the funnel health", ge=1, le=10)


class CriticalBottleneck(BaseModel):
    title: str = Field(description="Title of the #1 problem")
    financial_impact_text: str = Field(description="Dramatic sentence about lost money/sales")
    diagnosis: str = Field(description="Brief technical explanation")
    action_plan: List[str] = Field(description="Specific steps to fix it today")


class WinningAsset(BaseModel):
    asset_name: str = Field(description="Metric that is performing well (e.g. 'Hook Rate')")
    message: str = Field(description="Reinforcement message — tell user not to touch it")


class SecondaryOptimization(BaseModel):
    metric: str
    advice: str


class AnalyzeFunnelResponse(BaseModel):
    analysis_summary: AnalysisSummary
    critical_bottleneck: CriticalBottleneck
    winning_assets: List[WinningAsset] = Field(default_factory=list)
    secondary_optimizations: List[SecondaryOptimization] = Field(default_factory=list)
    semaforo: Dict[str, str] = Field(
        default_factory=dict,
        description="Traffic light status per rate: 'red' | 'yellow' | 'green'",
    )
