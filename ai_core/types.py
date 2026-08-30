"""시나리오 카드 / 세션 상태

JSON 도 Python 도 **snake_case** 로 통일한다. Django 모델과 팀원 작성 시나리오가
snake_case 라 로더가 변환할 이유가 없다. 프론트엔드에 camelCase 가 필요하면
serializer 경계에서만 변환한다.

필드명은 mirisalpim-web/backend/training/models.py 의 Django 모델과 대응한다
(Stage.id ↔ Stage.stage_key, TellPoint.id ↔ TellPoint.tp_key 등).

카드가 지켜야 하는 규칙은 ai_core/validate.py 한 곳에 있다 — 파일 로드 경로와
Django seed importer 가 같은 검증을 쓴다.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

Category = Literal["voice", "smishing", "phishing"]
#: 연령 트랙. 시나리오는 여러 트랙을 동시에 가질 수 있다 (Scenario.target_tracks)
TargetTrack = Literal["teen", "young", "middle_age", "senior"]
#: tell point 가 사기 신호인지 정상 신호인지
SignalType = Literal["risk", "legitimacy"]
Role = Literal["scammer", "user"]

#: 진행 난이도. scenario.md §4 확정 — 카테고리·소분류와 독립이며 Q4(대응 습관)로 정해진다.
#: 시나리오 콘텐츠를 난이도별로 따로 만들지 않고, 프롬프트 지시문으로만 강도를 조절한다.
Difficulty = Literal["easy", "normal", "hard"]

#: 시나리오 카드의 difficulty(1~3)는 그 시나리오의 기본 난이도다.
#: 세션 난이도는 Q4 로 결정되며, 문답을 건너뛴 경우 이 값을 기본값으로 쓴다.
DIFFICULTY_BY_LEVEL: dict[int, Difficulty] = {1: "easy", 2: "normal", 3: "hard"}

#: training.RiskyAction.ACTION_TYPE 과 동일한 5종 (Django 모델이 기준)
RiskyActionType = Literal[
    "personal_info", "link_click", "app_install", "transfer_consent", "isolation_accepted"
]


@dataclass
class Stage:
    id: str
    objective: str
    tactics: list[str]
    #: 이 턴 수를 채워야 다음 단계로 전환 후보가 된다. 최종 승인은 state.py + 판정기
    min_turns: int
    #: 판정기가 advance_stage 를 제안할 때 보는 기준. prompts.turn_state_block 이 쓴다
    advance_when: list[str] = field(default_factory=list)
    #: 시나리오 시작 단계에만 존재
    opening: str | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Stage:
        return cls(
            id=d["id"],
            objective=d["objective"],
            tactics=list(d.get("tactics", [])),
            min_turns=int(d["min_turns"]),
            advance_when=list(d.get("advance_when", [])),
            opening=d.get("opening"),
        )


@dataclass
class TellPoint:
    id: str
    stage: str
    trigger: str
    why: str
    #: 판별 결정력 1=약한 보조 신호 3=결정적 신호
    weight: int
    first_detectable_turn: int
    #: risk=사기 신호, legitimacy=정상 시나리오임을 보여주는 신호
    signal_type: SignalType = "risk"

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TellPoint:
        return cls(
            id=d["id"],
            stage=d["stage"],
            trigger=d["trigger"],
            why=d["why"],
            weight=int(d["weight"]),
            first_detectable_turn=int(d["first_detectable_turn"]),
            signal_type=d.get("signal_type", "risk"),
        )


@dataclass
class EndCondition:
    """종료 조건. 판정기가 충족을 제안하고 최종 승인은 코드가 한다 (단계 전환과 동일 원칙)."""

    id: str
    condition: str
    #: training_success | terminate | safety_stop
    result: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EndCondition:
        return cls(id=d["id"], condition=d["condition"], result=d["result"])


@dataclass
class Persona:
    display_name: str
    tone: str
    voice_preset: str
    #: 사칭할 기관. 자녀 사칭·신변 위협형은 기관이 없어 빈 문자열이다
    org: str = ""
    name: str = ""
    role: str = ""
    rules: list[str] = field(default_factory=list)
    resistance_strategy: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Persona:
        return cls(
            display_name=d["display_name"],
            tone=d["tone"],
            voice_preset=d["voice_preset"],
            org=d.get("org", ""),
            name=d.get("name", ""),
            role=d.get("role", ""),
            rules=list(d.get("rules", [])),
            resistance_strategy=list(d.get("resistance_strategy", [])),
        )

    @property
    def label(self) -> str:
        """프롬프트·화면에 쓰는 표기. org 가 없으면 이름만 쓴다."""
        who = self.name or self.display_name
        return f"{who} ({self.org})" if self.org else who


@dataclass
class Scenario:
    scenario_id: str
    category: Category
    #: scenario.md 의 분류 코드 (T01-5 등). 시나리오 추천이 이 값을 쓴다
    track: str
    #: 이 시나리오를 제공할 연령 트랙들
    target_tracks: list[str]
    title: str
    source: str
    #: False 면 정상(사기 아님) 시나리오
    is_scam: bool
    difficulty: int
    persona: Persona
    #: 상대 역할이 달성하려는 최종 목적. 평가 항목은 learning_objectives 에 둔다
    goal: str
    max_turns: int
    stages: list[Stage]
    tell_points: list[TellPoint]
    forbidden: list[str]
    learning_objectives: list[str] = field(default_factory=list)
    end_conditions: list[EndCondition] = field(default_factory=list)
    debrief_points: list[str] = field(default_factory=list)
    schema_version: int = 1

    @property
    def track_group(self) -> str:
        """추천 가중치가 집계되는 대분류 (T01-5 → T01)."""
        return self.track.split("-")[0]

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Scenario:
        return cls(
            scenario_id=d["scenario_id"],
            category=d["category"],
            track=d["track"],
            target_tracks=list(d["target_tracks"]),
            title=d["title"],
            source=d["source"],
            is_scam=bool(d["is_scam"]),
            difficulty=int(d["difficulty"]),
            persona=Persona.from_dict(d["persona"]),
            goal=d["goal"],
            max_turns=int(d["max_turns"]),
            stages=[Stage.from_dict(s) for s in d["stages"]],
            tell_points=[TellPoint.from_dict(t) for t in d["tell_points"]],
            forbidden=list(d.get("forbidden", [])),
            learning_objectives=list(d.get("learning_objectives", [])),
            end_conditions=[EndCondition.from_dict(c) for c in d.get("end_conditions", [])],
            debrief_points=list(d.get("debrief_points", [])),
            schema_version=int(d.get("schema_version", 1)),
        )


@dataclass
class Turn:
    role: Role
    text: str
    turn: int
    stage: str
    #: 응답 생성 소요(ms). 사기범 턴에만 존재
    latency_ms: int | None = None


@dataclass
class RiskyAction:
    turn: int
    #: training.RiskyAction.action_type 과 동일한 값만 허용 (RiskyActionType)
    type: str


@dataclass
class UserJudgment:
    turn: int
    is_scam_guess: bool


@dataclass
class SessionState:
    """코드가 소유하는 상태. LLM 은 이 값을 직접 바꾸지 못한다."""

    scenario_id: str
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    #: Q4(대응 습관)로 정해지는 진행 난이도. 사기꾼 프롬프트의 압박 강도만 바꾼다
    difficulty: Difficulty = "normal"
    turn: int = 0
    stage_index: int = 0
    turns_in_stage: int = 0
    risky_actions: list[RiskyAction] = field(default_factory=list)
    resistance_count: int = 0
    hit_tell_points: list[str] = field(default_factory=list)
    user_judgment: UserJudgment | None = None
    transcript: list[Turn] = field(default_factory=list)

    #: 훈련생이 화면에서 입력한 값. 사기꾼 프롬프트에만 쓴다 — 실제 보이스피싱은
    #: 이름을 알고 걸어오므로 이게 없으면 몰입이 크게 떨어진다.
    #: ⚠️ 저장하지 않는다. Django 쪽 engine_state.save_state() 가 이 세 필드를
    #:    DB 에 쓰지 않으며, 매 턴 요청 본문에서 다시 받는다 (기획서 10절의
    #:    "개인정보 수집·저장 없음"을 지키기 위한 구조다).
    trainee_name: str = ""
    trainee_age: str = ""
    trainee_region: str = ""
