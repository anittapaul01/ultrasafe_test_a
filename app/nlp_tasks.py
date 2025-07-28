import httpx
import os
import json
import re
from dotenv import load_dotenv
from typing import Dict, List, Optional
from fastapi import HTTPException
import logging

load_dotenv()
API_KEY = os.getenv("API_KEY")
BASE_URL_CHAT = "https://api.us.inc/usf/v1/hiring"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def process_nlp_task(text: str, task: str, categories: Optional[List[str]] = None) -> Dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}
        prompt = ""
        if task == "classify":
            prompt = f"Classify '{text}' as a medical condition into {categories}. Return JSON with 'category' and 'confidence' (0-1)."
        elif task == "extract_entities":
            prompt = f"Extract entities from '{text}'. Return JSON with 'entities' as a list."
        elif task == "summarize":
            prompt = f"Summarize '{text}'. Return JSON with 'summary'."
        elif task == "sentiment":
            prompt = f"Determine the sentiment of '{text}'. Return JSON with 'sentiment' ('positive', 'negative', 'neutral') and 'score' (0-1)."

        payload = {
            "model": "usf1-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "stream": False,
            "max_tokens": 1024
        }

        try:
            response = await client.post(f"{BASE_URL_CHAT}/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            result_data = response.json()
            content = result_data.get("choices", [{}])[0].get("message", {}).get("content", "")

            if isinstance(content, str) and content.strip():
                json_str = re.sub(r'^```json\n|\n```$', '', content, flags=re.MULTILINE).strip()
                if json_str:
                    return json.loads(json_str)
                else:
                    raise ValueError("No valid JSON found in content")
            else:
                raise ValueError("API returned invalid or empty content")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail="API request failed")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}, Content: {content}")
            if task == "classify":
                return {"category": "unknown", "confidence": 0.5}
            elif task == "extract_entities":
                return {"entities": []}
            elif task == "summarize":
                return {"summary": "No summary available"}
            elif task == "sentiment":
                return {"sentiment": "neutral", "score": 0.5}
        except Exception as e:
            logger.error(f"Error processing response: {e}")
            raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")