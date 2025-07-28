import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Optional
from enum import Enum
import redis.asyncio as redis
from celery import Celery
from datetime import datetime
from contextlib import asynccontextmanager
from .nlp_tasks import process_nlp_task
from .rag import retrieve_similar_docs, rerank_results, update_vector_db, check_qdrant_data, initialize_qdrant_collections
from .utils import notify_webhook
import logging
import os
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL)

# Celery configuration
celery_app = Celery(
    "nlp_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    broker_connection_retry_on_startup=True
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await initialize_qdrant_collections()
        await check_qdrant_data()
        yield
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant: {e}")
        raise
    finally:
        await redis_client.close()
        logger.info("Shutting down application...")
        logger.info("Shutdown complete.")

app = FastAPI(
    lifespan=lifespan,
    title="NLP Unified API",
    description="API for advanced NLP tasks with RAG integration and task queuing",
    version="1.0.0"
)

class TaskType(str, Enum):
    CLASSIFY = "classify"
    EXTRACT_ENTITIES = "extract_entities"
    SUMMARIZE = "summarize"
    SENTIMENT = "sentiment"

class NLPRequest(BaseModel):
    text: str
    task: TaskType
    batch: Optional[List[str]] = None
    webhook_url: Optional[str] = None
    categories: List[str] = ["infectious", "chronic", "other"]

class TaskResult(BaseModel):
    task_id: str
    result: Dict
    completed_at: str
    related_docs: Optional[List[str]] = None

@celery_app.task
def process_nlp_task_background(task_id: str, text: str, task: str, categories: Optional[List[str]], webhook_url: Optional[str]):
    result = asyncio.run(process_nlp_task(text, task, categories))
    category_hint = categories[0] if task == "classify" and categories else None
    similar_docs = asyncio.run(retrieve_similar_docs(task, text, category=category_hint))
    reranked_docs = asyncio.run(rerank_results(task, similar_docs, text))
    result["related_docs"] = reranked_docs
    asyncio.run(update_vector_db(task, text, result))
    asyncio.run(redis_client.setex(f"{task_id}_{task}", 3600, str(result)))
    if webhook_url:
        asyncio.run(notify_webhook(webhook_url, {
            "task_id": task_id,
            "result": result,
            "completed_at": datetime.now().isoformat()
        }))
    return result

@app.post("/nlp/unified", response_model=TaskResult)
async def unified_nlp(request: NLPRequest, background_tasks: BackgroundTasks):
    task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    cache_key = f"{task_id}_{request.task}"
    
    # Check Redis cache
    cached_result = await redis_client.get(cache_key)
    if cached_result:
        return TaskResult(
            task_id=task_id,
            result=eval(cached_result),
            completed_at=datetime.now().isoformat()
        )

    try:
        if request.batch:
            tasks = [process_nlp_task(text, request.task, request.categories if request.task == TaskType.CLASSIFY else None) for text in request.batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            result = {"batch_results": dict(zip(request.batch, results))}
            await redis_client.setex(cache_key, 3600, str(result))
            if request.webhook_url:
                background_tasks.add_task(notify_webhook, request.webhook_url, {
                    "task_id": task_id,
                    "result": result,
                    "completed_at": datetime.now().isoformat()
                })
            return TaskResult(
                task_id=task_id,
                result=result,
                completed_at=datetime.now().isoformat()
            )
        else:
            background_tasks.add_task(
                process_nlp_task_background,
                task_id,
                request.text,
                request.task,
                request.categories if request.task == TaskType.CLASSIFY else None,
                request.webhook_url
            )
            result = await process_nlp_task(request.text, request.task, request.categories if request.task == TaskType.CLASSIFY else None)
            category_hint = request.categories[0] if request.task == TaskType.CLASSIFY and request.categories else None
            similar_docs = await retrieve_similar_docs(request.task, request.text, category=category_hint)
            reranked_docs = await rerank_results(request.task, similar_docs, request.text)
            result["related_docs"] = reranked_docs
            await update_vector_db(request.task, request.text, result)
            await redis_client.setex(cache_key, 3600, str(result))
            return TaskResult(
                task_id=task_id,
                result=result,
                completed_at=datetime.now().isoformat(),
                related_docs=reranked_docs
            )
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=4)