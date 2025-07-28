# RAG Implementation Guide

This guide explains how the Retrieval-Augmented Generation (RAG) system works in Ultrasafe Test A.

## RAG Implementation
- RAG helps NLP tasks by finding useful documents to make answers better.

## How It Works
- **Storage**: Uses Qdrant to keep text data with embeddings. [RAG Implementation - Vector Database]
- **Embeddings**: Creates numbers from text using `usf1-embed` for medical data, like diseases. [RAG Implementation - Domain-Specific Embeddings]
- **Finding Docs**: Gets up to 5 similar documents based on your text, using filters for classify tasks. [RAG Implementation - Retrieval System]
- **Ranking**: Uses `usf1-rerank` to sort documents by how well they match your task. [RAG Implementation - Reranking System]
- **Updating**: Adds new text and results to Qdrant to learn more.

## Workflow
1. When the system starts, it reads `data/filtered_diseases.csv` and sets up Qdrant collections for each task.
2. For a request, it makes an embedding of your text and searches Qdrant.
3. It finds similar documents and reranks them to match your task (e.g., filtering by category for classify).
4. After processing, it saves the new text and result to Qdrant.
5. If there’s an error, it retries up to 3 times and logs the problem.

## Good Points
- Makes classification smarter with medical context.
- Grows better as more data is added.
- Handles errors with retries and logging.