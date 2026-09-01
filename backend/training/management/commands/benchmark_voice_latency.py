"""고정 WebM/Opus 파일로 배포 음성 SSE 경로의 레이턴시를 반복 측정한다."""

from __future__ import annotations

import json
import statistics
import sys
import time
import uuid
from pathlib import Path

import httpx
from django.core.management.base import BaseCommand, CommandError

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass


def _elapsed_ms(started):
    return max(0, round((time.monotonic() - started) * 1000))


def _sse_events(lines):
    event = "message"
    data_lines = []
    for line in lines:
        if line == "":
            if data_lines:
                yield event, json.loads("\n".join(data_lines))
            event, data_lines = "message", []
            continue
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
    if data_lines:
        yield event, json.loads("\n".join(data_lines))


class Command(BaseCommand):
    help = (
        "고정 WebM/Opus 파일을 /turns/audio/stream 에 반복 전송해 "
        "클라이언트·서버 구간별 레이턴시를 측정합니다. 음성 원본과 대화문은 저장하지 않습니다."
    )

    def add_arguments(self, parser):
        parser.add_argument("--audio", required=True, help="로컬 WebM/Opus 파일")
        parser.add_argument("--base-url", default="http://127.0.0.1:8000")
        parser.add_argument("--track-id", default="T01-1")
        parser.add_argument("--iterations", type=int, default=5)
        parser.add_argument("--turns-per-session", type=int, default=5)
        parser.add_argument("--sample-rate", type=int, default=48000)
        parser.add_argument("--timeout", type=float, default=90.0)
        parser.add_argument(
            "--output",
            help="선택 JSON 결과 경로. 지정하지 않으면 요약만 출력합니다.",
        )

    def handle(self, *args, **options):
        audio_path = Path(options["audio"]).expanduser().resolve()
        if not audio_path.is_file():
            raise CommandError(f"음성 파일을 찾을 수 없습니다: {audio_path}")
        if options["iterations"] < 1 or options["turns_per_session"] < 1:
            raise CommandError("iterations와 turns-per-session은 1 이상이어야 합니다.")
        if audio_path.suffix.lower() not in {".webm", ".weba"}:
            self.stderr.write(
                self.style.WARNING("현재 STT 계약은 WebM/Opus입니다. 파일 형식을 확인하세요.")
            )

        audio = audio_path.read_bytes()
        base_url = options["base_url"].rstrip("/")
        timeout = httpx.Timeout(options["timeout"])
        records = []
        session_id = None
        turns_in_session = 0
        pending_session_start_ms = None

        try:
            with httpx.Client(
                base_url=base_url, timeout=timeout, follow_redirects=True
            ) as client:
                self._bootstrap(client)
                for index in range(1, options["iterations"] + 1):
                    if (
                        session_id is None
                        or turns_in_session >= options["turns_per_session"]
                    ):
                        session_id, pending_session_start_ms = self._start_session(
                            client, options["track_id"]
                        )
                        turns_in_session = 0

                    record, ended = self._measure_turn(
                        client,
                        session_id,
                        audio,
                        options["sample_rate"],
                    )
                    record["iteration"] = index
                    record["sessionStartMs"] = pending_session_start_ms
                    pending_session_start_ms = None
                    records.append(record)
                    turns_in_session += 1
                    self.stdout.write(self._line(record))
                    if ended:
                        session_id = None
        except BaseException:
            # 429·AI_TIMEOUT·네트워크 오류로 중간에 끊겨도 여기까지 끝난 턴은 남긴다.
            # 측정 도구가 측정치를 못 지키면 반복 실행의 의미가 없다.
            if records:
                self.stderr.write(
                    self.style.WARNING(
                        f"측정이 중단되었습니다 - 완료된 {len(records)}회분만 남깁니다."
                    )
                )
                try:
                    self._finalize_results(records, options["output"])
                except Exception:
                    # 저장 실패가 원래 예외를 덮어쓰면 중단 원인을 알 수 없게 된다.
                    self.stderr.write(
                        self.style.ERROR("부분 결과 저장에 실패했습니다.")
                    )
            raise

        self._finalize_results(records, options["output"])

    def _finalize_results(self, records, output):
        """요약 출력과 선택적 JSON 저장. records 가 비어 있어도 실패하지 않는다."""
        summary = self._summary(records)
        self.stdout.write("\n" + json.dumps(summary, ensure_ascii=False, indent=2))
        if records and not any(record.get("server") for record in records):
            self.stderr.write(
                self.style.WARNING(
                    "서버 timing 이벤트가 없습니다. 서버에 "
                    "VOICE_LATENCY_DIAGNOSTICS=True를 설정했는지 확인하세요."
                )
            )
        if not output:
            return

        path = Path(output).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {"summary": summary, "runs": records}, ensure_ascii=False, indent=2
            ),
            encoding="utf-8",
        )
        self.stdout.write(self.style.SUCCESS(f"결과 저장: {path}"))

    def _headers(self, client):
        """CSRF 토큰 + same-origin 표시.

        Django 는 https 요청에 Origin 도 Referer 도 없으면 CsrfViewMiddleware 가
        "Referer checking failed - no Referer." 로 403 을 낸다. 브라우저와 달리
        httpx 는 둘 다 자동으로 붙이지 않아서, 이게 없으면 배포(Railway HTTPS)
        측정이 첫 POST 부터 전부 막힌다.

        ⚠️ base_url 의 scheme·host·port 로만 만든다. 사용자가 넘긴 URL 의 path 나
        끝 슬래시가 섞이면 오리진이 어긋나 오히려 거부된다.
        """
        origin = f"{client.base_url.scheme}://{client.base_url.host}"
        if client.base_url.port:
            origin += f":{client.base_url.port}"

        headers = {"Origin": origin, "Referer": f"{origin}/"}
        csrf = client.cookies.get("csrftoken")
        if csrf:
            headers["X-CSRFToken"] = csrf
        return headers

    def _bootstrap(self, client):
        response = client.get("/api/v1/bootstrap")
        response.raise_for_status()

    def _start_session(self, client, track_id):
        headers = self._headers(client)
        selection = client.post(
            "/api/v1/user-info",
            json={"category": "voice", "trackId": track_id},
            headers=headers,
        )
        selection.raise_for_status()
        started = time.monotonic()
        response = client.post("/api/v1/training-sessions", json={}, headers=headers)
        elapsed = _elapsed_ms(started)
        response.raise_for_status()
        return response.json()["sessionId"], elapsed

    def _measure_turn(self, client, session_id, audio, sample_rate):
        started = time.monotonic()
        client_marks = {}
        server_timing = None
        ended = False
        headers = {
            **self._headers(client),
            "Accept": "text/event-stream",
            "Idempotency-Key": str(uuid.uuid4()),
        }
        path = (
            f"/api/v1/training-sessions/{session_id}/turns/audio/stream"
            f"?sampleRate={sample_rate}&timing=1"
        )
        with client.stream(
            "POST",
            path,
            headers=headers,
            files={"audio": ("benchmark.webm", audio, "audio/webm")},
        ) as response:
            client_marks["responseHeadersMs"] = _elapsed_ms(started)
            response.raise_for_status()
            for event, data in _sse_events(response.iter_lines()):
                now = _elapsed_ms(started)
                if event == "accepted":
                    client_marks.setdefault("acceptedMs", now)
                elif event == "delta":
                    client_marks.setdefault("firstDeltaMs", now)
                elif event == "audio":
                    client_marks.setdefault("firstAudioMs", now)
                elif event == "timing":
                    server_timing = data
                elif event == "done":
                    client_marks["doneMs"] = now
                    ended = bool(data.get("ended"))
                elif event == "error":
                    raise CommandError(
                        f"SSE 오류 {data.get('code')}: {data.get('message')}"
                    )
        return {"client": client_marks, "server": server_timing}, ended

    def _line(self, record):
        client = record["client"]
        server = record.get("server") or {}
        scenario = server.get("scenarioId", "timing-off")
        return (
            f"#{record['iteration']} {scenario} "
            f"accepted={client.get('acceptedMs', '-')}ms "
            f"delta={client.get('firstDeltaMs', '-')}ms "
            f"audio={client.get('firstAudioMs', '-')}ms "
            f"done={client.get('doneMs', '-')}ms"
        )

    def _summary(self, records):
        keys = ("acceptedMs", "firstDeltaMs", "firstAudioMs", "doneMs")
        summary = {"runs": len(records)}
        for key in keys:
            values = [r["client"][key] for r in records if key in r["client"]]
            if values:
                summary[key] = {
                    "min": min(values),
                    "p50": round(statistics.median(values)),
                    "max": max(values),
                }
        return summary
