from locust import HttpUser, task, between

class NLPUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def test_classify(self):
        self.client.post("/nlp/unified", json={
            "text": "Patient has fever and cough",
            "task": "classify",
            "categories": ["infectious", "chronic"]
        })

    @task
    def test_extract_entities(self):
        self.client.post("/nlp/unified", json={
            "text": "Patient diagnosed with acute bronchitis and asthma",
            "task": "extract_entities"
        })

    @task
    def test_summarize(self):
        self.client.post("/nlp/unified", json={
            "text": "Cough is the most common illness-related reason for ambulatory care visits. Acute bronchitis is characterized by cough due to acute inflammation of the trachea and large airways.",
            "task": "summarize"
        })

    @task
    def test_sentiment(self):
        self.client.post("/nlp/unified", json={
            "text": "New treatment for chronic kidney disease shows promising results",
            "task": "sentiment"
        })

    @task
    def test_batch(self):
        self.client.post("/nlp/unified", json={
            "text": "",
            "task": "classify",
            "batch": ["Patient has fever and cough", "Chronic condition with high blood sugar"],
            "categories": ["infectious", "chronic"]
        })