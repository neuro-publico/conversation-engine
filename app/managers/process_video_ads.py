import asyncio
import os
import boto3
from typing import Optional

from app.requests.generate_video_request import GenerateAdScenesRequest
from app.managers.process_video_ads_interface import ProcessVideoAdsInterface
from app.repositories.ad_video_repository import AdVideoRepository
from app.models.ad import AdVideoStatus


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

    async def publish(self, request: GenerateAdScenesRequest, ad_video_id: int) -> str:
        if not self.queue_url:
            raise ValueError("SQS_QUEUE_URL no está configurada")

        print(self.queue_url)
        await asyncio.to_thread(
            self.sqs_client.send_message,
            QueueUrl=self.queue_url,
            MessageBody=request.ad_text,
            MessageAttributes={
                "ad_video_id": {"StringValue": str(ad_video_id), "DataType": "Number"},
            },
        )
        print("ENQUEUED")
        return "ENQUEUED"

    async def listen_forever(self) -> None:
        print("LISTENING")
        if not self.queue_url:
            raise ValueError("SQS_QUEUE_URL no está configurada")
        while True:
            resp = await asyncio.to_thread(
                self.sqs_client.receive_message,
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=5,
                WaitTimeSeconds=5,
                MessageAttributeNames=["All"],
            ) or {}
            messages = resp.get("Messages", [])
            if not messages:
                await asyncio.sleep(1)
                continue
            for msg in messages:
                try:
                    attrs = (msg.get("MessageAttributes") or {})
                    ad_video_id_attr = attrs.get("ad_video_id") or {}
                    ad_video_id_str = ad_video_id_attr.get("StringValue")
                    await asyncio.sleep(15)
                    if ad_video_id_str:
                        await self.mark_in_progress(int(ad_video_id_str))
                finally:
                    # borrar el mensaje
                    receipt = msg.get("ReceiptHandle")
                    if receipt:
                        await asyncio.to_thread(self.sqs_client.delete_message, QueueUrl=self.queue_url, ReceiptHandle=receipt)

    async def mark_in_progress(self, ad_video_id: int) -> None:
        await self.repository.update_ad_video(ad_video_id, {
            "status": AdVideoStatus.IN_PROGRESS.value,
            "progress": 10,
        })
