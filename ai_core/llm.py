"""LLM 프로바이더 추상화.

설정은 전부 ai_core/config.py 에 있습니다. 이 파일은 실행만 합니다.

⚠️ 세 경로는 동등하지 않습니다.
  anthropic : 본 서비스 후보 경로. mid-conversation system role + 명시적 ephemeral 캐싱.
  gemini    : Google AI Studio. anthropic 처럼 mid-conversation system role이 없어
              ollama 와 같은 방식(turn_state 를 마지막 user 메시지에 접어 넣음)을 쓴다.
              캐싱은 명시적 태그가 필요 없는 암묵적 자동 캐싱 (고정 prefix ≥ 2048~4096
              토큰이면 자동 적용, google-genai SDK 2026-08 기준 확인).
  ollama    : 무료 반복용. ① mid-conversation system 메시지 없음(→ 마지막 user 에
              접어 넣음) ② 프롬프트 캐싱 없음.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

import httpx

from .config import AGENTS, OLLAMA_HOST, PROVIDER, model_for, validate_config
from .cost import Usage

# ── 임포트 시 1회 검증. 돈을 쓰기 전에 잘못된 조합을 잡는다 ──
_problems = validate_config()
for _p in _problems:
    _tag = "\x1b[31m[설정 오류]\x1b[0m" if _p.level == "error" else "\x1b[33m[설정 경고]\x1b[0m"
    print(f"{_tag} {_p.message}", file=sys.stderr)
if any(p.level == "error" for p in _problems):
    sys.exit(1)


#: Anthropic 전용 튜닝. 지연을 낮추면서 <thinking> 누출을 피한다
_ROLEPLAY_TUNING: dict[str, Any] = {
    "thinking": {"type": "adaptive"},
    "output_config": {"effort": "low"},
}

#: 하네스·판정용. Haiku 4.5 는 effort·adaptive thinking 을 지원하지 않는다
_SIMPLE_TUNING: dict[str, Any] = {"thinking": {"type": "disabled"}}


@dataclass
class ChatRequest:
    #: 항상 고정인 시스템 프롬프트
    system: str
    messages: list[dict[str, str]]
    #: 세션 내내 고정. Anthropic 에서는 여기에 cache_control 이 붙는다
    cached_system: str | None = None
    #: 턴마다 변하는 상태. Anthropic 은 messages 끝의 system 역할
    turn_state: str | None = None
    #: 판정기 등 구조화 출력이 필요할 때 JSON Schema(dict) 를 넘긴다.
    #: 지금은 gemini 경로만 지원(response_schema). anthropic 쪽 구조화 출력
    #: (output_config.format) 은 미구현 — 필요해지면 추가할 것.
    response_schema: Any | None = None


@dataclass
class ChatResult:
    text: str
    model: str
    latency_ms: int
    first_token_ms: int
    usage: Usage = field(default_factory=Usage)


_PROVIDER_FN: dict[str, Callable[..., ChatResult]] = {}


def chat(
    role: str,
    req: ChatRequest,
    on_delta: Callable[[str], None] | None = None,
) -> ChatResult:
    """역할만 넘기면 config.py 에서 모델·토큰·튜닝을 알아서 고른다"""
    cfg = AGENTS[role]
    model = model_for(role)
    fn = _PROVIDER_FN[PROVIDER]
    return fn(req, model, cfg.max_tokens, cfg.roleplay, on_delta)


# ─────────────────────── Anthropic (후보 경로) ───────────────────────

_client = None


def _anthropic_client():
    global _client
    if _client is None:
        import anthropic

        _client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "unused-in-ollama-mode")
        )
    return _client


def _chat_anthropic(
    req: ChatRequest,
    model: str,
    max_tokens: int,
    roleplay: bool,
    on_delta: Callable[[str], None] | None,
) -> ChatResult:
    if req.response_schema is not None:
        raise NotImplementedError(
            "anthropic 경로는 아직 구조화 출력(response_schema)을 지원하지 않습니다 "
            "(output_config.format 미구현). 판정기는 지금 gemini 전용입니다."
        )

    system: list[dict[str, Any]] = [{"type": "text", "text": req.system}]
    if req.cached_system:
        system.append(
            {
                "type": "text",
                "text": req.cached_system,
                "cache_control": {"type": "ephemeral"},
            }
        )

    messages: list[dict[str, Any]] = [dict(m) for m in req.messages]
    # 턴 상태는 messages 끝에 system 역할로. 캐시된 prefix 를 건드리지 않는다.
    if req.turn_state:
        messages.append({"role": "system", "content": req.turn_state})

    tuning = _ROLEPLAY_TUNING if roleplay else _SIMPLE_TUNING
    started = time.monotonic()
    first_token = -1.0
    chunks: list[str] = []

    with _anthropic_client().messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system,  # type: ignore[arg-type]
        messages=messages,  # type: ignore[arg-type]
        **tuning,
    ) as stream:
        for piece in stream.text_stream:
            if first_token < 0:
                first_token = time.monotonic() - started
            chunks.append(piece)
            if on_delta:
                on_delta(piece)
        final = stream.get_final_message()

    elapsed = time.monotonic() - started
    text = "".join(
        b.text for b in final.content if getattr(b, "type", None) == "text"
    ).strip()

    return ChatResult(
        text=text,
        model=model,
        latency_ms=int(elapsed * 1000),
        first_token_ms=int((first_token if first_token >= 0 else elapsed) * 1000),
        usage=Usage(
            input=final.usage.input_tokens,
            output=final.usage.output_tokens,
            cache_read=getattr(final.usage, "cache_read_input_tokens", 0) or 0,
            cache_write=getattr(final.usage, "cache_creation_input_tokens", 0) or 0,
        ),
    )


# ─────────────────────── Ollama (무과금 반복 경로) ───────────────────────


def _chat_ollama(
    req: ChatRequest,
    model: str,
    max_tokens: int,
    roleplay: bool,
    on_delta: Callable[[str], None] | None,
) -> ChatResult:
    if req.response_schema is not None:
        raise NotImplementedError(
            "ollama 경로는 구조화 출력(response_schema)을 지원하지 않습니다. "
            "판정기는 지금 gemini 전용입니다."
        )

    # Ollama 는 messages 끝의 system 역할을 지원하지 않는다.
    # 마지막 user 메시지에 상태 블록을 접어 넣는다. → 프롬프트 구조가 본 서비스와 달라진다.
    messages = [dict(m) for m in req.messages]
    if req.turn_state:
        if messages and messages[-1]["role"] == "user":
            messages[-1]["content"] = f"{messages[-1]['content']}\n\n{req.turn_state}"
        else:
            messages.append({"role": "user", "content": req.turn_state})

    system = f"{req.system}\n\n{req.cached_system}" if req.cached_system else req.system
    payload = {
        "model": model,
        "stream": True,
        "think": False,  # qwen3 등의 <think> 블록 억제
        "options": {"temperature": 0.8 if roleplay else 0.9, "num_predict": max_tokens},
        "messages": [{"role": "system", "content": system}, *messages],
    }

    started = time.monotonic()
    first_token = -1.0
    chunks: list[str] = []
    prompt_tokens = output_tokens = 0

    try:
        with httpx.stream(
            "POST", f"{OLLAMA_HOST}/api/chat", json=payload, timeout=600.0
        ) as res:
            if res.status_code != 200:
                res.read()
                raise RuntimeError(
                    f"Ollama 응답 오류 {res.status_code}: {res.text[:200]}\n"
                    f"  {OLLAMA_HOST} 가 떠 있는지, '{model}' 이 설치돼 있는지 확인하세요 (ollama list)"
                )
            for line in res.iter_lines():
                if not line.strip():
                    continue
                try:
                    j = json.loads(line)
                except json.JSONDecodeError:
                    continue
                piece = (j.get("message") or {}).get("content") or ""
                if piece:
                    if first_token < 0:
                        first_token = time.monotonic() - started
                    chunks.append(piece)
                    if on_delta:
                        on_delta(piece)
                if j.get("done"):
                    prompt_tokens = j.get("prompt_eval_count") or 0
                    output_tokens = j.get("eval_count") or 0
    except httpx.ConnectError as e:
        raise RuntimeError(
            f"Ollama 에 연결할 수 없습니다 ({OLLAMA_HOST}). `ollama serve` 가 떠 있는지 확인하세요."
        ) from e

    elapsed = time.monotonic() - started
    # 일부 모델이 <think> 를 흘리는 경우 방어
    import re

    text = re.sub(r"<think>.*?</think>", "", "".join(chunks), flags=re.S).strip()

    return ChatResult(
        text=text,
        model=model,
        latency_ms=int(elapsed * 1000),
        first_token_ms=int((first_token if first_token >= 0 else elapsed) * 1000),
        usage=Usage(input=prompt_tokens, output=output_tokens),
    )


# ─────────────────────── Gemini (Google AI Studio) ───────────────────────

_gemini_client = None


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        from google import genai

        _gemini_client = genai.Client(
            api_key=os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        )
    return _gemini_client


def _chat_gemini(
    req: ChatRequest,
    model: str,
    max_tokens: int,
    roleplay: bool,
    on_delta: Callable[[str], None] | None,
) -> ChatResult:
    from google.genai import types

    # Gemini 는 명시적 cache_control 태그가 없다 — 암묵적 prefix 캐싱이라
    # "고정 내용을 먼저" 두기만 하면 된다. cached_system 을 system_instruction에 이어붙인다.
    system_instruction = (
        f"{req.system}\n\n{req.cached_system}" if req.cached_system else req.system
    )

    # Anthropic 과 달리 mid-conversation system role 이 없다. Ollama 와 동일하게
    # turn_state 를 마지막 user 메시지에 접어 넣는다.
    messages = [dict(m) for m in req.messages]
    if req.turn_state:
        if messages and messages[-1]["role"] == "user":
            messages[-1] = {
                "role": "user",
                "content": f"{messages[-1]['content']}\n\n{req.turn_state}",
            }
        else:
            messages.append({"role": "user", "content": req.turn_state})

    # Gemini 의 역할명은 "model" (Anthropic/OpenAI 관례의 "assistant" 가 아니다)
    contents = [
        types.Content(
            role="model" if m["role"] == "assistant" else "user",
            parts=[types.Part(text=m["content"])],
        )
        for m in messages
    ]

    config_kwargs: dict[str, Any] = {
        "system_instruction": system_instruction,
        "max_output_tokens": max_tokens,
        "temperature": 0.8 if roleplay else 0.9,
    }
    # 구조화 출력(판정기 등). anthropic 경로엔 아직 대응 기능이 없다.
    if req.response_schema is not None:
        config_kwargs["response_mime_type"] = "application/json"
        config_kwargs["response_schema"] = req.response_schema
        # 판정은 창작이 아니라 분석 — roleplay 기준 온도(0.8/0.9)보다 낮춰 일관성을 높인다
        config_kwargs["temperature"] = 0.2

    started = time.monotonic()
    first_token = -1.0
    chunks: list[str] = []
    usage_meta = None

    stream = _get_gemini_client().models.generate_content_stream(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(**config_kwargs),
    )
    for chunk in stream:
        piece = chunk.text or ""
        if piece:
            if first_token < 0:
                first_token = time.monotonic() - started
            chunks.append(piece)
            if on_delta:
                on_delta(piece)
        if getattr(chunk, "usage_metadata", None):
            usage_meta = chunk.usage_metadata

    elapsed = time.monotonic() - started
    text = "".join(chunks).strip()

    prompt_tokens = getattr(usage_meta, "prompt_token_count", 0) or 0
    cached_tokens = getattr(usage_meta, "cached_content_token_count", 0) or 0
    output_tokens = getattr(usage_meta, "candidates_token_count", 0) or 0

    return ChatResult(
        text=text,
        model=model,
        latency_ms=int(elapsed * 1000),
        first_token_ms=int((first_token if first_token >= 0 else elapsed) * 1000),
        usage=Usage(
            # prompt_token_count 는 캐시 히트분을 포함한 전체 입력 토큰수.
            # 신규(비캐시) 입력만 input 에 남기고 캐시 히트는 cache_read 로 뺀다.
            input=max(prompt_tokens - cached_tokens, 0),
            output=output_tokens,
            cache_read=cached_tokens,
            # 암묵적 캐싱은 "쓰기"에 별도 요금이 없다 (명시적 caches.create 와 다름).
            cache_write=0,
        ),
    )


# ─────────────────────── 프로바이더 등록 ───────────────────────
# chat() 의 조회 테이블. 함수 정의가 끝난 뒤 한 번만 채운다.
_PROVIDER_FN.update(
    {
        "anthropic": _chat_anthropic,
        "ollama": _chat_ollama,
        "gemini": _chat_gemini,
    }
)
