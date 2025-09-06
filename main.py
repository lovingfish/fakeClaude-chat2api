import json
import os
import time
import uuid
from typing import (
    Any,
    Dict,
    List,
    Optional,
    AsyncGenerator,
    Union,
)  # <--- 1. 导入 Union

import httpx
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    # --- MODIFICATION START ---
    # 2. 允许 content 字段是字符串或一个包含字典的列表
    #    这是为了兼容新版客户端（如 Claude Code）发送的多部分内容格式
    content: Union[str, List[Dict[str, Any]]]
    # --- MODIFICATION END ---


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: bool = False
    temperature: Optional[float] = 0.7


# ... [ModelInfo, ModelList, ChatCompletionChoice, etc. a-z-Z] ...
# ... [这部分代码无需修改，保持原样] ...
class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "talkai"


class ModelList(BaseModel):
    object: str = "list"
    data: List[ModelInfo]


class ResponseMessage(BaseModel):
    role: str
    content: str


class ChatCompletionChoice(BaseModel):
    # 注意：这里的 ChatMessage 也要能处理非字符串的 content，但由于我们会在下游处理，所以这里可以暂时不动
    # 为了严谨，我们最好也在这里定义一个简单的输出用 Message 模型
    message: ResponseMessage
    index: int = 0
    finish_reason: str = "stop"


class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionChoice]
    usage: Dict[str, int] = Field(
        default_factory=lambda: {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
    )


class StreamChoice(BaseModel):
    delta: Dict[str, Any] = Field(default_factory=dict)
    index: int = 0
    finish_reason: Optional[str] = None


class StreamResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: str = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[StreamChoice]


# ... [以上部分代码无需修改，保持原样] ...


app = FastAPI(title="TalkAI OpenAI API Adapter")
security = HTTPBearer()
VALID_CLIENT_KEYS: set = set()


def load_client_api_keys():
    global VALID_CLIENT_KEYS
    keys_str = os.environ.get("CLIENT_API_KEYS")
    if keys_str:
        # If the environment variable is set, use it
        VALID_CLIENT_KEYS = set(key.strip() for key in keys_str.split(','))
        print(f"Loaded {len(VALID_CLIENT_KEYS)} API key(s) from environment variable.")
    else:
        # Otherwise, fall back to the JSON file for local development
        try:
            with open("client_api_keys.json", "r", encoding="utf-8") as f:
                keys = json.load(f)
                VALID_CLIENT_KEYS = set(keys) if isinstance(keys, list) else set()
                print(f"Loaded {len(VALID_CLIENT_KEYS)} API key(s) from client_api_keys.json.")
        except (FileNotFoundError, json.JSONDecodeError):
            VALID_CLIENT_KEYS = set()
            print("No API keys loaded. The application will be open to all requests.")


async def authenticate_client(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    if VALID_CLIENT_KEYS and (not auth or auth.credentials not in VALID_CLIENT_KEYS):
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.on_event("startup")
async def startup():
    load_client_api_keys()


def get_models_list() -> ModelList:
    try:
        with open("models.json", "r", encoding="utf-8") as f:
            models_dict = json.load(f)
        return ModelList(
            data=[ModelInfo(id=model_id) for model_id in models_dict.values()]
        )
    except:
        return ModelList(data=[])


@app.get("/v1/models", response_model=ModelList)
async def list_models(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(authenticate_client),
):
    return get_models_list()


async def stream_generator(
    response: httpx.Response, model: str
) -> AsyncGenerator[str, None]:
    stream_id = f"chatcmpl-{uuid.uuid4().hex}"
    created_time = int(time.time())

    yield f"data: {StreamResponse(id=stream_id, created=created_time, model=model, choices=[StreamChoice(delta={'role': 'assistant'})]).json()}\n\n"

    async for line in response.aiter_lines():
        if line.startswith("data:"):
            content = line[5:].strip()
            normalized_content = content.replace("\\n", "\n")
            if normalized_content and normalized_content != "-1":
                yield f"data: {StreamResponse(id=stream_id, created=created_time, model=model, choices=[StreamChoice(delta={'content': normalized_content})]).json()}\n\n"

    yield f"data: {StreamResponse(id=stream_id, created=created_time, model=model, choices=[StreamChoice(delta={}, finish_reason='stop')]).json()}\n\n"
    yield "data: [DONE]\n\n"


async def aggregate_stream(response: httpx.Response) -> str:
    content = []
    async for line in response.aiter_lines():
        if line.startswith("data:"):
            data = line[5:].strip()
            if data and data != "-1":
                content.append(data)
    return "".join(content).replace("\\n", "\n")


@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(authenticate_client),
):
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages required")

    messages_history = []
    system_prompt = ""

    for msg in request.messages:
        # --- MODIFICATION START ---
        # 3. 处理可能为列表的 content 字段
        current_content = ""
        if isinstance(msg.content, str):
            current_content = msg.content
        elif isinstance(msg.content, list):
            # 如果 content 是一个列表，遍历它并拼接所有 "text" 类型的内容
            for part in msg.content:
                if isinstance(part, dict) and part.get("type") == "text":
                    current_content += part.get("text", "")
        # --- MODIFICATION END ---

        if msg.role == "system":
            system_prompt = current_content
        elif msg.role in ["user", "assistant"]:
            messages_history.append(
                {
                    "id": str(uuid.uuid4()),
                    "from": "you" if msg.role == "user" else "assistant",
                    "content": current_content,  # 使用处理过后的 current_content
                }
            )

    if system_prompt and messages_history and messages_history[-1]["from"] == "you":
        messages_history[-1][
            "content"
        ] = f"{system_prompt}\n\n{messages_history[-1]['content']}"

    payload = {
        "type": "chat",
        "messagesHistory": messages_history,
        "settings": {"model": request.model, "temperature": request.temperature},
    }
    print(payload)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }

    try:
        client = httpx.AsyncClient(timeout=300)
        req = client.build_request(
            "POST",
            "https://claude.talkai.info/chat/send/",
            json=payload,
            headers=headers,
        )
        response = await client.send(req, stream=True)
        response.raise_for_status()

        if request.stream:
            return StreamingResponse(
                stream_generator(response, request.model),
                status_code=response.status_code,
            )
        else:
            content = await aggregate_stream(response)
            return ChatCompletionResponse(
                model=request.model,
                # 确保返回的 message 格式正确
                choices=[
                    ChatCompletionChoice(
                        message=ResponseMessage(role="assistant", content=content)
                    )
                ],
            )

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code, detail="TalkAI API error"
        )
    except (httpx.RequestError, Exception) as e:
        # Log the exception for debugging purposes
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal error")


if __name__ == "__main__":
    import uvicorn

    if not os.path.exists("client_api_keys.json"):
        with open("client_api_keys.json", "w", encoding="utf-8") as f:
            json.dump([f"sk-talkai-{uuid.uuid4().hex}"], f)

    # 注意：您的原始代码中端口是 8001，我保持一致
    uvicorn.run(app, host="0.0.0.0", port=8001)
