"""ai_core.SessionState ↔ DB 변환 어댑터.

ai_core 는 손대지 않는다. ai_core 의 SessionState 는 메모리 dataclass 라서 HTTP 요청이
끝나면 사라지고, 배포는 워커가 여러 개여서 3턴째 요청이 1턴째와 다른 프로세스로 갈 수
있다. 그래서 매 턴 DB 에서 복원하고 다시 저장한다.

시나리오는 여기서 다루지 않는다 - ai_core.load_scenario() 가 data/scenarios/*.json 을
직접 읽는다. DB 의 Scenario/Stage/TellPoint 는 목록 조회와 리포트용이고, 훈련 실행의
원본은 JSON 쪽이다 (둘 다 같은 파일에서 나오므로 stage 순서와 키가 일치한다).

전제: SessionState 의 transcript / risky_actions / hit_tell_points 는 ai_core 안에서
append 만 된다 (record_turn, apply_judgment, mark_tell_points). 그래서 저장은 "DB 에
이미 있는 개수 이후만 추가"하는 증분 방식으로 충분하다.
"""

from ai_core.types import RiskyAction, SessionState, Turn, UserJudgment
from django.utils import timezone

from .models import RiskyAction as RiskyActionRow
from .models import SessionTellPointHit, Stage, TellPoint
from .models import Turn as TurnRow
from .models import UserJudgment as UserJudgmentRow


def load_state(session):
    """Session 행과 자식 행들로 ai_core 의 SessionState 를 복원한다."""
    stage_index = session.current_stage.order_index if session.current_stage else 0

    transcript = [
        Turn(
            role=row.role,
            text=row.text,
            turn=row.turn_no,
            stage=row.stage.stage_key,
            latency_ms=row.latency_ms,
        )
        for row in session.turns.select_related("stage").order_by("turn_no", "created_at")
    ]

    risky_actions = [
        RiskyAction(turn=row.turn_no, type=row.action_type)
        for row in session.risky_actions.order_by("turn_no", "created_at")
    ]

    hit_tell_points = [
        row.tell_point.tp_key
        for row in session.tell_point_hits.select_related("tell_point").order_by("hit_turn")
    ]

    judgment_row = UserJudgmentRow.objects.filter(session=session).first()
    user_judgment = (
        UserJudgment(
            turn=judgment_row.judged_turn or 0,
            is_scam_guess=judgment_row.is_scam_guess,
        )
        if judgment_row
        else None
    )

    return SessionState(
        scenario_id=session.scenario_id,
        session_id=str(session.session_id),
        difficulty=session.difficulty,
        turn=session.turn,
        stage_index=stage_index,
        turns_in_stage=session.turns_in_stage,
        risky_actions=risky_actions,
        resistance_count=session.resistance_count,
        hit_tell_points=hit_tell_points,
        user_judgment=user_judgment,
        transcript=transcript,
    )


def save_state(session, state):
    """SessionState 를 DB 에 반영한다. 새로 늘어난 항목만 추가한다."""
    stages = {s.stage_key: s for s in Stage.objects.filter(scenario_id=session.scenario_id)}

    _append_turns(session, state, stages)
    _append_risky_actions(session, state)
    _append_tell_point_hits(session, state)

    session.turn = state.turn
    session.turns_in_stage = state.turns_in_stage
    session.resistance_count = state.resistance_count
    session.current_stage = _stage_at(session, state.stage_index, stages)
    session.last_activity_at = timezone.now()
    session.save(
        update_fields=[
            "turn",
            "turns_in_stage",
            "resistance_count",
            "current_stage",
            "last_activity_at",
        ]
    )


def _stage_at(session, stage_index, stages):
    for stage in stages.values():
        if stage.order_index == stage_index:
            return stage
    raise ValueError(
        f"시나리오 {session.scenario_id} 에 order_index={stage_index} 인 stage 가 없습니다"
    )


def _append_turns(session, state, stages):
    already = session.turns.count()
    TurnRow.objects.bulk_create(
        [
            TurnRow(
                session=session,
                turn_no=turn.turn,
                role=turn.role,
                text=turn.text,
                stage=stages[turn.stage],
                latency_ms=turn.latency_ms,
            )
            for turn in state.transcript[already:]
        ]
    )


def _append_risky_actions(session, state):
    already = session.risky_actions.count()
    RiskyActionRow.objects.bulk_create(
        [
            RiskyActionRow(
                session=session, turn_no=action.turn, action_type=action.type
            )
            for action in state.risky_actions[already:]
        ]
    )


def _append_tell_point_hits(session, state):
    already = set(
        session.tell_point_hits.select_related("tell_point").values_list(
            "tell_point__tp_key", flat=True
        )
    )
    new_keys = [key for key in state.hit_tell_points if key not in already]
    if not new_keys:
        return

    tell_points = {
        tp.tp_key: tp
        for tp in TellPoint.objects.filter(
            scenario_id=session.scenario_id, tp_key__in=new_keys
        )
    }
    SessionTellPointHit.objects.bulk_create(
        [
            SessionTellPointHit(
                session=session, tell_point=tell_points[key], hit_turn=state.turn
            )
            for key in new_keys
            if key in tell_points
        ]
    )
