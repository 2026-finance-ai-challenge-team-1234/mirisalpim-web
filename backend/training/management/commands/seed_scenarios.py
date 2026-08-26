"""시나리오 카드 JSON → DB 적재.

검증은 ai_core.validate 를 그대로 쓴다 — AI 코어 로더와 DB importer 가 서로 다른
규칙을 갖지 않도록 검증 로직은 한 곳에만 둔다.

사용법:
    python manage.py seed_scenarios                 # settings.SCENARIO_SEED_DIR
    python manage.py seed_scenarios --dir ../../scenario/json_data
    python manage.py seed_scenarios --check         # 검증만, DB 미변경

카드에 있지만 DB 로 옮기지 않는 필드(팀원 조사 원본 등)는 삭제하지 않고 무시한다.
무시된 키는 -v 2 로 확인할 수 있다 — "왜 이 설정이 대화에 반영되지 않지?" 를
디버깅으로 찾지 않기 위한 것이다.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import ProtectedError

from ai_core.validate import validate

from training.models import Scenario, Stage, TellPoint

#: importer 가 실제로 읽는 키. 이 목록에 없는 키는 무시된다 (에러 아님)
CONSUMED_KEYS = {
    "schema_version",
    "scenario_id",
    "category",
    "track",
    "target_tracks",
    "title",
    "source",
    "source_refs",
    "source_review_status",
    "is_scam",
    "difficulty",
    "goal",
    "learning_objectives",
    "max_turns",
    "persona",
    "stages",
    "tell_points",
    "end_conditions",
    "forbidden",
    "debrief_points",
}


class Command(BaseCommand):
    help = "시나리오 카드 JSON 을 Scenario/Stage/TellPoint 로 적재한다"

    def add_arguments(self, parser):
        parser.add_argument("--dir", dest="directory", default=None)
        parser.add_argument(
            "--check", action="store_true", help="검증만 하고 DB 를 바꾸지 않는다"
        )

    def handle(self, *args, **options):
        directory = Path(options["directory"] or settings.SCENARIO_SEED_DIR)
        if not directory.is_dir():
            raise CommandError(f"디렉터리가 없습니다: {directory}")

        files = sorted(directory.glob("*.json"))
        if not files:
            raise CommandError(f"JSON 이 없습니다: {directory}")

        cards, invalid = [], 0
        for f in files:
            card = json.loads(f.read_text(encoding="utf-8"))
            errors = validate(card)
            if errors:
                invalid += 1
                self.stderr.write(self.style.ERROR(f"✗ {f.name}"))
                for msg in errors:
                    self.stderr.write(f"    - {msg}")
                continue
            cards.append((f.name, card))

        if invalid:
            raise CommandError(f"{invalid}개 카드가 검증에 실패해 아무것도 적재하지 않았습니다")

        if options["check"]:
            self.stdout.write(self.style.SUCCESS(f"{len(cards)}개 카드 검증 통과 (DB 미변경)"))
            return

        verbosity = int(options.get("verbosity", 1))
        with transaction.atomic():
            for name, card in cards:
                self._load(card, name, verbosity)

        self.stdout.write(self.style.SUCCESS(f"{len(cards)}개 시나리오 적재 완료"))

    def _load(self, card: dict, filename: str, verbosity: int) -> None:
        persona = card["persona"]
        scenario, _ = Scenario.objects.update_or_create(
            scenario_id=card["scenario_id"],
            defaults={
                "schema_version": card.get("schema_version", 1),
                "category": card["category"],
                "track": card["track"],
                "target_tracks": card["target_tracks"],
                "title": card["title"],
                "source": card["source"],
                "source_refs": card.get("source_refs", []),
                "source_review_status": card.get("source_review_status", "human_reviewed"),
                "is_scam": card["is_scam"],
                "difficulty": card["difficulty"],
                "goal": card["goal"],
                "learning_objectives": card.get("learning_objectives", []),
                "max_turns": card["max_turns"],
                "persona_display_name": persona["display_name"],
                "persona_name": persona.get("name", ""),
                "persona_org": persona.get("org", ""),
                "persona_role": persona.get("role", ""),
                "persona_tone": persona["tone"],
                "persona_rules": persona.get("rules", []),
                "persona_resistance_strategy": persona.get("resistance_strategy", []),
                "persona_voice_preset": persona["voice_preset"],
                "forbidden": card["forbidden"],
                "end_conditions": card.get("end_conditions", []),
                "debrief_points": card.get("debrief_points", []),
            },
        )

        stages = self._sync_stages(scenario, card)
        self._sync_tell_points(scenario, card, stages)

        ignored = sorted(set(card) - CONSUMED_KEYS)
        line = f"  {card['scenario_id']} ({card['track']}) stages={len(stages)} tp={len(card['tell_points'])}"
        if ignored:
            line += f" — 무시된 필드: {', '.join(ignored)}"
        if verbosity >= 2 or ignored:
            self.stdout.write(line)

    def _sync_stages(self, scenario, card: dict) -> dict:
        """단계를 stage_key 기준으로 갱신한다.

        ⚠️ 통째로 지우고 다시 만들지 않는다. Turn.stage 가 PROTECT 라서, 한 번이라도
        진행된 세션이 있으면 delete() 가 ProtectedError 를 낸다. 이 명령은 컨테이너가
        기동할 때마다 돌기 때문에(Dockerfile CMD) 그러면 재배포부터 서비스가 못 뜬다.
        갱신 방식이면 참조는 그대로 두고 내용만 바뀐다.
        """
        stages = {}
        for i, s in enumerate(card["stages"]):
            stage, _ = Stage.objects.update_or_create(
                scenario=scenario,
                stage_key=s["id"],
                defaults={
                    "order_index": i,
                    "objective": s["objective"],
                    "opening": s.get("opening"),
                    "min_turns": s["min_turns"],
                    "tactics": s.get("tactics", []),
                    "advance_when": s.get("advance_when", []),
                },
            )
            stages[s["id"]] = stage

        self._delete_removed(
            scenario.stages.exclude(stage_key__in=stages), card["scenario_id"], "단계"
        )
        return stages

    def _sync_tell_points(self, scenario, card: dict, stages: dict) -> None:
        """단서를 tp_key 기준으로 갱신한다.

        예전에는 단계가 CASCADE 로 지워질 때 단서도 함께 사라져서 create 만으로
        충분했다. 이제 단계가 남으므로 여기도 갱신해야 unique(scenario, tp_key) 에
        걸리지 않는다.
        """
        for tp in card["tell_points"]:
            TellPoint.objects.update_or_create(
                scenario=scenario,
                tp_key=tp["id"],
                defaults={
                    "stage": stages[tp["stage"]],
                    "signal_type": tp.get("signal_type", "risk"),
                    "trigger": tp["trigger"],
                    "why": tp["why"],
                    "weight": tp["weight"],
                    "first_detectable_turn": tp["first_detectable_turn"],
                },
            )

        keys = [tp["id"] for tp in card["tell_points"]]
        # SessionTellPointHit 이 CASCADE 라 빠진 단서의 기록도 함께 정리된다
        self._delete_removed(
            scenario.tell_points.exclude(tp_key__in=keys), card["scenario_id"], "단서"
        )

    def _delete_removed(self, queryset, scenario_id: str, label: str) -> None:
        """카드에서 빠진 행을 지운다. 참조가 걸려 있으면 무엇을 치우면 되는지 알린다."""
        try:
            queryset.delete()
        except ProtectedError as e:
            raise CommandError(
                f"{scenario_id}: 카드에서 빠진 {label}를 진행 중이던 세션이 참조하고 있어 "
                f"삭제할 수 없습니다. 세션을 정리한 뒤 다시 실행하세요. ({e})"
            ) from e
