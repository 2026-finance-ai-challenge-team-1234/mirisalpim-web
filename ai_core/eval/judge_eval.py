"""판정기 정확도 검증 - engine.step() 을 실제로 돌리면서 그 자리에서 채점한다.

ai-test/cli/judge_eval.py 는 저장된 PoC-1 로그를 재생하는 2단계 구조였지만,
지금 engine.step() 은 이미 판정기가 붙어 있는 실제 경로라 그럴 필요가 없다 -
스크립트된 훈련생 발화로 대화를 진행하면서 매 턴 판정을 즉시 보여주고 채점받는다.

시나리오 2개 × 대응 스타일 2가지를 라운드로빈으로 섞는다:
  sc-02 (사기, 검찰 사칭) - 위험행동·전환을 제대로 잡아내는지
  nm-01 (정상, 경찰 민원 회신) - 정상 시나리오에서 위험행동을 오탐하지 않는지
     (지금까지 한 번도 검증 안 된 축)

합격 기준: 80%+ (ai-test/README.md 의 기존 관행과 동일).

사용법 (mirisalpim-web/ 에서, LLM_PROVIDER=gemini 필요):
    python -m ai_core.eval.judge_eval [최대 라벨 수]
"""

from __future__ import annotations

import json
import sys
import time
from itertools import chain
from pathlib import Path
from typing import Iterator

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except (AttributeError, OSError):
        pass

from ai_core.config import PROVIDER  # noqa: E402
from ai_core.engine import Engine, TurnOutcome, load_scenario, start_session, step  # noqa: E402

BOLD, RED, GREEN, YELLOW, CYAN, DIM, RESET = (
    "\x1b[1m",
    "\x1b[31m",
    "\x1b[32m",
    "\x1b[33m",
    "\x1b[36m",
    "\x1b[2m",
    "\x1b[0m",
)

RESULTS_DIR = Path(__file__).resolve().parent / "results"

# ── 시나리오 2개 × 대응 스타일 2가지, 스크립트된 훈련생 발화 ───────────────

CONVERSATIONS: dict[str, list[str]] = {
    "sc-02·순응형": [
        "네? 무슨 일이시죠? 제 계좌가 왜요?",
        "아... 그러면 어떻게 해야 하나요?",
        "네, 성함은 홍길동이고 생년월일은 1985년 3월생입니다.",
        "네 알겠습니다. 지금 방에 혼자 있어요.",
        "무섭네요... 제가 뭘 잘못한 거죠?",
        "네, 시키는 대로 할게요. 어떻게 하면 되나요?",
    ],
    "sc-02·의심형": [
        "네? 저는 그런 적 없는데요. 진짜 검찰 맞아요?",
        "사건번호랑 소속 부서를 다시 말씀해 주세요. 제가 직접 확인해볼게요.",
        "개인정보는 전화로 못 알려드립니다. 서면으로 보내주세요.",
        "가족한테 말하면 왜 안 되나요? 이상한데요.",
        "저 지금 전화 끊고 112에 신고하겠습니다.",
        "안전계좌라는 게 어디 있어요? 그런 제도 없잖아요.",
    ],
    "nm-01·순응형": [
        "네, 무슨 민원 회신이신가요?",
        "아 그러시군요. 알겠습니다.",
        "네, 대표번호로 확인해봐도 될까요?",
        "네 감사합니다, 확인해볼게요.",
        "네, 잘 알겠습니다. 수고하세요.",
    ],
    "nm-01·의심형": [
        "이거 보이스피싱 아니에요? 갑자기 왜 전화하신 거예요?",
        "진짜 경찰 맞는지 어떻게 믿어요?",
        "그럼 제가 대표번호로 다시 걸어서 확인해도 되나요?",
        "왜 자꾸 금융정보는 안 물어보시는 거예요? 뭔가 이상한데.",
        "알겠습니다, 제가 직접 확인해보고 다시 연락드릴게요.",
    ],
}


def scenario_id_of(label: str) -> str:
    return label.split("·")[0]


