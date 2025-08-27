import asyncio
import json
from typing import Any, Dict, Optional, Callable

from app.listeners.ads_listener_interface import AdsListenerInterface
from app.managers.process_video_ads_interface import ProcessVideoAdsInterface
from app.repositories.ad_video_repository import AdVideoRepository
from app.models.ad import AdVideoStatus


class AdsListener(AdsListenerInterface):
    def __init__(self, sqs_client, handler: ProcessVideoAdsInterface, human_queue_url: Optional[str], animated_queue_url: Optional[str]):
        self.sqs_client = sqs_client
        self.handler = handler
        self.human_queue_url = human_queue_url
        self.animated_queue_url = animated_queue_url
        self.repository = AdVideoRepository()

    async def listen_forever(self) -> None:
        await asyncio.gather(
            self._listen_queue(self.human_queue_url, label="HUMAN"),
            self._listen_queue(self.animated_queue_url, label="ANIMATED"),
        )

    async def _listen_queue(self, queue_url: str, label: str) -> None:
        while True:
            try:
                resp = await asyncio.to_thread(
                    self.sqs_client.receive_message,
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=5,
                    WaitTimeSeconds=5,
                    MessageAttributeNames=["All"],
                )
                resp = resp or {}
                messages = resp.get("Messages", [])
                if not messages:
                    await asyncio.sleep(1)
                    continue
                for msg in messages:
                    try:
                        body_str = msg.get("Body") or ""
                        attrs = msg.get("MessageAttributes") or {}
                        scene_type_attr, ad_video_id = self._parse_attributes(attrs)
                        parsed_body = self._parse_body(body_str)

                        if ad_video_id is not None:
                            await self.repository.update_ad_video(ad_video_id, {
                                "status": AdVideoStatus.IN_PROGRESS.value,
                            })

                        await self._dispatch_scene(label, scene_type_attr, parsed_body)
                    finally:
                        receipt = msg.get("ReceiptHandle")
                        if receipt:
                            await asyncio.to_thread(
                                self.sqs_client.delete_message,
                                QueueUrl=queue_url,
                                ReceiptHandle=receipt,
                            )
            except Exception as e:
                print(f"[{label}] Error receiving messages: {e}")
                await asyncio.sleep(2)

    def _parse_attributes(self, attrs: Dict[str, Any]) -> tuple[Optional[str], Optional[int]]:
        scene_type_attr = (attrs.get("scene_type") or {}).get("StringValue")
        ad_video_id_str = (attrs.get("ad_video_id") or {}).get("StringValue")
        ad_video_id = None
        if ad_video_id_str is not None:
            try:
                ad_video_id = int(ad_video_id_str)
            except Exception:
                ad_video_id = None
        return scene_type_attr, ad_video_id

    def _parse_body(self, body: str) -> Dict[str, Any]:
        try:
            return json.loads(body)
        except Exception:
            return {"raw": body}

    async def _dispatch_scene(self, label: str, scene_type: Optional[str], parsed_body: Dict[str, Any]) -> None:
        effective_type = scene_type or ("human_scene" if label == "HUMAN" else ("animated_scene" if label == "ANIMATED" else None))
        if effective_type == "human_scene":
            await self.handler.handle_human_scene(parsed_body)
        elif effective_type == "animated_scene":
            await self.handler.handle_animated_scene(parsed_body)
        else:
            print(f"[{label}] Unknown scene_type. Body={parsed_body}")

    async def handle_human_scene(self, scene: Dict[str, Any]) -> None:
        await self.handler.handle_human_scene(scene)

    async def handle_animated_scene(self, scene: Dict[str, Any]) -> None:
        await self.handler.handle_animated_scene(scene)


