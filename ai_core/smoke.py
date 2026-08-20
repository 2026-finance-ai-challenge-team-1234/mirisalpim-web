"""API 키 없이 돌아가는 스모크 테스트.

시나리오 스키마와 상태머신의 전환 승인 로직만 검증한다 (판정기 LLM 호출 없음).
"전환 조건 회귀 테스트" — 판정기를 engine.step() 에 연결하면서 try_advance_stage() 의
게이트 로직이 바뀌었으므로(관련 커밋: proposed 기본값 True→AND-게이트), 그 경계 조건을
전부 이 파일에서 결정론적으로 검증한다.

사용법: python -m ai_core.smoke   (mirisalpim-web/ 에서 실행)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ⚠️ Windows 콘솔 기본 인코딩(cp949)에서 한글/기호 출력이 UnicodeEncodeError 로 죽는다.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except (AttributeError, OSError):
        pass

from ai_core.state import create_session, current_stage, try_advance_stage  # noqa: E402
from ai_core.streaming import split_sentences  # noqa: E402
from ai_core.types import Scenario  # noqa: E402

failed = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global failed
    mark = "✓" if cond else "✗"
    tail = f" {detail}" if detail else ""
    print(f"  {mark} {label}{tail}")
    if not cond:
        failed += 1


path = Path(__file__).resolve().parent.parent / "data" / "scenarios" / "sc-02.json"
scenario = Scenario.from_dict(json.loads(path.read_text(encoding="utf-8")))

print("\n시나리오 스키마")
check("로드 성공", bool(scenario.scenario_id), scenario.scenario_id)
check("단계 4개", len(scenario.stages) == 4, f"{len(scenario.stages)}개")
check("첫 단계에 opening 존재", bool(scenario.stages[0].opening))
check("tellPoint 3개 이상", len(scenario.tell_points) >= 3, f"{len(scenario.tell_points)}개")
stage_ids = {s.id for s in scenario.stages}
check(
    "tellPoint 의 stage 가 모두 실재",
    all(t.stage in stage_ids for t in scenario.tell_points),
)
check("모든 tellPoint 에 why 존재", all(len(t.why) > 10 for t in scenario.tell_points))
check("forbidden 정의됨", len(scenario.forbidden) > 0, f"{len(scenario.forbidden)}개")

print("\n상태머신 — 전환은 코드가 승인한다 (판정기 미연결 기본 동작)")
state = create_session(scenario)
check("초기 단계", current_stage(scenario, state).id == "trust_building")

early = try_advance_stage(scenario, state)
check("최소 턴 미달 시 전환 거부 (판정기 기본값)", not early.advanced, early.reason)

proposed_early = try_advance_stage(scenario, state, proposed=True)
check("판정기가 제안해도 조건 미달이면 거부", not proposed_early.advanced, proposed_early.reason)

state.turns_in_stage = scenario.stages[0].min_turns
ok = try_advance_stage(scenario, state)
check("조건 충족 + 판정기 미연결(기본 True) 시 전환", ok.advanced, ok.reason)
check("전환 후 단계 카운터 초기화", state.turns_in_stage == 0)

print("\n판정기 연결 시 AND-게이트 (신규)")
state2 = create_session(scenario)
state2.turns_in_stage = scenario.stages[0].min_turns
rejected_by_judge = try_advance_stage(scenario, state2, proposed=False)
check(
    "최소 턴 충족해도 판정기가 반대(False)하면 전환 안 함",
    not rejected_by_judge.advanced,
    rejected_by_judge.reason,
)
check("전환 안 됐으니 단계는 그대로", current_stage(scenario, state2).id == "trust_building")

approved_by_judge = try_advance_stage(scenario, state2, proposed=True)
check("같은 상태에서 판정기가 찬성(True)하면 전환됨", approved_by_judge.advanced, approved_by_judge.reason)

# 마지막 단계까지 밀어서 경계 확인
state3 = create_session(scenario)
while state3.stage_index < len(scenario.stages) - 1:
    state3.turns_in_stage = scenario.stages[state3.stage_index].min_turns
    try_advance_stage(scenario, state3)
state3.turns_in_stage = 99
last = try_advance_stage(scenario, state3, proposed=True)
check("마지막 단계에서는 판정기가 찬성해도 전환 안 함", not last.advanced, last.reason)

print("\n문장 분리 — split_sentences() (스트리밍 x 안전 필터)")

sentences, rest = split_sentences("괜찮으세요? 확인이 필요합니다.")
check("일반 문장 2개로 분리", sentences == ["괜찮으세요?", "확인이 필요합니다."], str(sentences))
check("잔여 버퍼 없음", rest == "", repr(rest))

sentences, rest = split_sentences("hanbit-secure.example 로 접속하세요.")
check(
    "더미 도메인 마침표는 경계로 안 잡힘",
    sentences == ["hanbit-secure.example 로 접속하세요."],
    str(sentences),
)

sentences, rest = split_sentences("본인 확인이 필요합니다. 성함이")
check("완성된 문장만 반환", sentences == ["본인 확인이 필요합니다."], str(sentences))
check("종결부호 없는 잔여분은 버퍼에 남음", rest == " 성함이", repr(rest))

if failed == 0:
    print("\n스모크 테스트 통과 — 결정론적 코어는 정상입니다.\n")
else:
    print(f"\n{failed}건 실패\n")
sys.exit(0 if failed == 0 else 1)
