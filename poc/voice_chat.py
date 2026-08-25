"""POC - Chirp STT/TTS 로 실제 음성 대화가 되는지 검증한다.

프론트엔드·백엔드를 건드리지 않고, ai_core 만으로 마이크 입력 -> engine.step() ->
문장 단위 TTS 재생까지 전부 로컬에서 돈다. StreamingSafetyGate(on_delta)가 승인한
문장이 나오는 즉시 재생되는지(Controlled Streaming Cascade, idea-plan.md §7.5) 직접
확인하는 게 목적이다.

이 폴더(mirisalpim-web/poc/)는 검증용이며 실제 서비스 코드가 아니다 - 결과를
백엔드/프론트엔드 담당자와 공유한 뒤 폴더째 지워도 ai_core 는 영향 없다.

세션마다 poc/results/session-<시각>/ 에 턴별 로그(log.json)와 녹음 원본(turn-N-user.wav)을
남긴다 - 응답 지연시간·인식 결과·안전 필터 판정을 나중에 분석하거나, 녹음 자체를 들어보고
STT 인식 문제가 마이크 품질 때문인지 배경 소음 때문인지 구분할 수 있다.

사용법 (mirisalpim-web/ 에서, LLM_PROVIDER=gemini + GOOGLE_APPLICATION_CREDENTIALS 필요):
    python -m poc.voice_chat            # 기본 시나리오 sc-02
    python -m poc.voice_chat nm-01      # 다른 시나리오 지정
"""

from __future__ import annotations

import io
import json
import sys
import time
import wave
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import numpy as np  # noqa: E402
import sounddevice as sd  # noqa: E402

from ai_core.engine import load_scenario, start_session, step  # noqa: E402
from poc.stt import transcribe  # noqa: E402
from poc.tts import speak  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parent / "results"

#: 대부분의 마이크가 네이티브로 지원하는 표준 레이트. 장치의 "기본 샘플레이트"를
#: 자동 감지해 신뢰하면(sd.InputStream 의 samplerate 생략) Windows 일부 호스트
#: API(MME 등)에서 보고값과 실제 캡처 레이트가 어긋나 WAV 재생 시 음이 틀어지는
#: 문제가 있었다(2026-08-25 실측: 녹음이 "뭉개져서" 들리고 STT 도 엉뚱하게 나옴).
#: 명시적으로 48000 을 요청해 그 값 그대로 WAV 헤더에도 쓴다.
SAMPLE_RATE = 48000


def record_audio() -> tuple[bytes, int, int]:
    """[Enter] 로 녹음 시작, 다시 [Enter] 로 종료.

    Returns: (WAV LINEAR16 바이트, 녹음 시간 ms, 피크 진폭 0~32767)
    """
    device_info = sd.query_devices(kind="input")
    print(
        f"  입력 장치: {device_info['name']} "
        f"(장치 기본 {device_info['default_samplerate']:.0f}Hz, 녹음은 {SAMPLE_RATE}Hz 로 진행)"
    )

    input("\n[Enter] 눌러서 녹음 시작...")
    print("녹음 중... 다 말씀하셨으면 다시 [Enter] 를 누르세요.")

    frames: list[np.ndarray] = []

    def callback(indata, frame_count, time_info, status):
        if status:
            print(f"  (녹음 경고: {status})", file=sys.stderr)
        frames.append(indata.copy())

    started = time.monotonic()
    with sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype="int16", callback=callback
    ):
        input()
    record_ms = int((time.monotonic() - started) * 1000)
    samplerate = SAMPLE_RATE

    audio = np.concatenate(frames, axis=0) if frames else np.zeros((0, 1), dtype="int16")
    peak = int(np.abs(audio).max()) if audio.size else 0
    print(f"  (녹음 {record_ms}ms, {samplerate}Hz, 피크 레벨 {peak}/32767)")
    if peak < 1000:
        print("  ⚠️ 피크 레벨이 매우 낮습니다 - 마이크가 소리를 거의 못 잡은 것으로 보입니다.")

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        wf.writeframes(audio.tobytes())
    return buf.getvalue(), record_ms, peak


def main() -> None:
    scenario_id = sys.argv[1] if len(sys.argv) > 1 else "sc-02"
    scenario = load_scenario(scenario_id)
    engine = start_session(scenario)

    session_dir = RESULTS_DIR / time.strftime("session-%m%d-%H%M%S")
    session_dir.mkdir(parents=True, exist_ok=True)
    log_path = session_dir / "log.json"
    log: dict = {"scenario_id": scenario_id, "turns": []}

    opening = engine.state.transcript[-1].text
    print(f"\n[상대] {opening}")
    speak(opening)

    turn_no = 0
    while True:
        wav_bytes, record_ms, peak = record_audio()
        (session_dir / f"turn-{turn_no}-user.wav").write_bytes(wav_bytes)

        stt_started = time.monotonic()
        user_text = transcribe(wav_bytes)
        stt_ms = int((time.monotonic() - stt_started) * 1000)

        if not user_text:
            print("(인식된 발화가 없습니다 - 다시 시도하세요)")
            continue
        print(f"[훈련생 - 인식됨, STT {stt_ms}ms] {user_text}")

        outcome = step(engine, user_text, on_delta=speak)

        print(f"[상대 - 표시문, 지연 {outcome.latency_ms}ms 첫문장 {outcome.first_token_ms}ms] {outcome.scammer_text}")
        if outcome.blocked:
            print(f"  (안전 필터가 이 턴을 차단함: {outcome.safety_violations})")

        log["turns"].append(
            {
                "turn_no": turn_no,
                "record_ms": record_ms,
                "peak_amplitude": peak,
                "stt_ms": stt_ms,
                "user_text": user_text,
                "scammer_text": outcome.scammer_text,
                "scammer_latency_ms": outcome.latency_ms,
                "scammer_first_token_ms": outcome.first_token_ms,
                "stage_changed": outcome.stage_changed,
                "risky_actions": outcome.risky_actions,
                "resisted": outcome.resisted,
                "blocked": outcome.blocked,
                "safety_violations": outcome.safety_violations,
                "ended": outcome.ended,
                "end_reason": outcome.end_reason,
            }
        )
        log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
        turn_no += 1

        if outcome.ended:
            print(f"\n[종료] {outcome.end_reason}")
            break

    print(f"\n로그: {log_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n중단됨.")
