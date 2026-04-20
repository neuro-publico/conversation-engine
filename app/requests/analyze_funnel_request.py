from typing import List, Optional

from pydantic import BaseModel, Field


class FunnelMetricsRaw(BaseModel):
    impressions: int = 0
    video_3s: int = 0
    video_50: int = 0
    link_clicks: int = 0
    spend: float = 0.0
    purchases: int = 0
    thruplay: int = 0


class FunnelMetricsRates(BaseModel):
    hook_rate: float = Field(default=0.0, description="video_views / impressions")
    thruplay_rate: float = Field(default=0.0, description="thruplay / impressions")
    ctr: float = Field(default=0.0, description="click-through rate (percent, e.g. 1.5 for 1.5%)")
    cpc: float = Field(default=0.0, description="cost per click")
    roas: float = Field(default=0.0, description="return on ad spend")
    click_to_purchase: float = Field(default=0.0, description="purchases / link_clicks")


class FunnelAdContext(BaseModel):
    ad_id: Optional[str] = None
    ad_name: Optional[str] = None
    campaign_name: Optional[str] = None
    effective_status: Optional[str] = None
    date_start: Optional[str] = None
    date_end: Optional[str] = None


class AnalyzeFunnelRequest(BaseModel):
    ad: FunnelAdContext = Field(default_factory=FunnelAdContext)
    raw: FunnelMetricsRaw = Field(default_factory=FunnelMetricsRaw)
    rates: FunnelMetricsRates = Field(default_factory=FunnelMetricsRates)
    benchmark_profile: str = Field(
        default="dropshipping_prospecting",
        description="Which benchmark profile to apply for the traffic-light thresholds",
    )
