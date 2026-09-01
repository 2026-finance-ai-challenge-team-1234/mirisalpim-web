"""두 Gemini 판정기를 같은 대화 상태에서 나란히 비교한다.

각 케이스마다 두 모델이 완전히 같은 transcript와 현재 단계를 받는다. 사람이 어느
출력이 맞는지 한 번만 표시하면 모델별 정확도와 p50/p95 지연을 함께 저장한다.
사기범 발화는 다음 케이스의 자연스러운 맥락을 만들기 위해 한 번만 생성하며, 비교
대상 판정 결과로 상태를 바꾸지 않아 두 모델 사이의 대화 분기를 막는다.

사용법 (저장소 루트):
    python -m ai_core.eval.judge_compare
    python -m ai_core.eval.judge_compare --max-cases 8
    python -m ai_core.eval.judge_compare \
        --models gemini-3.7-flash gemini-3.5-flash-lite

입력: a=둘 다 정확, 1=첫 모델만 정확, 2=둘째 모델만 정확,
      n=둘 다 부정확, s=건너뛰기, q=종료
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import statistics
import sys
import time
from itertools import zip_longest
from pathlib import Path

from ai_core.agents.judge import generate_judge_turn
from ai_core.config import PROVIDER
from ai_core.engine import Engine, load_scenario, start_session, step
from ai_core.eval.judge_eval import CONVERSATIONS, scenario_id_of
from ai_core.state import current_stage, record_turn

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models",
        nargs=2,
        default=["gemini-3.7-flash", "gemini-3.5-flash-lite"],
        metavar=("BASELINE", "CANDIDATE"),
    )
    parser.add_argument("--max-cases", type=int, default=20)
    return parser.parse_args()


def _state_with_user_turn(engine: Engine, user_text: str):
    state = copy.deepcopy(engine.state)
    state.turn += 1
    record_turn(state, "user", user_text, current_stage(engine.scenario, state).id)
    return state


def _judge_with_model(engine: Engine, user_text: str, model: str):
    state = _state_with_user_turn(engine, user_text)
    previous = os.environ.get("GEMINI_JUDGE_MODEL")
    os.environ["GEMINI_JUDGE_MODEL"] = model
    try:
        return generate_judge_turn(engine.scenario, state)
    finally:
        if previous is None:
            os.environ.pop("GEMINI_JUDGE_MODEL", None)
        else:
            os.environ["GEMINI_JUDGE_MODEL"] = previous


def _round_robin_cases():
    """네 대화를 한 턴씩 번갈아 낸다 - judge_eval.round_robin() 과 같은 의도.

    라벨 순서대로 몰아서 채점하면 두 가지가 어긋난다. (1) 기본 --max-cases 20 에서
    분포가 6/6/5/3 이 되어 마지막 페르소나가 과소표집된다(라운드로빈이면 5/5/5/5).
    (2) 사람이 같은 대화 6턴을 연속으로 채점하게 되어 순서 편향이 생긴다.
    모델 A/B 비교에서는 이 둘이 결론을 뒤집을 수 있다.
    """
    return [
        (label, user_text)
        for column in zip_longest(*CONVERSATIONS.values())
        for label, user_text in zip(CONVERSATIONS, column)
        if user_text is not None
    ]


def _p95(values):
    ordered = sorted(values)
    if not ordered:
        return 0
    return ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]


def _print_result(index, configured_model, result):
    print(f"  [{index}] {configured_model} (실제 {result.model}, {result.latency_ms}ms)")
    print(f"      advance={result.advance_stage} resisted={result.resisted}")
    print(f"      risky={result.risky_actions or '없음'}")
    print(f"      근거={result.reasoning}")


def main():
    args = parse_args()
    if PROVIDER != "gemini":
        raise SystemExit("LLM_PROVIDER=gemini 일 때만 실행할 수 있습니다.")
    if args.max_cases < 1:
        raise SystemExit("--max-cases 는 1 이상이어야 합니다.")
    if args.models[0] == args.models[1]:
        # 모델별 집계를 이름 기준 dict 로 잡아서, 같은 이름이면 두 항목이 한 칸에
        # 겹쳐 정확도가 두 배로 계산된다(실측: 6/3 = 200%).
        raise SystemExit("--models 는 서로 다른 두 모델이어야 합니다.")

    scores = {model: 0 for model in args.models}
    latencies = {model: [] for model in args.models}
    records = []
    graded = 0

    # 대화마다 엔진을 따로 두고 케이스는 라운드로빈으로 섞는다. 단일 루프라
    # 라벨 경계의 이중 break 가 사라진다(예전에는 첫 라벨의 발화 목록이 비면
    # 종료 조건이 아직 대입되지 않은 answer 를 읽어 UnboundLocalError 가 났다).
    engines = {
        label: start_session(load_scenario(scenario_id_of(label)))
        for label in CONVERSATIONS
    }

    for label, user_text in _round_robin_cases():
        if graded >= args.max_cases:
            break
        engine = engines[label]

        print("\n" + "─" * 72)
        print(f"[{label}] 단계={current_stage(engine.scenario, engine.state).id}")
        for turn in engine.state.transcript[-3:]:
            who = "상대" if turn.role == "scammer" else "훈련생"
            print(f"  {who}: {turn.text}")
        print(f"  훈련생: {user_text}")

        results = [
            _judge_with_model(engine, user_text, model) for model in args.models
        ]
        for index, (model, result) in enumerate(
            zip(args.models, results, strict=True), start=1
        ):
            _print_result(index, model, result)

        while True:
            answer = input("정확한 출력 [a/1/2/n/s/q]: ").strip().lower()
            if answer in {"a", "1", "2", "n", "s", "q"}:
                break
        if answer == "q":
            break
        if answer != "s":
            graded += 1
            correct = {
                args.models[0]: answer in {"a", "1"},
                args.models[1]: answer in {"a", "2"},
            }
            for model, result in zip(args.models, results, strict=True):
                scores[model] += int(correct[model])
                latencies[model].append(result.latency_ms)
            records.append(
                {
                    "label": label,
                    "turn": engine.state.turn + 1,
                    "humanChoice": answer,
                    "results": [
                        {
                            "configuredModel": model,
                            "actualModel": result.model,
                            "latencyMs": result.latency_ms,
                            "advanceStage": result.advance_stage,
                            "riskyActions": result.risky_actions,
                            "resisted": result.resisted,
                            "reasoning": result.reasoning,
                            "humanCorrect": correct[model],
                        }
                        for model, result in zip(args.models, results, strict=True)
                    ],
                }
            )

        # 다음 판정 케이스용 맥락만 만든다. 어느 후보의 판정을 채택하면 이후
        # transcript가 갈라지므로 판정기를 끄고 사기범 발화만 한 번 생성한다.
        step(engine, user_text, use_judge=False, use_safety=False)

    summary = {}
    print("\n" + "═" * 72)
    for model in args.models:
        values = latencies[model]
        rate = round(scores[model] / graded * 100, 1) if graded else 0.0
        summary[model] = {
            "correct": scores[model],
            "graded": graded,
            "accuracyPercent": rate,
            "p50Ms": round(statistics.median(values)) if values else 0,
            "p95Ms": _p95(values),
        }
        print(
            f"{model}: 정확도 {scores[model]}/{graded} ({rate}%), "
            f"p50 {summary[model]['p50Ms']}ms, p95 {summary[model]['p95Ms']}ms"
        )

    if records:
        RESULTS_DIR.mkdir(exist_ok=True)
        output = RESULTS_DIR / f"judge-compare-{time.strftime('%m%d-%H%M%S')}.json"
        output.write_text(
            json.dumps(
                {"models": args.models, "summary": summary, "records": records},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"결과 저장: {output}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n중단됨.", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001 - CLI 경계에서 읽을 수 있는 오류로 변환
        print(f"오류: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
