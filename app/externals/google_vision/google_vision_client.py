import aiohttp
from app.configurations.config import GOOGLE_VISION_API_KEY
from app.externals.google_vision.responses.vision_analysis_response import VisionAnalysisResponse


async def analyze_image(image_base64: str) -> VisionAnalysisResponse:
    vision_api_url = f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_VISION_API_KEY}"

    payload = {
        "requests": [{
            "image": {
                "content": image_base64
            },
            "features": [
                {
                    "type": "LABEL_DETECTION",
                    "maxResults": 3
                },
                {
                    "type": "LOGO_DETECTION",
                    "maxResults": 1
                }
            ]
        }]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
                vision_api_url,
                json=payload,
                headers={"Content-Type": "application/json"}
        ) as response:
            if response.status != 200:
                raise Exception(f"Error en Google Vision API: {await response.text()}")

            data = await response.json()

            logo_description = ""
            if data["responses"][0].get("logoAnnotations"):
                logo = data["responses"][0]["logoAnnotations"][0]
                if logo.get("score", 0) > 0.65:
                    logo_description = logo["description"]

            labels = []
            if data["responses"][0].get("labelAnnotations"):
                labels = [
                    label["description"]
                    for label in data["responses"][0]["labelAnnotations"]
                    if label.get("score", 0) > 0.65
                ]

            label_description = ", ".join(labels)

            return VisionAnalysisResponse(
                logo_description=logo_description,
                label_description=label_description
            )
