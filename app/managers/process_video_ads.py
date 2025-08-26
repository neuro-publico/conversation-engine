import asyncio
import os
import boto3
import json
from typing import Optional, Dict, Any

from app.requests.generate_video_request import GenerateAdScenesRequest
from app.managers.process_video_ads_interface import ProcessVideoAdsInterface
from app.repositories.ad_video_repository import AdVideoRepository
from app.models.ad import AdVideoStatus

HUMAN_QUEUE_NAME = "generate_human_video"
ANIMATED_QUEUE_NAME = "generate_animated_image_video"


class ProcessVideoAds(ProcessVideoAdsInterface):
    def __init__(self, queue_url: Optional[str] = None):
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.endpoint_url = os.getenv("SQS_ENDPOINT_URL")
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID", "test")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "test")

        # Cliente SQS (usa endpoint xlocal si está definido)
        self.sqs_client = boto3.client(
            "sqs",
            region_name=self.region,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            endpoint_url=self.endpoint_url,
        )

        self.queue_url = queue_url or os.getenv("SQS_QUEUE_URL")
        self.queue_name = os.getenv("SQS_QUEUE_NAME")

        if not self.queue_url:
            if not self.queue_name:
                raise ValueError("Debe configurar SQS_QUEUE_URL o SQS_QUEUE_NAME")
            self._ensure_queue_exists()

        self.repository = AdVideoRepository()

    def _ensure_queue_exists(self) -> None:
        self.sqs_client.create_queue(QueueName=self.queue_name)
        resp = self.sqs_client.get_queue_url(QueueName=self.queue_name)
        self.queue_url = resp["QueueUrl"]

    def _get_or_create_queue_url(self, queue_name: str) -> str:
        self.sqs_client.create_queue(QueueName=queue_name)
        resp = self.sqs_client.get_queue_url(QueueName=queue_name)
        return resp["QueueUrl"]

    async def publish(self, request: GenerateAdScenesRequest, ad_video_id: int) -> str:
        if not self.queue_url:
            raise ValueError("SQS_QUEUE_URL no está configurada")

        await asyncio.to_thread(
            self.sqs_client.send_message,
            QueueUrl=self.queue_url,
            MessageBody=request.ad_text,
            MessageAttributes={
                "ad_video_id": {"StringValue": str(ad_video_id), "DataType": "Number"},
            },
        )
        return "ENQUEUED"

    async def publish_scene(self, queue_name: str, ad_video_id: int, scene: Dict[str, Any]) -> str:
        queue_url = self._get_or_create_queue_url(queue_name)
        body = json.dumps({
            "ad_video_id": ad_video_id,
            "sort": scene.get("sort"),
            "type": scene.get("type"),
            "content": scene.get("content"),
        })
        await asyncio.to_thread(
            self.sqs_client.send_message,
            QueueUrl=queue_url,
            MessageBody=body,
            MessageAttributes={
                "ad_video_id": {"StringValue": str(ad_video_id), "DataType": "Number"},
                "scene_type": {"StringValue": str(scene.get("type")), "DataType": "String"},
                "scene_sort": {"StringValue": str(scene.get("sort")), "DataType": "Number"},
            },
        )
        return "ENQUEUED"

    def _resolve_scene_queue_urls(self) -> tuple[str, str]:
        human_queue_url = os.getenv("SQS_HUMAN_QUEUE_URL") or self._get_or_create_queue_url(HUMAN_QUEUE_NAME)
        animated_queue_url = os.getenv("SQS_ANIMATED_QUEUE_URL") or self._get_or_create_queue_url(ANIMATED_QUEUE_NAME)
        return human_queue_url, animated_queue_url

    async def _receive_messages(self, queue_url: str) -> Dict[str, Any]:
        return await asyncio.to_thread(
            self.sqs_client.receive_message,
            QueueUrl=queue_url,
            MaxNumberOfMessages=5,
            WaitTimeSeconds=5,
            MessageAttributeNames=["All"],
        )

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
            await self.handle_human_scene(parsed_body)
        elif effective_type == "animated_scene":
            await self.handle_animated_scene(parsed_body)
        else:
            print(f"[{label}] Unknown scene_type. Body={parsed_body}")

    # Public listener API
    async def listen_forever(self) -> None:
        print("LISTENING")
        human_queue_url, animated_queue_url = self._resolve_scene_queue_urls()
        await asyncio.gather(
            self._listen_queue(human_queue_url, label="HUMAN"),
            self._listen_queue(animated_queue_url, label="ANIMATED"),
        )

    async def _listen_queue(self, queue_url: str, label: str) -> None:
        while True:
            try:
                resp = (await self._receive_messages(queue_url)) or {}
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
                            await self.mark_in_progress(ad_video_id)

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

    async def mark_in_progress(self, ad_video_id: int) -> None:
        await self.repository.update_ad_video(ad_video_id, {
            "status": AdVideoStatus.IN_PROGRESS.value,
            "progress": 10,
        })

    async def handle_human_scene(self, scene: Dict[str, Any]) -> None:
        print(f"Handling human scene: {scene}")

    async def handle_animated_scene(self, scene: Dict[str, Any]) -> None:
        print(f"Handling animated scene: {scene}")