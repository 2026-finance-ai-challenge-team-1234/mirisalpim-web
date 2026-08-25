"""POC 전용 패키지. 실제 서비스 코드가 아니다 - 검증 끝나면 이 폴더째 지워도 ai_core 는 영향 없다."""

from __future__ import annotations

import os
from pathlib import Path

# ai_core/config.py 와 같은 .env(mirisalpim-web/ 루트)를 읽는다. ai_core 를 먼저 import
# 하지 않고 poc.stt/poc.tts 를 단독으로 써도 인증 정보가 로드되도록 여기서 직접 처리한다.
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
if _ENV_PATH.exists():
    for _line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _, _v = _line.partition("=")
        os.environ.setdefault(_k.strip(), _v.strip().strip("\"'"))
