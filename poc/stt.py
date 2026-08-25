"""Chirp 2 (Cloud Speech-to-Text V2) 음성 인식. POC 전용.

리전은 us-central1 고정 - Chirp 2 가 GA 상태로 제공되는 리전 중 하나다
(2026-08-20 기준 공식 문서 확인: us-central1 / europe-west4 / asia-southeast1).
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from google.api_core.client_options import ClientOptions
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech

REGION = "us-central1"


@lru_cache(maxsize=1)
def _project_id() -> str:
    cred_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    data = json.loads(Path(cred_path).read_text(encoding="utf-8"))
    return data["project_id"]


@lru_cache(maxsize=1)
def _client() -> SpeechClient:
    return SpeechClient(
        client_options=ClientOptions(api_endpoint=f"{REGION}-speech.googleapis.com")
    )


def _recognize(config: cloud_speech.RecognitionConfig, content: bytes) -> str:
    request = cloud_speech.RecognizeRequest(
        recognizer=f"projects/{_project_id()}/locations/{REGION}/recognizers/_",
        config=config,
        content=content,
    )
    response = _client().recognize(request=request)
    texts = [r.alternatives[0].transcript for r in response.results if r.alternatives]
    return " ".join(texts).strip()


def transcribe(wav_bytes: bytes) -> str:
    """WAV(LINEAR16) 오디오를 한국어 텍스트로 변환한다. 인식 결과 없으면 빈 문자열.

    poc/voice_chat.py(데스크톱 마이크 버전)가 쓴다.
    """
    config = cloud_speech.RecognitionConfig(
        auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
        language_codes=["ko-KR"],
        model="chirp_2",
    )
    return _recognize(config, wav_bytes)


def transcribe_webm(webm_bytes: bytes, sample_rate_hertz: int = 48000) -> str:
    """브라우저 MediaRecorder 가 만드는 webm/opus 오디오를 한국어 텍스트로 변환한다.

    poc/server.py(브라우저 마이크 버전)가 쓴다 - 실제 배포 경로(브라우저 getUserMedia)와
    가장 가까운 캡처 방식이다.
    """
    config = cloud_speech.RecognitionConfig(
        explicit_decoding_config=cloud_speech.ExplicitDecodingConfig(
            encoding=cloud_speech.ExplicitDecodingConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=sample_rate_hertz,
            audio_channel_count=1,
        ),
        language_codes=["ko-KR"],
        model="chirp_2",
    )
    return _recognize(config, webm_bytes)
