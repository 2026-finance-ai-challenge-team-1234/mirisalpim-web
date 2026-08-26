import logging

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class TrainingConfig(AppConfig):
    name = 'training'

    def ready(self):
        """기동 시 LLM 설정을 확인해 로그로 알린다.

        ai_core.config 의 LLM_PROVIDER 기본값은 ollama 다. Railway 변수에
        LLM_PROVIDER 와 해당 API 키를 넣지 않으면 ai_core.llm 이 import 시점에
        sys.exit(1) 을 불러(llm.py 하단의 임포트 시 1회 검증) 워커가 부팅 중에
        그대로 죽는다. 그때 남는 단서는 ai_core 가 stderr 로 찍는 몇 줄뿐이라
        크래시 루프의 원인을 찾기 어렵다. ready() 는 그보다 먼저 돌기 때문에,
        여기서 남긴 로그가 "무엇이 없어서 죽었는지" 를 알려준다.

        ⚠️ 여기서 예외를 던지지 않는다. ready() 는 migrate·collectstatic·
        seed_scenarios 에서도 실행되고, 그 명령들은 빌드 단계에서 API 키 없이
        돈다. 던지면 이미지 빌드부터 깨진다.
        """
        if getattr(settings, "IS_TEST", False):
            return

        try:
            from ai_core.config import PROVIDER, validate_config
        except Exception as exc:  # ai_core 를 못 읽는 상황도 조용히 넘기지 않는다
            logger.error("ai_core 설정을 불러오지 못했습니다: %s", exc)
            return

        problems = validate_config()
        logger.info("LLM 프로바이더: %s", PROVIDER)
        for problem in problems:
            message = problem.message.replace("\n", " ").strip()
            if problem.level == "error":
                logger.error("LLM 설정 오류 - %s", message)
            else:
                logger.warning("LLM 설정 경고 - %s", message)
