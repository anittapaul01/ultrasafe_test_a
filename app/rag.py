import nest_asyncio
nest_asyncio.apply()

from qdrant_client import QdrantClient
from qdrant_client.http import models
import asyncio
import httpx
import os
import csv
from dotenv import load_dotenv
from typing import List, Dict, Optional
from fastapi import HTTPException
import logging
import json

load_dotenv()
API_KEY = os.getenv("API_KEY")
BASE_URL_EMBED = "https://api.us.inc/usf/v1/embed"
BASE_URL_RERANK = "https://api.us.inc/usf/v1/embed"
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Qdrant client with fallback to HTTP
def initialize_qdrant_client():
    try:
        client = QdrantClient(
            url=QDRANT_URL,
            prefer_grpc=True,
            timeout=10.0
        )
        # Test gRPC connection
        client.get_collections()
        logger.info("Qdrant client initialized with gRPC")
        return client
    except Exception as e:
        logger.warning(f"gRPC connection failed: {e}. Falling back to HTTP.")
        client = QdrantClient(
            url=QDRANT_URL,
            prefer_grpc=False,
            timeout=10.0
        )
        return client

client = initialize_qdrant_client()

async def create_qdrant_collections():
    """Create Qdrant collections if they don't exist, with error handling and retry."""
    for task in ["classify", "extract_entities", "summarize", "sentiment"]:
        for attempt in range(3):  # Retry up to 3 times
            try:
                # Check if collection exists
                collections = client.get_collections().collections
                if any(collection.name == task for collection in collections):
                    logger.info(f"Collection {task} already exists, skipping creation")
                    break
                client.recreate_collection(
                    collection_name=task,
                    vectors_config=models.VectorParams(size=1024, distance=models.Distance.COSINE),
                    shard_number=2,
                    replication_factor=2
                )
                logger.info(f"Created collection {task}")
                break
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for collection {task}: {e}")
                if attempt == 2:
                    logger.error(f"Failed to create collection {task} after 3 attempts: {e}")
                    raise HTTPException(status_code=500, detail=f"Failed to create collection {task}: {str(e)}")
                await asyncio.sleep(2)  # Wait 2 seconds before retrying

