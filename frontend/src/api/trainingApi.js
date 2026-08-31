// src/api/trainingApi.js
//
// P-04/P-05/P-06. 실제 훈련 진행 API.
//
// ⚠️ 여기는 recommendationApi/scenarioApi와 달리 목업 폴백을 두지 않음.
// 훈련 대화는 가짜 데이터로 대체하면 사용자가 "AI와 대화했다"고 착각하게 되므로,
// 실패는 화면에 그대로 드러내고 재시도하게 해야 함.

import {
  ApiError,
  apiPost,
  apiPostRaw,
  apiPostRawSse,
  newIdempotencyKey,
} from "./client";

// 훈련 시작. body 없음 — 어떤 유형을 고를지는 서버 세션에 이미 저장돼 있음
// (추천 트랙: POST /recommendations 시 저장 / 직접선택 트랙: POST /user-info 시 저장)
export function startTrainingSession() {
  return apiPost("/training-sessions", {});
}

// 훈련생 정보(이름·나이·주소)는 매 턴 함께 보낸다. 서버는 저장하지 않고
// 사기꾼 프롬프트에만 쓴다 (backend/training/trainee.py).
// 값이 없으면 아예 넣지 않는다.
function withTrainee(body, trainee) {
  return trainee ? { ...body, trainee } : body;
}

// 오디오 턴에 훈련생 정보를 함께 보내려면 multipart 여야 한다.
// 쿼리 문자열로 보내면 이름이 웹서버·프록시 접근 로그에 남기 때문에 백엔드가 막아뒀다.
function buildAudioBody(audioBlob, trainee) {
  if (!trainee) {
    // 정보가 없으면 기존처럼 원본 바이트를 그대로 보낸다.
    return { body: audioBlob, contentType: audioBlob.type || "audio/webm" };
  }

  const form = new FormData();
  form.append("audio", audioBlob, "turn.webm");
  form.append("trainee", JSON.stringify(trainee));
  // contentType: null → 브라우저가 multipart boundary까지 직접 붙이게 둔다.
  return { body: form, contentType: null };
}

// 대화 한 턴 (동기 방식). 응답을 통째로 받은 뒤 한 번에 표시함.
// idempotencyKey를 넘기면 네트워크 오류로 재시도해도 턴이 중복 진행되지 않음.
// linkClicked: 화면에서 문자 속 링크를 눌러 보낸 턴이라는 표시.
// 표시용 문장과 분리해 보낸다 - 서버가 문장을 문자열로 대조하면 문구를 다듬는
// 순간 위험행동 기록이 조용히 끊긴다.
export function sendTurn(sessionId, text, idempotencyKey, trainee, linkClicked = false) {
  return apiPost(
    `/training-sessions/${sessionId}/turns`,
    withTrainee({ text, linkClicked }, trainee),
    { idempotencyKey: idempotencyKey || newIdempotencyKey() }
  );
}

// 브라우저 MediaRecorder가 만든 webm/opus 원본을 그대로 보냄.
// 서버가 STT로 인식한 userText와 다음 상대방 발화/음성을 함께 반환함.
export function sendAudioTurn(
  sessionId,
  audioBlob,
  sampleRate = 48000,
  idempotencyKey,
  trainee,
) {
  const query = new URLSearchParams({ sampleRate: String(sampleRate) });
  const { body, contentType } = buildAudioBody(audioBlob, trainee);
  return apiPostRaw(
    `/training-sessions/${sessionId}/turns/audio?${query}`,
    body,
    {
      contentType,
      idempotencyKey: idempotencyKey || newIdempotencyKey(),
    },
  );
}

// 음성 한 턴을 STT한 뒤 승인된 문장·TTS를 SSE로 받는다.
// 서버의 error 이벤트도 일반 API 오류와 같은 ApiError로 바꿔 화면 처리를 통일한다.
export function sendAudioTurnStream(
  sessionId,
  audioBlob,
  sampleRate = 48000,
  { idempotencyKey, signal, onEvent, trainee } = {},
) {
  const query = new URLSearchParams({ sampleRate: String(sampleRate) });
  const { body, contentType } = buildAudioBody(audioBlob, trainee);
  return apiPostRawSse(
    `/training-sessions/${sessionId}/turns/audio/stream?${query}`,
    body,
    {
      contentType,
      idempotencyKey: idempotencyKey || newIdempotencyKey(),
      signal,
      onEvent: async (event, data) => {
        if (event === "error") {
          throw new ApiError(
            data?.code || "AI_ERROR",
            data?.message || "응답 생성에 실패했습니다.",
          );
        }
        await onEvent?.(event, data);
      },
    },
  );
}

// 판단 제출 → 종료·채점·진단서 생성까지 한 번에 처리됨 (5~10초 소요)
export function submitJudgment(sessionId, isScamGuess) {
  return apiPost(`/training-sessions/${sessionId}/judgment`, { isScamGuess });
}