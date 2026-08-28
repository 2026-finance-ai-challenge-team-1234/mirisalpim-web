"""Chirp 음성 — 브라우저 오디오 ↔ 텍스트.

poc/stt.py · poc/tts.py 에서 검증한 것을 운영 경로로 옮긴 것이다. 옮기면서 세 가지가
달라졌다.

  1. 재생을 하지 않는다. poc/tts.py 는 sounddevice 로 데스크톱 스피커에 직접
     재생하는데, 서버는 오디오 바이트만 만들고 재생은 브라우저가 한다.
     그래서 sounddevice/soundfile 을 의존성에 넣지 않는다.
  2. 자격증명을 환경변수 JSON 에서 읽는다. poc 는 GOOGLE_APPLICATION_CREDENTIALS
     (파일 경로)를 쓰는데 배포 환경에는 GCP_CREDENTIALS_JSON (내용)이 들어온다.
     둘 다 지원한다.
  3. MP3 로 합성한다. poc 는 WAV(LINEAR16) 인데 24kHz mono 기준 초당 약 48KB 라,
     세 문장이면 200KB 에 가깝다. 매 턴 그만큼 실어 보낼 이유가 없다.

⚠️ 오디오를 디스크에 쓰지 않는다. poc/server.py 는 검증 기록용으로 turn-N-user.webm
   을 남기는데, 운영에서는 훈련생 음성이 서버에 남으면 안 된다
   (기획서 10절: 개인정보 미수집 / 대화는 세션 종료 시 파기).
"""

import json
import logging
import os
from functools import lru_cache
from pathlib import Path

from google.api_core.client_options import ClientOptions
from google.cloud import texttospeech
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

#: Chirp 2 가 GA 로 제공되는 리전 중 하나 (poc/stt.py 와 동일).
REGION = "us-central1"
LANGUAGE = "ko-KR"

#: 시나리오 카드의 voice_preset → Chirp 3 HD 화자.
#: 공개 프리셋만 쓴다 — 실존 인물 음성 복제는 하지 않는다 (기획서 10절).
#: ⚠️ 시나리오 데이터에 neutral_formal(15개)과 formal_neutral(2개)이 섞여 있다.
#:    같은 뜻으로 보여 둘 다 같은 화자로 보낸다. 시나리오 담당 확인이 필요하다.
VOICE_BY_PRESET = {
    "male_40s_formal": "ko-KR-Chirp3-HD-Charon",
    "neutral_formal": "ko-KR-Chirp3-HD-Charon",
    "formal_neutral": "ko-KR-Chirp3-HD-Charon",
    "neutral_casual": "ko-KR-Chirp3-HD-Kore",
    "casual_family": "ko-KR-Chirp3-HD-Kore",
}
DEFAULT_VOICE = "ko-KR-Chirp3-HD-Charon"

#: 브라우저 MediaRecorder 기본 출력. 프론트가 다른 값을 쓰면 요청에서 넘겨받는다.
DEFAULT_SAMPLE_RATE = 48000


class VoiceUnavailable(RuntimeError):
    """자격증명이 없거나 음성 API 를 부를 수 없는 상태."""


@lru_cache(maxsize=1)
def _credentials_info():
    """서비스 계정 JSON. 배포는 환경변수 내용, 로컬은 파일 경로를 쓴다."""
    raw = os.environ.get("GCP_CREDENTIALS_JSON")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise VoiceUnavailable("GCP_CREDENTIALS_JSON 이 올바른 JSON 이 아닙니다") from exc

    path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if path:
        # 상대 경로는 저장소 루트 기준으로 푼다. Django 는 backend/ 에서 돌아서
        # ".gcp-credentials.json" 같은 값을 그대로 열면 못 찾는다.
        resolved = Path(path)
        if not resolved.is_absolute():
            resolved = Path(__file__).resolve().parents[2] / path
        if resolved.exists():
            return json.loads(resolved.read_text(encoding="utf-8"))

    raise VoiceUnavailable(
        "음성 기능에 GCP 자격증명이 필요합니다 "
        "(GCP_CREDENTIALS_JSON 또는 GOOGLE_APPLICATION_CREDENTIALS)"
    )


@lru_cache(maxsize=1)
def _credentials():
    return service_account.Credentials.from_service_account_info(_credentials_info())


@lru_cache(maxsize=1)
def _speech_client():
    return SpeechClient(
        credentials=_credentials(),
        client_options=ClientOptions(api_endpoint=f"{REGION}-speech.googleapis.com"),
    )


@lru_cache(maxsize=1)
def _tts_client():
    return texttospeech.TextToSpeechClient(credentials=_credentials())


def is_available():
    """자격증명이 갖춰졌는가. 기동 시 features 계산에 쓴다."""
    try:
        _credentials_info()
    except VoiceUnavailable:
        return False
    return True


def transcribe(audio_bytes, sample_rate=DEFAULT_SAMPLE_RATE):
    """브라우저 MediaRecorder 의 webm/opus 오디오를 한국어 텍스트로 바꾼다.

    인식된 발화가 없으면 빈 문자열. 오디오는 메모리에서만 다루고 저장하지 않는다.
    """
    project_id = _credentials_info()["project_id"]
    config = cloud_speech.RecognitionConfig(
        explicit_decoding_config=cloud_speech.ExplicitDecodingConfig(
            encoding=cloud_speech.ExplicitDecodingConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=sample_rate,
            audio_channel_count=1,
        ),
        language_codes=[LANGUAGE],
        model="chirp_2",
    )
    response = _speech_client().recognize(
        request=cloud_speech.RecognizeRequest(
            recognizer=f"projects/{project_id}/locations/{REGION}/recognizers/_",
            config=config,
            content=audio_bytes,
        )
    )
    parts = [r.alternatives[0].transcript for r in response.results if r.alternatives]
    return " ".join(parts).strip()


def synthesize(text, voice_preset=None):
    """텍스트를 MP3 바이트로 합성한다."""
    voice_name = VOICE_BY_PRESET.get(voice_preset, DEFAULT_VOICE)
    response = _tts_client().synthesize_speech(
        input=texttospeech.SynthesisInput(text=text),
        voice=texttospeech.VoiceSelectionParams(
            language_code=LANGUAGE, name=voice_name
        ),
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        ),
    )
    return response.audio_content


def synthesize_b64(text, voice_preset=None):
    """응답 JSON 에 실을 base64 문자열. 실패해도 훈련은 계속되도록 None 을 돌려준다.

    음성은 부가 기능이다 - 합성이 실패했다고 대화까지 막을 이유가 없다.
    프론트는 오디오가 없으면 텍스트만 표시하면 된다.
    """
    import base64

    if not text:
        return None
    try:
        return base64.b64encode(synthesize(text, voice_preset)).decode("ascii")
    except Exception as exc:
        logger.warning("tts 실패(%s) - 텍스트만 내보냅니다", type(exc).__name__)
        return None
