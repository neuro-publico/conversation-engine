import os
import boto3
from typing import Optional, Tuple


def build_sqs_client() -> any:
	region = os.getenv("AWS_REGION", "us-east-1")
	endpoint_url = os.getenv("SQS_ENDPOINT_URL")
	access_key = os.getenv("AWS_ACCESS_KEY_ID", "test")
	secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "test")
	return boto3.client(
		"sqs",
		region_name=region,
		aws_access_key_id=access_key,
		aws_secret_access_key=secret_key,
		endpoint_url=endpoint_url,
	)


def resolve_queue_urls(sqs_client) -> Tuple[str, str]:
	human_queue = os.getenv("SQS_HUMAN_QUEUE_URL")
	animated_queue = os.getenv("SQS_ANIMATED_QUEUE_URL")
	if human_queue and animated_queue:
		return human_queue, animated_queue

	from app.producers.ads_producer import AdsProducer
	producer = AdsProducer(sqs_client=sqs_client)
	human_queue_url = human_queue or producer.get_or_create_queue_url("generate_human_video")
	animated_queue_url = animated_queue or producer.get_or_create_queue_url("generate_animated_image_video")
	return human_queue_url, animated_queue_url 