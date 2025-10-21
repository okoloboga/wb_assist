import os
from typing import Any, Dict, List, Optional
from fastapi import FastAPI
from pydantic import BaseModel

from gpt_integration.gpt_client import GPTClient
from gpt_integration.pipeline import run_analysis

app = FastAPI(title="GPT Integration Service", version="1.0.0")


class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    system_prompt: Optional[str] = None


class ChatResponse(BaseModel):
    text: str


class AnalysisRequest(BaseModel):
    data: Dict[str, Any]
    template_path: Optional[str] = None
    validate_output: bool = False


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    # Instantiate client on each request to pick up latest envs
    client = GPTClient.from_env()
    if req.system_prompt:
        client.system_prompt = req.system_prompt
    text = client.complete_messages(req.messages)
    return ChatResponse(text=text)


@app.post("/v1/analysis")
def analysis(req: AnalysisRequest) -> Dict[str, Any]:
    client = GPTClient.from_env()
    result = run_analysis(client, data=req.data, template_path=req.template_path, validate=req.validate_output)
    return result


if __name__ == "__main__":
    port_str = os.getenv("GPT_PORT") or "9000"
    port = int(port_str)
    import uvicorn
    uvicorn.run("gpt_integration.service:app", host="0.0.0.0", port=port)