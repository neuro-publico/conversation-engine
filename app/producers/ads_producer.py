import asyncio
import json
import os
import boto3
from typing import Any, Optional

from app.producers.ads_producer_interface import AdsProducerInterface


class AdsProducer(AdsProducerInterface):
    def __init__(self, sqs_client=None):
        if sqs_client is None:
            region = os.getenv("AWS_REGION", "us-east-1")
            endpoint_url = os.getenv("SQS_ENDPOINT_URL")
            access_key = os.getenv("AWS_ACCESS_KEY_ID", "test")
            secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "test")
            sqs_client = boto3.client(
                "sqs",
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                endpoint_url=endpoint_url,
            )
        self.sqs_client = sqs_client

    def _ensure_queue_exists(self) -> None:
        self.sqs_client.create_queue(QueueName=self.queue_name)
        resp = self.sqs_client.get_queue_url(QueueName=self.queue_name)
        self.queue_url = resp["QueueUrl"]

    def get_or_create_queue_url(self, queue_name: str) -> str:
        self.sqs_client.create_queue(QueueName=queue_name)
        resp = self.sqs_client.get_queue_url(QueueName=queue_name)
        return resp["QueueUrl"]

    async def publish_scene(self, queue_name: str, ad_video_id: int, scene: dict[str, Any]) -> str:
        queue_url = self.get_or_create_queue_url(queue_name)
        print(f"Publishing message to {queue_url}")
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