def initialize_from_csv(csv_path: str, limit: int = 200, max_length: int = 2000) -> tuple:
    try:
        with open(csv_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            classify_data = []
            extract_entities_data = []
            summarize_data = []
            sentiment_data = []
            count = 0
            for row in reader:
                if count >= limit:
                    break
                disease = row['disease'].strip()
                description = row['description'].strip()
                if not disease or not description:  # Skip empty strings
                    logger.warning(f"Skipping empty disease or description at row {count + 2}")
                    continue
                classify_text = f"{disease}: {description[:max_length - len(disease) - 2]}" if len(description) > max_length - len(disease) - 2 else f"{disease}: {description}"
                extract_text = description[:max_length] if len(description) > max_length else description
                summarize_text = description[:max_length] if len(description) > max_length else description
                sentiment_text = f"Information on {disease}: {description[:max_length - len(disease) - 15]}" if len(description) > max_length - len(disease) - 15 else f"Information on {disease}: {description}"
                classify_data.append(classify_text)
                extract_entities_data.append(extract_text)
                summarize_data.append(summarize_text)
                sentiment_data.append(sentiment_text)
                count += 1
            logger.info(f"Loaded {count} records from {csv_path}")
            return classify_data, extract_entities_data, summarize_data, sentiment_data
    except Exception as e:
        logger.error(f"Failed to initialize from CSV: {e}")
        raise

csv_path = "data/filtered_diseases.csv"
classify_texts, extract_entities_texts, summarize_texts, sentiment_texts = initialize_from_csv(
    csv_path, limit=int(os.getenv("CSV_LIMIT", 200)), max_length=int(os.getenv("CSV_MAX_LENGTH", 2000))
)

async def initialize_qdrant_collections():
    try:
        await create_qdrant_collections()
        tasks = [
            get_embeddings_and_upsert("classify", classify_texts),
            get_embeddings_and_upsert("extract_entities", extract_entities_texts),
            get_embeddings_and_upsert("summarize", summarize_texts),
            get_embeddings_and_upsert("sentiment", sentiment_texts)
        ]
        await asyncio.gather(*tasks)
        logger.info("Qdrant collections initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant collections: {e}")
        raise

async def get_embeddings_and_upsert(task: str, texts: List[str]):
    try:
        # Batch texts into chunks of 32 to respect API limits
        batch_size = 32
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            embeddings = await get_embeddings(batch_texts)
            client.upsert(
                collection_name=task,
                points=models.Batch(
                    ids=list(range(i, i + len(batch_texts))),
                    payloads=[{"text": text} for text in batch_texts],
                    vectors=embeddings
                )
            )
            logger.info(f"Upserted {len(batch_texts)} points to {task} collection (batch {i//batch_size + 1})")
    except Exception as e:
        logger.error(f"Failed to upsert embeddings for {task}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upsert embeddings: {str(e)}")

async def get_embeddings(texts: List[str]) -> List[List[float]]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"x-api-key": API_KEY}
        payload = {"model": "usf1-embed", "input": texts}
        try:
            response = await client.post(f"{BASE_URL_EMBED}/embeddings", json=payload, headers=headers)
            response.raise_for_status()
            embeddings = [emb["embedding"] for emb in response.json()["result"]["data"]]
            if len(embeddings) > 0 and len(embeddings[0]) != 1024:
                raise ValueError(f"Expected 1024D embeddings, got {len(embeddings[0])}D")
            return embeddings
        except httpx.HTTPStatusError as e:
            logger.error(f"Embedding API error: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail="Embedding API request failed")
        except Exception as e:
            logger.error(f"Embedding processing error: {e}")
            raise HTTPException(status_code=500, detail=f"Embedding processing error: {str(e)}")

async def update_vector_db(task: str, prompt: str, result: Dict):
    try:
        embedding = (await get_embeddings([f"{prompt} -> {json.dumps(result)}"]))[0]
        point_id = client.count(collection_name=task).count
        client.upsert(
            collection_name=task,
            points=models.Batch(
                ids=[point_id],
                payloads=[{"text": f"{prompt} -> {json.dumps(result)}"}],
                vectors=[embedding]
            )
        )
        logger.info(f"Updated vector DB for {task} with point ID {point_id}")
    except Exception as e:
        logger.error(f"Failed to update vector DB for {task}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update vector DB: {str(e)}")

async def retrieve_similar_docs(task: str, query: str, category: Optional[str] = None) -> List[str]:
    try:
        query_embedding = (await get_embeddings([query]))[0]
        search_result = client.search(
            collection_name=task,
            query_vector=query_embedding,
            limit=5,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="text",
                        match=models.MatchText(text=category.lower())
                    )
                ]
            ) if category and task == "classify" else None
        )
        logger.info(f"Retrieved {len(search_result)} documents for {task}")
        return [hit.payload["text"] for hit in search_result]
    except Exception as e:
        logger.error(f"Failed to retrieve documents for {task}: {e}")
        return []

async def rerank_results(task: str, results: List[str], query: str) -> List[str]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"x-api-key": API_KEY}
        if not results:
            logger.warning(f"No documents to rerank for query: {query}")
            return results
        payload = {"model": "usf1-rerank", "input": {"query": query, "documents": results}}
        logger.debug(f"Reranker payload: {payload}")
        try:
            response = await client.post(f"{BASE_URL_RERANK}/reranker", json=payload, headers=headers)
            response.raise_for_status()
            return response.json().get("ranked_documents", results)
        except httpx.HTTPStatusError as e:
            logger.error(f"Reranker API error: {e.response.status_code} - {e.response.text}")
            return results
        except Exception as e:
            logger.error(f"Reranker processing error: {e}")
            return results

async def check_qdrant_data():
    try:
        collections = client.get_collections().collections
        logger.info(f"Collections: {[c.name for c in collections]}")
        for task in ["classify", "extract_entities", "summarize", "sentiment"]:
            count = client.count(collection_name=task).count
            logger.info(f"{task} collection has {count} points")
    except Exception as e:
        logger.error(f"Failed to check Qdrant data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check Qdrant data: {str(e)}")