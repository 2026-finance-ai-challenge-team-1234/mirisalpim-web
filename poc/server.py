"""로컬 전용 POC 서버 - 브라우저 마이크로 실제 음성 대화가 되는지 검증한다.

Django/React 앱과 무관한 별도 서버다(포트도 다르게 씀, 8765). 표준 라이브러리
http.server 만 쓰고 새 프레임워크를 추가하지 않았다 - 삭제해도 mirisalpim-web 의
다른 부분에 영향 없다.

턴 처리는 스트리밍이 아니라 전체 응답을 한 번에 합성해서 반환한다(POC 1차 목표는
"브라우저 마이크로 대화가 되는가" 확인 - 문장 단위 재생 지연까지 보려면 SSE +
청크 오디오가 필요한데, 그건 이 파이프라인이 기본적으로 동작한다는 게 확인된 뒤에
필요하면 추가한다).

사용법 (mirisalpim-web/ 에서, LLM_PROVIDER=gemini + GOOGLE_APPLICATION_CREDENTIALS 필요):
    python -m poc.server
    브라우저에서 http://localhost:8765 접속
"""

from __future__ import annotations

import base64
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.stdout.reconfigure(encoding="utf-8")

from ai_core.engine import Engine, load_scenario, start_session, step  # noqa: E402
from poc.stt import transcribe_webm  # noqa: E402
from poc.tts import synthesize  # noqa: E402

WEB_DIR = Path(__file__).resolve().parent / "web"
RESULTS_DIR = Path(__file__).resolve().parent / "results"

#: 단일 사용자 POC라 프로세스 전역 상태 하나로 충분하다.
_state: dict = {"engine": None, "session_dir": None, "log": None, "turn_no": 0}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        pass  # 기본 접속 로그를 끈다 - 콘솔이 지저분해지는 것만 막는다.

    def _send_json(self, obj: dict, status: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/":
            html = (WEB_DIR / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return

        if parsed.path == "/session":
            qs = parse_qs(parsed.query)
            scenario_id = qs.get("scenario", ["sc-02"])[0]
            scenario = load_scenario(scenario_id)
            engine = start_session(scenario)

            session_dir = RESULTS_DIR / time.strftime("session-%m%d-%H%M%S")
            session_dir.mkdir(parents=True, exist_ok=True)
            _state.update(
                engine=engine,
                session_dir=session_dir,
                log={"scenario_id": scenario_id, "turns": []},
                turn_no=0,
            )

            opening = engine.state.transcript[-1].text
            audio = synthesize(opening)
            self._send_json(
                {
                    "opening_text": opening,
                    "audio_b64": base64.b64encode(audio).decode("ascii"),
                }
            )
            return

        self.send_error(404)

    def _send_event(self, obj: dict) -> None:
        payload = json.dumps(obj, ensure_ascii=False)
        self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
        self.wfile.flush()

    def do_POST(self) -> None:
        if self.path != "/turn":
            self.send_error(404)
            return

        engine: Engine | None = _state["engine"]
        if engine is None:
            self._send_json({"error": "세션이 없습니다. 먼저 '세션 시작'을 누르세요."}, 400)
            return

        length = int(self.headers.get("Content-Length", 0))
        webm_bytes = self.rfile.read(length)

        turn_no = _state["turn_no"]
        session_dir: Path = _state["session_dir"]
        (session_dir / f"turn-{turn_no}-user.webm").write_bytes(webm_bytes)

        stt_started = time.monotonic()
        user_text = transcribe_webm(webm_bytes)
        stt_ms = int((time.monotonic() - stt_started) * 1000)

        if not user_text:
            self._send_json({"error": "인식된 발화가 없습니다. 다시 시도하세요."})
            return

        # 여기서부터는 SSE(Server-Sent Events) - 안전검사를 통과한 문장이 나올 때마다
        # 그 문장의 TTS 오디오를 즉시 이벤트로 흘려보낸다. gate.feed() 는 LLM 스트림을
        # 읽는 메인 스레드에서, downstream(=on_sentence)은 StreamingSafetyGate 의
        # 백그라운드 워커 스레드에서 호출된다 - 그래서 이 문장의 TTS 합성+전송이
        # 진행되는 동안에도 다음 문장의 LLM 토큰은 계속 받아지는 게(진짜 병행) 핵심이다.
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        self._send_event({"type": "user_text", "user_text": user_text, "stt_ms": stt_ms})

        sentence_timings: list[dict] = []

        def on_sentence(sentence: str) -> None:
            t0 = time.monotonic()
            audio = synthesize(sentence)
            sentence_timings.append(
                {"sentence": sentence, "tts_ms": int((time.monotonic() - t0) * 1000)}
            )
            self._send_event(
                {
                    "type": "sentence",
                    "text": sentence,
                    "audio_b64": base64.b64encode(audio).decode("ascii"),
                }
            )

        step_started = time.monotonic()
        outcome = step(engine, user_text, on_delta=on_sentence)
        step_ms = int((time.monotonic() - step_started) * 1000)

        record = {
            "turn_no": turn_no,
            "stt_ms": stt_ms,
            "user_text": user_text,
            "scammer_text": outcome.scammer_text,
            "scammer_latency_ms": outcome.latency_ms,
            "scammer_first_token_ms": outcome.first_token_ms,
            "step_ms": step_ms,
            "sentence_timings": sentence_timings,
            "stage_changed": outcome.stage_changed,
            "risky_actions": outcome.risky_actions,
            "resisted": outcome.resisted,
            "blocked": outcome.blocked,
            "safety_violations": outcome.safety_violations,
            "ended": outcome.ended,
            "end_reason": outcome.end_reason,
        }
        _state["log"]["turns"].append(record)
        (session_dir / "log.json").write_text(
            json.dumps(_state["log"], ensure_ascii=False, indent=2), encoding="utf-8"
        )
        _state["turn_no"] += 1

        self._send_event({"type": "done", **record})


def main() -> None:
    port = 8765
    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"POC 서버: http://localhost:{port}  (Ctrl+C 로 종료)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n중단됨.")


if __name__ == "__main__":
    main()
