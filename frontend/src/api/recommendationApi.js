// src/api/recommendationApi.js
//
// P-02 추천 API 호출 헬퍼.
//
// 목업 폴백 정책:
// - 개발 환경(import.meta.env.DEV)에서만 목업으로 대체함. 운영 빌드에서는 에러를 그대로 던져서
//   백엔드 장애가 조용히 감춰지지 않게 함.
// - 목업으로 대체된 경우 결과에 __isMock: true 를 붙여, 화면에서 배지를 띄울 수 있게 함.

import { apiPost } from "./client";

export async function fetchRecommendation(surveyAnswers) {
  try {
    return await apiPost("/recommendations", surveyAnswers);
  } catch (err) {
    if (!import.meta.env.DEV) throw err; // 운영에서는 실패를 감추지 않음
    console.warn("[recommendationApi] 백엔드 호출 실패, 목업 데이터로 대체합니다:", err.message);
    return { ...mockRecommendation(surveyAnswers), __isMock: true };
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
