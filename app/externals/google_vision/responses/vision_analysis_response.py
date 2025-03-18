from dataclasses import dataclass


@dataclass
class VisionAnalysisResponse:
    logo_description: str
    label_description: str

    def get_analysis_text(self) -> str:
        analysis_parts = []

        if self.logo_description:
            analysis_parts.append(f"Detected logos: {self.logo_description}")

        if self.label_description:
            analysis_parts.append(f"Detected category: {self.label_description}")

        return ". ".join(analysis_parts) + ("." if analysis_parts else "")
