# API Endpoints Guide

This guide explains how to use the API endpoints in the Ultrasafe Test A NLP system.

## `/nlp/unified`
- **Method**: Use `POST` to send your request.
- **What It Does**: Handles four NLP tasks: classifying text, finding entities, summarizing, and checking sentiment. It works in the background for long tasks. [API Development]
- **What to Send**:
  - `text` (the text to analyze, required).
  - `task` (choose `classify`, `extract_entities`, `summarize`, or `sentiment`, required).
  - `batch` (list of texts for processing many at once, optional). [API Development - Batch Processing]
  - `webhook_url` (where to send results when done, optional). [API Development - Webhook Notifications]
  - `categories` (list of categories for classify, optional, defaults to `["infectious", "chronic", "other"]`).
- **Example Request**:
  ```json
  {
    "text": "Malaria is infectious",
    "task": "classify",
    "categories": ["infectious", "chronic", "other"]
  }
- **Example Response**:
```json
{
  "task_id": "task_20250729005300",
  "result": {"category": "infectious", "confidence": 0.9},
  "completed_at": "2025-07-29T00:53:00",
  "related_docs": ["Malaria is infectious"]
}

## How It Works
- When you send a request, the system checks if the result is saved in Redis. If not, it starts the task.
- For a single text, it uses Celery to process in the background. [API Development - Asynchronous Processing]
- For a batch, it processes all texts at once and returns results directly.
- After processing, it finds similar documents, updates the database, and sends a webhook if you provided a URL.
- Results are saved for 1 hour and can be retrieved with the task_id.
