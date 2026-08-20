// src/api/recommendationApi.js
//
// P-02 추천 API 호출 헬퍼.
// 실제 백엔드가 아직 없거나 호출이 실패하면 자동으로 목업 데이터로 대체합니다.
// 백엔드가 준비되면 이 파일은 손댈 필요 없이 자동으로 실제 데이터를 씁니다.

import { apiPost } from "./client";

export async function fetchRecommendation(surveyAnswers) {
  try {
    return await apiPost("/recommendations", surveyAnswers);
  } catch (err) {
    console.warn("[recommendationApi] 백엔드 호출 실패, 목업 데이터로 대체합니다:", err.message);
    return mockRecommendation(surveyAnswers);
  }
}

// ────────────────────────────────────────────────────────────
// 백엔드 완성 전, 화면 흐름 확인용 목업.
// 실제 로직(recommendation_engine.py)과 완전히 동일하진 않지만,
// 최소한 "이 track이 오면 화면이 이렇게 뜬다"를 검증하는 용도로 충분함.
// ────────────────────────────────────────────────────────────
function mockRecommendation(answers) {
  const isVoiceLeaning = answers.concerns?.some((c) =>
    ["CONCERN_01", "CONCERN_02", "CONCERN_03", "CONCERN_09", "CONCERN_10", "CONCERN_11"].includes(c)
  );

  if (isVoiceLeaning || !answers.concerns?.length) {
    return {
      category: "voice",
      track: "T01-1",
      title: "전화 기반 기관사칭 대응 훈련",
      description: "검찰·금융감독원을 사칭한 압박형 음성 통화에 대응하는 훈련입니다.",
      reasons: ["(목업) 백엔드 연동 전 임시 데이터입니다.", "기관 사칭 음성 연락 우려"],
      suitability: "90",
    };
  }

  return {
    category: "smishing",
    track: "S03-1",
    title: "택배·배송 스미싱 대응 훈련",
    description: "택배 조회를 가장한 문자 속 악성 링크에 대응하는 훈련입니다.",
    reasons: ["(목업) 백엔드 연동 전 임시 데이터입니다.", "택배·배송 관련 우려"],
    suitability: "88",
  };
}
