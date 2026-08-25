"""Chirp 3: HD (Cloud Text-to-Speech) 음성 합성 + 즉시 재생. POC 전용.

음성 이름은 2026-08-20 기준 공식 문서에서 확인한 8종(남 4·여 4) 중 하나다.
CLAUDE.md 의 비협상 안전 제약(음성 클로닝 금지, 상용 TTS 공개 화자 프리셋만 사용)을
그대로 만족한다 - Chirp 3 HD 는 구글이 제공하는 공개 프리셋 음성이다.
"""

from __future__ import annotations

import io
from functools import lru_cache

import sounddevice as sd
import soundfile as sf
from google.cloud import texttospeech

LANGUAGE = "ko-KR"
#: 남성(Charon) - sc-02 페르소나(voice_preset: male_40s_formal)에 맞춘 기본값.
#: 필요하면 호출부에서 다른 이름(예: ko-KR-Chirp3-HD-Kore, 여성)으로 바꿔 쓴다.
DEFAULT_VOICE = "ko-KR-Chirp3-HD-Charon"


@lru_cache(maxsize=1)
def _client() -> texttospeech.TextToSpeechClient:
    return texttospeech.TextToSpeechClient()


def synthesize(text: str, voice_name: str = DEFAULT_VOICE) -> bytes:
    """텍스트를 WAV(LINEAR16) 오디오 바이트로 합성한다."""
    response = _client().synthesize_speech(
        input=texttospeech.SynthesisInput(text=text),
        voice=texttospeech.VoiceSelectionParams(
            language_code=LANGUAGE, name=voice_name
        ),
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16
        ),
    )
    return response.audio_content


def speak(text: str, voice_name: str = DEFAULT_VOICE) -> None:
    """텍스트를 합성해서 바로 재생한다.

    engine.step(on_delta=speak) 로 그대로 꽂는다 - StreamingSafetyGate 가 승인한
    문장이 나올 때마다 이 함수가 호출되므로, Controlled Streaming Cascade(idea-plan.md
    §7.5)가 실제로 "문장이 끝나는 대로 재생 시작"하는지 이 POC 로 직접 확인할 수 있다.
    """
    audio_bytes = synthesize(text, voice_name)
    data, samplerate = sf.read(io.BytesIO(audio_bytes))
    sd.play(data, samplerate)
    sd.wait()
