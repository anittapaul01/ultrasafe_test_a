import httpx
import os
from dotenv import load_dotenv
import logging

load_dotenv()
API_KEY = os.getenv("API_KEY")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def notify_webhook(webhook_url: str, data: dict):
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}
        try:
            response = await client.post(webhook_url, json=data, headers=headers)
            response.raise_for_status()
            logger.info(f"Webhook notified successfully: {webhook_url}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Webhook notification failed: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"Webhook notification error: {e}")