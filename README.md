# Ultrasafe Test A: Unified NLP System

Welcome to the Ultrasafe Test A project! This is a FastAPI application that handles advanced NLP tasks like classifying text, finding entities, summarizing, and checking sentiment. It uses a smart system to find similar documents and works fast even with many requests.

## Installation

Follow these steps to set up the project on your computer.

1. **Clone the Repository**
   ```bash
   git clone https://github.com/anittapaul01/ultrasafe_test_a.git
   cd ultrasafe_test_a

2. **Setup Environment, Install requirements and prerequisites**
 
3. **Run with Docker (Optional)**
Start Redis and Qdrant databases:
```bash
docker-compose up -d
```
- This sets up the system to run smoothly with multiple servers.

4. **Run the Application**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --workers 4
```

5. **Test the API**
Use curl to try it out:
```bash
curl -X POST "http://localhost:8000/nlp/unified" -d '{"text": "Malaria is infectious", "task": "classify", "categories": ["infectious", "chronic", "other"]}' -H "Content-Type: application/json"
```
- You’ll get a response with a task_id and results.

**What the System Does**
*Main Features*
- Tasks: 
1. Classify: Puts text into groups (e.g., "infectious") with a confidence score.
2. Extract Entities: Finds important words (e.g., "Malaria").
3. Summarize: Shortens text to key points.
4. Sentiment: Checks if text is happy, sad, or neutral with a score.
   
- Batch Processing: Handles many texts at once.
- Background Work: Uses Celery to process tasks separately, so it doesn’t slow down.
- Webhooks: Sends results to a URL you provide when done.
- Smart Search: Finds similar documents to improve answers.
- Fast Storage: Saves results for 1 hour to avoid redoing work.
  
**How It Works**
- The app starts by setting up Qdrant with data from filtered_diseases.csv.
- When you send a request to /nlp/unified, it checks if the result is saved in Redis.
- If not, Celery takes the task and processes it using usf1-mini.
- It finds similar documents with usf1-embed and ranks them with usf1-rerank.
- New data is saved to Qdrant, and a webhook is sent if you gave a URL.
- The system runs with 4 workers and can grow with more.
  
**Design Choices**
- One Endpoint: Uses /nlp/unified for all tasks to keep it simple. This makes it easy to use but less specific than separate endpoints.
- usf1-mini: Used for all tasks because it’s the only model available. It works well but might not be as accurate as special models.
- Qdrant: Stores data with embeddings for medical focus. Starts small but can grow with more data.
- Celery: Handles tasks in the background with a queue. Adds some complexity but manages heavy loads.
- Redis: Saves results for 1 hour. Fast but might miss new data after that time.
- Docker: Sets up Redis and Qdrant easily. Helps with scaling but needs setup.
  
**Extra Tools**
- Load Testing: Use locust -f locustfile.py to test how it handles many requests.
- Docker Setup: Check docker-compose.yml to run Redis and Qdrant.
