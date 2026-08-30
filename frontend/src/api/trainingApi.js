// src/api/trainingApi.js
//
// P-04/P-05/P-06. 실제 훈련 진행 API.
//
// ⚠️ 여기는 recommendationApi/scenarioApi와 달리 목업 폴백을 두지 않음.
// 훈련 대화는 가짜 데이터로 대체하면 사용자가 "AI와 대화했다"고 착각하게 되므로,
// 실패는 화면에 그대로 드러내고 재시도하게 해야 함.

import { apiPost, apiPostRaw, newIdempotencyKey } from "./client";

// 훈련 시작. body 없음 — 어떤 유형을 고를지는 서버 세션에 이미 저장돼 있음
// (추천 트랙: POST /recommendations 시 저장 / 직접선택 트랙: POST /user-info 시 저장)
export function startTrainingSession() {
  return apiPost("/training-sessions", {});
}

// 대화 한 턴 (동기 방식). 응답을 통째로 받은 뒤 한 번에 표시함.
// idempotencyKey를 넘기면 네트워크 오류로 재시도해도 턴이 중복 진행되지 않음.
export function sendTurn(sessionId, text, idempotencyKey) {
  return apiPost(
    `/training-sessions/${sessionId}/turns`,
    { text },
    { idempotencyKey: idempotencyKey || newIdempotencyKey() }
  );
}

// 브라우저 MediaRecorder가 만든 webm/opus 원본을 그대로 보냄.
// 서버가 STT로 인식한 userText와 다음 상대방 발화/음성을 함께 반환함.
export function sendAudioTurn(sessionId, audioBlob, sampleRate = 48000, idempotencyKey) {
  const query = new URLSearchParams({ sampleRate: String(sampleRate) });
  return apiPostRaw(
    `/training-sessions/${sessionId}/turns/audio?${query}`,
    audioBlob,
    {
      contentType: audioBlob.type || "audio/webm",
      idempotencyKey: idempotencyKey || newIdempotencyKey(),
    },
  );
}

// 판단 제출 → 종료·채점·진단서 생성까지 한 번에 처리됨 (5~10초 소요)
export function submitJudgment(sessionId, isScamGuess) {
  return apiPost(`/training-sessions/${sessionId}/judgment`, { isScamGuess });
}
