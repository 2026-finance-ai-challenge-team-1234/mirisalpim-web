"""시나리오 카드 검증기.

Django 의존이 없다 — AI 코어 로더와 Django seed importer 가 **같은 규칙**을 쓰도록
검증 로직을 여기 한 곳에만 둔다. 카드를 DB 에 넣기 전에도, 파일에서 바로 로드할 때도
이 함수를 통과해야 한다.

사용법:
    python -m ai_core.validate                     # ai_core/data/scenarios/ 전체
    python -m ai_core.validate ../scenario/json_data
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

CATEGORIES = {"voice", "smishing", "phishing"}
TARGET_TRACKS = {"teen", "young", "middle_age", "senior"}
SIGNAL_TYPES = {"risk", "legitimacy"}
END_RESULTS = {"training_success", "terminate", "safety_stop"}

#: scenario.md 의 분류 코드. T=보이스피싱, S=스미싱, 뒤에 대분류 2자리 + 세부번호
TRACK_PATTERN = r"^[TS]\d{2}-\d{1,2}$"

REQUIRED = [
    "schema_version",
    "scenario_id",
    "category",
    "track",
    "target_tracks",
    "title",
    "source",
    "is_scam",
    "difficulty",
    "goal",
    "max_turns",
    "persona",
    "stages",
    "tell_points",
    "forbidden",
]


def earliest_turn(min_turns: list[int], stage_index: int) -> int:
    """engine 기준 해당 stage 에서 사기꾼이 처음 말하는 턴.

    turn 은 발화마다 1 증가하고 사기꾼은 홀수 턴에 말한다 (1턴 = opening).
    stage i 는 앞 단계들의 min_turns 를 모두 채운 뒤 시작하므로
    1 + 2*sum(앞 min_turns) 가 그 단계의 최초 발화 턴이다.
    """
    return 1 + 2 * sum(min_turns[:stage_index])


def required_turns(min_turns: list[int]) -> int:
    """모든 단계가 min_turns 를 채우는 데 필요한 전체 턴 수."""
    return 2 * sum(min_turns) - 1


def validate(card: dict[str, Any]) -> list[str]:
    """위반 목록을 돌려준다. 빈 리스트면 통과."""
    import re

    e: list[str] = []

    for k in REQUIRED:
        if k not in card:
            e.append(f"필수 필드 누락: {k}")
    if e:
        return e

    if card["category"] not in CATEGORIES:
        e.append(f"category 허용값 아님: {card['category']}")
    if not re.match(TRACK_PATTERN, str(card["track"])):
        e.append(f"track 형식 오류(예: T01-5): {card['track']}")

    tracks = card["target_tracks"]
    if not isinstance(tracks, list) or not tracks:
        e.append("target_tracks 는 비어 있지 않은 배열이어야 함")
    else:
        bad = [t for t in tracks if t not in TARGET_TRACKS]
        if bad:
            e.append(f"target_tracks 허용값 아님: {bad}")

    if not isinstance(card["goal"], str) or not card["goal"].strip():
        e.append("goal 은 비어 있지 않은 문자열이어야 함 (평가 항목 목록은 learning_objectives)")
    if not 1 <= int(card["difficulty"]) <= 3:
        e.append(f"difficulty 는 1~3: {card['difficulty']}")
    if not card["forbidden"]:
        e.append("forbidden 이 비어 있음 — 안전 제약은 시나리오마다 명시해야 함")

    persona = card["persona"]
    # org 는 선택 — 자녀 사칭·신변 위협형은 사칭할 기관이 없다 (display_name 만 있다)
    for k in ("display_name", "tone", "voice_preset"):
        if not persona.get(k):
            e.append(f"persona.{k} 누락")

    stages = card["stages"]
    if not stages:
        e.append("stages 가 비어 있음")
        return e

    ids = [s["id"] for s in stages]
    if len(ids) != len(set(ids)):
        e.append(f"stage id 중복: {ids}")
    if not stages[0].get("opening"):
        e.append("첫 stage 에 opening 이 없음 — 엔진은 1턴을 opening 으로 시작한다")
    for s in stages[1:]:
        if s.get("opening"):
            e.append(f"stage '{s['id']}': opening 은 첫 stage 에만 둔다")

    min_turns = []
    for s in stages:
        mt = int(s.get("min_turns", 0))
        if mt < 1:
            e.append(f"stage '{s['id']}': min_turns 는 1 이상이어야 함")
        if not s.get("advance_when"):
            e.append(f"stage '{s['id']}': advance_when 이 비어 있음 (판정기 프롬프트가 이 값을 쓴다)")
        if not s.get("tactics"):
            e.append(f"stage '{s['id']}': tactics 가 비어 있음")
        min_turns.append(max(mt, 1))

    need = required_turns(min_turns)
    if need > int(card["max_turns"]):
        e.append(
            f"min_turns 합({sum(min_turns)})을 채우려면 {need}턴이 필요한데 "
            f"max_turns 는 {card['max_turns']} — 마지막 단계에 도달하지 못한다"
        )

    seen_tp = set()
    for tp in card["tell_points"]:
        if tp["id"] in seen_tp:
            e.append(f"tell_point id 중복: {tp['id']}")
        seen_tp.add(tp["id"])
        if tp["stage"] not in ids:
            e.append(f"tell_point '{tp['id']}': 존재하지 않는 stage '{tp['stage']}' 참조")
            continue
        if tp.get("signal_type") not in SIGNAL_TYPES:
            e.append(f"tell_point '{tp['id']}': signal_type 은 risk|legitimacy")
        if not 1 <= int(tp["weight"]) <= 3:
            e.append(f"tell_point '{tp['id']}': weight 는 1~3")
        idx = ids.index(tp["stage"])
        lo = earliest_turn(min_turns, idx)
        if int(tp["first_detectable_turn"]) < lo:
            e.append(
                f"tell_point '{tp['id']}': first_detectable_turn "
                f"{tp['first_detectable_turn']} < 해당 stage 도달 최초 턴 {lo} "
                "— 노출되기 전에 탐지된 것으로 집계된다"
            )
        if int(tp["first_detectable_turn"]) > int(card["max_turns"]):
            e.append(f"tell_point '{tp['id']}': first_detectable_turn 이 max_turns 를 넘음")

    kinds = {tp.get("signal_type") for tp in card["tell_points"]}
    if card["is_scam"] and "risk" not in kinds:
        e.append("사기 시나리오인데 signal_type=risk 인 tell_point 가 없음")
    if not card["is_scam"] and "risk" in kinds:
        e.append("정상 시나리오에 signal_type=risk 인 tell_point 가 있음")

    for c in card.get("end_conditions", []):
        if c["result"] not in END_RESULTS:
            e.append(f"end_condition '{c['id']}': result 허용값 아님 ({c['result']})")

    return e


def main() -> int:
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, OSError):
            pass

    target = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path(__file__).resolve().parent / "data" / "scenarios"
    )
    files = sorted(target.glob("*.json"))
    if not files:
        print(f"검증할 JSON 이 없습니다: {target}")
        return 1

    bad = 0
    for f in files:
        errors = validate(json.loads(f.read_text(encoding="utf-8")))
        if errors:
            bad += 1
            print(f"✗ {f.name}")
            for msg in errors:
                print(f"    - {msg}")
        else:
            print(f"✓ {f.name}")

    print(f"\n{len(files) - bad}/{len(files)} 통과")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
