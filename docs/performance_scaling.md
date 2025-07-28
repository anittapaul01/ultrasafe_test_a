
# Performance and Scaling Guide

This guide shows how the Ultrasafe Test A NLP system performs and can grow.

## Performance Features
- **Fast Work**: Uses `asyncio` to handle requests quickly, even with many users. [Performance and Scaling]
- **Saving Results**: Uses Redis to store results for 1 hour, so it doesn’t redo work. [Performance and Scaling - Caching]
- **Batch Processing**: Can handle multiple texts in one request to save time. [Performance and Scaling]

## Scaling Features
- **Workers**: Runs with `uvicorn` and 4 workers by default (can change with `--workers`). [Performance and Scaling - Horizontal Scaling]
- **Task Queue**: Uses Celery to manage tasks in the background, so it can handle many requests at once. [Performance and Scaling - Efficient Task Queuing]
- **Docker Setup**: Includes Redis and Qdrant with `docker-compose.yml` for easy scaling across servers.

## How It Works
- When a request comes, it checks Redis first. If the result is there, it returns it fast.
- If not, Celery takes the task and processes it separately, freeing up the main system.
- The 4 workers share the work, and more can be added. Docker lets you run multiple copies of Redis and Qdrant.
- For heavy use, add more workers or servers with a load balancer (like Nginx).

## Things to Know
- Good for medium traffic with 4 workers. For very high traffic, add more servers.
- Redis caching speeds things up but might miss new data after 1 hour.
- Celery and Docker make it ready to grow as needed.