def run_conversation(label: str) -> Iterator[tuple[str, Engine, TurnOutcome]]:
    """스크립트된 발화로 실제 engine.step() 을 돌리며 (label, engine, outcome) 을 낸다."""
    scenario = load_scenario(scenario_id_of(label))
    engine = start_session(scenario)
    for user_text in CONVERSATIONS[label]:
        outcome = step(engine, user_text)
        yield label, engine, outcome
        if outcome.ended:
            break


def round_robin() -> Iterator[tuple[str, Engine, TurnOutcome]]:
    """네 대화를 한 턴씩 번갈아 섞는다 - 같은 조합이 연달아 나오지 않게."""
    iters = [iter(run_conversation(label)) for label in CONVERSATIONS]
    while iters:
        alive = []
        for it in iters:
            try:
                item = next(it)
            except StopIteration:
                continue
            yield item
            alive.append(it)
        iters = alive


def print_context(engine: Engine) -> None:
    for t in engine.state.transcript[-3:]:
        who = f"{RED}상대{RESET}" if t.role == "scammer" else f"{CYAN}훈련생{RESET}"
        print(f"  {who} {t.text}")


def print_judgment(outcome: TurnOutcome) -> None:
    print(f"{YELLOW}판정기 출력{RESET}")
    print(f"  advance_proposed : {outcome.advance_proposed}  (코드 최종승인: stage_changed={outcome.stage_changed})")
    print(f"  risky_actions    : {outcome.risky_actions or '없음'}")
    print(f"  resisted         : {outcome.resisted}")


def main() -> None:
    if PROVIDER != "gemini":
        print(
            f"{RED}✗ 오류{RESET}  구조화 출력(response_schema)은 지금 gemini 경로에만 구현돼 있습니다.\n"
            f"    LLM_PROVIDER=gemini python -m ai_core.eval.judge_eval 로 실행하세요.",
            file=sys.stderr,
        )
        sys.exit(1)

    max_labels = int(sys.argv[1]) if len(sys.argv) > 1 else 20

    print(f"{YELLOW}판정기 정확도 검증{RESET} {DIM}(대화 실시간 생성, 최대 {max_labels}개 라벨){RESET}")
    print(f"{DIM}각 판정을 보고 y(동의)/n(비동의)/s(건너뛰기)/q(종료) 로 응답하세요{RESET}\n")

    agree = total = 0
    records: list[dict] = []

    for label, engine, outcome in round_robin():
        if total >= max_labels:
            break
        print(f"{DIM}{'─' * 60}{RESET}")
        print(f"[{label}] {DIM}턴 {engine.state.turn}{RESET}")
        print_context(engine)
        print()
        print_judgment(outcome)

        while True:
            ans = input(f"\n{BOLD}동의하십니까? [y/n/s/q]{RESET} ").strip().lower()
            if ans in ("y", "n", "s", "q"):
                break
        if ans == "q":
            print(f"\n{DIM}중단됨.{RESET}")
            break
        if ans == "s":
            continue

        total += 1
        correct = ans == "y"
        agree += int(correct)
        records.append(
            {
                "label": label,
                "turn": engine.state.turn,
                "advance_proposed": outcome.advance_proposed,
                "stage_changed": outcome.stage_changed,
                "risky_actions": outcome.risky_actions,
                "resisted": outcome.resisted,
                "humanAgrees": correct,
            }
        )

    rate = round(agree / total * 100) if total else 0
    print(f"\n{DIM}{'═' * 60}{RESET}")
    verdict = f"{GREEN}합격{RESET}" if rate >= 80 else f"{RED}불합격 - 기준 80%{RESET}"
    print(f"{YELLOW}결과{RESET}  판정 정확도 {agree}/{total} ({rate}%)  {verdict}")

    if records:
        RESULTS_DIR.mkdir(exist_ok=True)
        out_file = RESULTS_DIR / f"judge-{time.strftime('%m%d-%H%M%S')}.json"
        out_file.write_text(
            json.dumps({"rate": rate, "records": records}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"{DIM}라벨 기록: {out_file}{RESET}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{DIM}중단됨.{RESET}")
    except Exception as e:  # noqa: BLE001
        print(f"{RED}오류:{RESET} {e}", file=sys.stderr)
        sys.exit(1)
