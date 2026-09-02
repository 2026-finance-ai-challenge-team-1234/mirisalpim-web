"""
══════════════════════════════════════════════════════════════════════════

  ⚙️  설정 — 여기만 고치면 됩니다

  프로바이더와 기능별 모델을 이 파일 하나에서 결정합니다.
  환경변수로 덮어쓸 수 있습니다 (일회성 실행용):
     LLM_PROVIDER=ollama python -m ai_core.smoke

══════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# .env 로딩 — mirisalpim-web/ 루트의 .env 를 읽는다 (.env.example 과 같은 위치).
# ai_core 는 Django 를 import 하지 않지만, 실제로는 Django 프로세스 안에서
# 호출되므로 환경변수를 두 곳에서 따로 관리하지 않기 위한 실용적 선택이다.
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
if _ENV_PATH.exists():
    for _line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _, _v = _line.partition("=")
        os.environ.setdefault(_k.strip(), _v.strip().strip("\"'"))

Provider = Literal["anthropic", "ollama", "gemini"]
AgentRole = Literal["scammer", "judge", "safety"]

# ─────────────────────────────────────────────────────────────────────────
#  1. 프로바이더 — 이 한 줄
# ─────────────────────────────────────────────────────────────────────────

#: "ollama"    무과금 로컬. 프롬프트 다듬기·코드 디버깅용.
#:             ⚠️ 합격/불합격 판정 근거로는 쓸 수 없습니다 (구조가 다름)
#: "anthropic" 후보 경로. mid-conversation system role + 명시적 ephemeral 캐싱.
#: "gemini"    Google AI Studio. mid-conversation system role이 없어 ollama와
#:             같은 방식(turn_state를 마지막 user 메시지에 접어 넣음)을 쓴다.
#:             캐싱은 암묵적 자동 캐싱(2.5+/3.x, 최소 2048~4096토큰 고정 prefix 필요).
#:             최종 프로바이더는 아직 미확정 — 2026-08-19 기준.
PROVIDER: Provider = os.environ.get("LLM_PROVIDER", "ollama")  # type: ignore[assignment]


# ─────────────────────────────────────────────────────────────────────────
#  2. 기능별 모델
# ─────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class AgentConfig:
    label: str
    #: Anthropic 프로바이더일 때 쓸 모델
    anthropic: str
    #: Ollama 프로바이더일 때 쓸 모델
    ollama: str
    #: Gemini(Google AI Studio) 프로바이더일 때 쓸 모델
    gemini: str
    max_tokens: int
    #: True = 역할극(사고 최소 튜닝), False = 하네스/판정(사고 불필요)
    roleplay: bool
    #: Anthropic 전용 기능을 쓰는가 (모델 제약 검사용). gemini/ollama 는 해당 없음
    needs_opus_features: bool
    note: str = ""


AGENTS: dict[str, AgentConfig] = {
    # 사기범 역할극. 유일하게 훈련생과 직접 대화하는 역할
    "scammer": AgentConfig(
        label="사기꾼",
        anthropic="claude-opus-5",
        ollama="qwen3:14b",
        gemini="gemini-3.7-flash",
        max_tokens=1000,
        roleplay=True,
        needs_opus_features=True,
        note=(
            "mid-conversation system 메시지 + effort + adaptive thinking 사용 (anthropic). "
            "gemini-3.7-flash 는 정식 출시·저렴 (3.1-pro는 preview라 미채택). "
            "⚠️ 2026-08-17 실측: 이 계정은 2.5 시리즈(pro/flash/flash-lite) 전부 "
            "'신규 사용자에게 더 이상 제공 안 됨' 404 — 대안은 3.1-pro-preview(다만 preview)뿐. "
            "⚠️ gemini-3.7-flash 는 thinking_budget=0 으로도 사고를 못 끈다(항상 "
            "~380~550 토큰 소모, anthropic Opus 5 와 같은 종류의 함정). max_tokens 를 "
            "400 으로 두면 대사가 문장 중간에 잘린다 — 1000 으로 여유를 둔 이유"
        ),
    ),
    # 판정기 — 훈련생 발화 분석 (structured outputs). engine.step() 에 연결됨
    "judge": AgentConfig(
        label="판정기",
        anthropic="claude-opus-5",
        ollama="qwen3:14b",
        gemini="gemini-3.5-flash-lite",
        max_tokens=1000,
        roleplay=False,
        needs_opus_features=False,
        note=(
            "structured outputs 로 단계전환·위험행동·저항 판정. "
            "gemini 경로는 response_schema 로 llm.py 에서 지원 — "
            "gemini-2.5-flash 는 이 계정에서 404라 3.x 계열을 쓴다. "
            "정확도 검증: 3.7-flash 20/20(100%, 2026-08-19). "
            "2026-09-01 3.5-flash-lite 로 교체 — 같은 4페르소나 라운드로빈 20턴에서 "
            "19/20(95%), 기준 80%+ 통과. 판정 지연이 p50 6048ms→908ms, "
            "p95 13461ms→1040ms 로 줄고 변동폭이 사라진다(음성 한 턴의 최대 구간이었다). "
            "⚠️ 유일한 오답 유형: 이전 턴에서 이미 한 위험행동을 이번 턴에 다시 보고한다"
            "(실측 sc-02 turn 11 의 isolation_accepted 중복). 채점 등급에는 영향이 없고"
            "(grading 은 멤버십 검사만 한다) 개입 경고가 한 번 더 뜨는 것이 유일한 증상이다. "
            "prompts.JUDGE_CORE 의 '이번 발화에서 새로 일어난 것만' 문장으로도 막히지 않았다"
        ),
    ),
    # 안전 필터 예정 — 사기꾼 출력이 안전 제약을 지키는지 검증 (미구현)
    "safety": AgentConfig(
        label="안전 필터",
        anthropic="claude-haiku-4-5",
        ollama="qwen3:14b",
        gemini="gemini-3.5-flash-lite",
        max_tokens=300,
        roleplay=False,
        needs_opus_features=False,
        note="미구현. 통과/차단 판정만 하므로 가벼운 모델로 충분",
    ),
}

# ─────────────────────────────────────────────────────────────────────────
#  3. Ollama 접속
# ─────────────────────────────────────────────────────────────────────────

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# ─────────────────────────────────────────────────────────────────────────
#  3-1. 사기범 일시 장애 폴백
# ─────────────────────────────────────────────────────────────────────────

#: 사기범 모델이 503/429 로 죽었을 때 한 번만 대신 쓸 모델. 빈 값이면 폴백하지 않는다.
#:
#: 2026-09-01 실측: gemini-3.7-flash 가 "This model is currently experiencing high
#: demand" 로 503 을 냈고, 그동안 3.5-flash-lite 를 쓰는 판정기·안전 필터는 1초 내외로
#: 멀쩡했다. 사기범은 훈련생과 직접 대화하는 유일한 역할이라 이게 죽으면 판정기가
#: 살아 있어도 훈련이 진행되지 않는다 - 심사 중에 겪으면 서비스가 멈춘 것으로 보인다.
#:
#: ⚠️ 폴백 모델은 역할극 품질이 검증되지 않았다. "품질이 조금 떨어진 훈련" 이
#: "멈춘 서비스" 보다 낫다는 판단이며, 안전 필터는 모델과 무관하게 그대로 적용된다.
#: 폴백이 쓰이면 경고 로그가 남으므로 배포 로그에서 빈도를 확인할 수 있다.
SCAMMER_FALLBACK_MODEL: dict[str, str] = {
    "gemini": os.environ.get("GEMINI_SCAMMER_FALLBACK", "gemini-3.5-flash-lite"),
    "anthropic": os.environ.get("ANTHROPIC_SCAMMER_FALLBACK", ""),
    "ollama": os.environ.get("OLLAMA_SCAMMER_FALLBACK", ""),
}


def scammer_fallback_for(provider: str | None = None) -> str | None:
    """폴백 모델 이름. 설정이 없거나 기본 모델과 같으면 None."""
    p = provider or PROVIDER
    fallback = (SCAMMER_FALLBACK_MODEL.get(p) or "").strip()
    if not fallback or fallback == model_for("scammer", p):
        return None
    return fallback

# ─────────────────────────────────────────────────────────────────────────
#  4. 단가 (표시용) — $/MTok
# ─────────────────────────────────────────────────────────────────────────

MODEL_PRICE: dict[str, dict[str, float]] = {
    "claude-opus-5": {"input": 5.0, "output": 25.0},
    "claude-opus-4-8": {"input": 5.0, "output": 25.0},
    "claude-sonnet-5": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 1.0, "output": 5.0},
    # 2026-08 Google AI Studio 공식 단가 (≤200k 프롬프트 기준. 그 이상은 티어가 오름)
    # ⚠️ startswith 로 매칭하므로(_price_for, config.py) "-lite" 처럼 더 긴/구체적인
    # 이름을 접두사가 겹치는 짧은 이름보다 반드시 먼저 둘 것.
    # ⚠️ 2026-08-17 이 프로젝트 계정으로 실측: gemini-2.5-* (pro/flash/flash-lite) 전부
    # "신규 사용자에게 더 이상 제공 안 됨" 404. AGENTS 는 전부 3.x 로 맞춰뒀다.
    # 다른 계정/키로 바뀌면 다시 될 수 있어 가격 정보는 지우지 않고 남겨둔다.
    "gemini-3.7-flash": {"input": 0.75, "output": 3.75},
    "gemini-3.5-flash-lite": {"input": 0.30, "output": 2.50},
    "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.0},
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
}

#: 캐시 쓰기는 입력의 1.25배, 캐시 읽기는 0.1배 (anthropic 명시적 ephemeral 캐시 기준)
CACHE_WRITE_MULTIPLIER = 1.25
CACHE_READ_MULTIPLIER = 0.1
#: gemini 는 암묵적 캐싱이라 "쓰기"에 별도 요금이 없다 (llm.py 가 cache_write=0 으로 보고).
#: 확인된 캐시 읽기 할인율은 gemini 도 입력가의 0.1배로 anthropic과 동일 (2.5/3.7 flash, 2.5 pro 전부 확인).

#: 표시용 환율. 정확한 청구액이 아니라 감을 잡기 위한 값
USD_TO_KRW = 1400


# ─────────────────────────────────────────────────────────────────────────
#  헬퍼 — 아래는 고칠 일이 없습니다
# ─────────────────────────────────────────────────────────────────────────


def _env_override(role: str, provider: str) -> str | None:
    """환경변수 오버라이드: SCAMMER_MODEL / OLLAMA_SCAMMER_MODEL / GEMINI_SCAMMER_MODEL 등"""
    upper = role.upper()
    if provider == "ollama":
        key = f"OLLAMA_{upper}_MODEL"
    elif provider == "gemini":
        key = f"GEMINI_{upper}_MODEL"
    else:
        key = f"{upper}_MODEL"
    return os.environ.get(key)


def model_for(role: str, provider: str | None = None) -> str:
    p = provider or PROVIDER
    cfg = AGENTS[role]
    if p == "ollama":
        default = cfg.ollama
    elif p == "gemini":
        default = cfg.gemini
    else:
        default = cfg.anthropic
    return _env_override(role, p) or default


def supports_opus_features(model: str) -> bool:
    """Anthropic 전용 기능(mid-conversation system, effort, adaptive)을 지원하는가"""
    return model.startswith(
        ("claude-opus-5", "claude-opus-4-8", "claude-fable", "claude-mythos")
    )


@dataclass
class ConfigProblem:
    level: Literal["error", "warn"]
    message: str


def validate_config(provider: str | None = None) -> list[ConfigProblem]:
    """설정 검증. 돈을 쓰기 전에 잘못된 조합을 잡는다."""
    p = provider or PROVIDER
    problems: list[ConfigProblem] = []

    if p == "anthropic":
        for role, cfg in AGENTS.items():
            model = model_for(role, "anthropic")
            if cfg.needs_opus_features and not supports_opus_features(model):
                problems.append(
                    ConfigProblem(
                        "error",
                        f"[{cfg.label}] {model} 은 필요한 기능을 지원하지 않습니다.\n"
                        f"    · output_config.effort          → 에러\n"
                        f'    · thinking: {{"type":"adaptive"}}   → 미지원\n'
                        f'    · messages 안의 role:"system"   → 400 (캐싱 설계의 핵심)\n'
                        f"    config.py 의 AGENTS['{role}'].anthropic 을 claude-opus-5 로 되돌리세요.",
                    )
                )
            if not any(model.startswith(k) for k in MODEL_PRICE):
                problems.append(
                    ConfigProblem(
                        "warn",
                        f"[{cfg.label}] {model} 의 단가를 모릅니다. 비용이 Opus 기준으로 과대 추정됩니다.",
                    )
                )
        if not os.environ.get("ANTHROPIC_API_KEY"):
            problems.append(
                ConfigProblem(
                    "error",
                    "ANTHROPIC_API_KEY 가 없습니다.\n"
                    "    backend/.env 에 키를 넣으세요.\n"
                    '    또는 무과금: config.py 의 PROVIDER 를 "ollama" 로.',
                )
            )

    if p == "gemini":
        for role, cfg in AGENTS.items():
            model = model_for(role, "gemini")
            if not any(model.startswith(k) for k in MODEL_PRICE):
                problems.append(
                    ConfigProblem(
                        "warn",
                        f"[{cfg.label}] {model} 의 단가를 모릅니다. "
                        "비용 표시가 부정확할 수 있습니다 (실제 청구엔 영향 없음).",
                    )
                )
        if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
            problems.append(
                ConfigProblem(
                    "error",
                    "GEMINI_API_KEY 가 없습니다.\n"
                    "    backend/.env 에 GEMINI_API_KEY=... 를 넣으세요 (GOOGLE_API_KEY 도 인식됩니다).\n"
                    '    또는 무과금: config.py 의 PROVIDER 를 "ollama" 로.',
                )
            )

    if p == "ollama":
        used = {model_for(r, "ollama") for r in AGENTS}
        if len(used) > 1:
            problems.append(
                ConfigProblem(
                    "warn",
                    f"Ollama 모델이 {len(used)}종입니다 ({', '.join(sorted(used))}).\n"
                    f"    매 턴 모델 스와핑이 일어나 프롬프트를 재처리합니다. 실측 42초/턴 → 7초/턴.\n"
                    f"    config.py 에서 모든 역할의 ollama 값을 같은 모델로 맞추세요.",
                )
            )

    return problems
