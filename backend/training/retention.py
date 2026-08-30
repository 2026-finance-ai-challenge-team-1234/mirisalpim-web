"""훈련 대화 원문 보존 기한과 만료 처리.

Django 세션 쿠키가 만료돼도 training_turn 행은 자동으로 지워지지 않는다. 따라서
DB 세션의 마지막 활동 시각을 별도로 추적하고, 30분 이상 방치된 세션은 원문을
비운 뒤 만료 상태로 닫는다.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import connection, transaction
from django.utils import timezone

from .models import Session, Turn

logger = logging.getLogger(__name__)

OPEN_STATUSES = (
    Session.STATUS_ACTIVE,
    Session.STATUS_AWAITING_JUDGMENT,
    Session.STATUS_JUDGING,
)
CLEANUP_CACHE_KEY = "training:expired-session-cleanup"
CLEANUP_INTERVAL_SECONDS = 300
DEFAULT_BATCH_SIZE = 100


def retention_cutoff(now=None):
    """익명 웹 세션과 같은 30분 비활성 기준 시각을 반환한다."""
    current = now or timezone.now()
    return current - timedelta(seconds=settings.SESSION_COOKIE_AGE)


def is_expired(session, now=None):
    return (
        session.status in OPEN_STATUSES
        and session.last_activity_at < retention_cutoff(now)
    )


def discard_transcript(session):
    """타임라인 메타데이터는 남기고 발화 원문만 파기한다."""
    session.turns.exclude(text="").update(text="")


def expire_locked_session(session, now=None):
    """행 잠금을 잡은 세션을 만료 처리한다."""
    current = now or timezone.now()
    discard_transcript(session)
    session.status = Session.STATUS_EXPIRED
    session.ended_at = session.ended_at or current
    session.last_activity_at = current
    session.save(update_fields=["status", "ended_at", "last_activity_at"])


def cleanup_expired_sessions(*, now=None, batch_size=DEFAULT_BATCH_SIZE):
    """방치된 세션 한 배치를 잠그고 원문을 파기한다.

    반환값은 이번 호출에서 만료한 세션 수다. 여러 웹 워커가 동시에 실행해도
    PostgreSQL에서는 skip_locked로 같은 세션을 중복 처리하지 않는다.
    """
    current = now or timezone.now()
    cutoff = retention_cutoff(current)
    lock_options = (
        {"skip_locked": True}
        if connection.features.has_select_for_update_skip_locked
        else {}
    )

    with transaction.atomic():
        sessions = list(
            Session.objects.select_for_update(**lock_options)
            .filter(status__in=OPEN_STATUSES, last_activity_at__lt=cutoff)
            .order_by("last_activity_at")[:batch_size]
        )
        for session in sessions:
            expire_locked_session(session, current)
    return len(sessions)


def maybe_cleanup_expired_sessions():
    """일반 요청 경로에서 최대 5분에 한 번, 작은 배치만 정리한다.

    정리 실패 때문에 bootstrap까지 실패하면 안 되므로 오류는 로그에 남기고 삼킨다.
    운영자가 전체 정리를 강제할 때는 cleanup_expired_sessions 관리 명령을 쓴다.
    """
    try:
        if not cache.add(
            CLEANUP_CACHE_KEY, True, timeout=CLEANUP_INTERVAL_SECONDS
        ):
            return 0
        return cleanup_expired_sessions()
    except Exception:
        cache.delete(CLEANUP_CACHE_KEY)
        logger.exception("만료된 훈련 세션 정리에 실패했습니다")
        return 0
