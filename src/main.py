
from models import ChatRequest
from openai_client import chat
from fastapi import FastAPI
import logging, json, time, uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(title="AKS AI Observability")

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/chat", response_model=dict)
def chat_endpoint(request: ChatRequest):
    request_id = str(uuid.uuid4())
    initial_timestamp = time.time()
    
    logger.info(f"Received request: {request_id} at {initial_timestamp}")
    latency_ms = int((time.time() - initial_timestamp) * 1000)
    result = chat(request)
    logger.info(f"Request {request_id} processed in {latency_ms}ms")


    logger.info(json.dumps({
        "event": "chat",
        "request_id": request_id,
        "latency_ms": latency_ms,
        "tokens": result["completion"]["total_tokens"],
        "status": "ok",
    }))

    return result