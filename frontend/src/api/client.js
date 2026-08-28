// src/api/client.js
//
// 모든 API 호출이 거쳐가는 공용 래퍼.
// - credentials: 'same-origin' 고정 (익명 세션 쿠키가 항상 같이 전송되게)
// - 쿠키에서 csrftoken을 읽어 변경 요청(POST 등)에 X-CSRFToken 헤더 자동 첨부
// - 에러 응답의 { error: { code, message } } 형태를 파싱해서 던짐
// - Idempotency-Key 지원: 네트워크 오류로 재시도해도 서버에서 턴이 두 번 진행되지 않음
//   (백엔드가 5분간 첫 응답을 그대로 돌려줌)

const API_BASE = "/api/v1";

function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : null;
}

export class ApiError extends Error {
  constructor(code, message, details) {
    super(message);
    this.code = code;
    this.details = details;
  }
}

// 재시도해도 안전해야 하는 요청(대화 턴 등)에 붙일 키 생성용
export function newIdempotencyKey() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  // 구형 브라우저 대비 폴백
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

async function request(path, { method = "GET", body, idempotencyKey } = {}) {
  const headers = { "Content-Type": "application/json" };

  // GET 등 안전한 메서드가 아니면 CSRF 토큰 첨부
  if (method !== "GET") {
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) headers["X-CSRFToken"] = csrfToken;
  }

  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    credentials: "same-origin",
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  const data = await res.json().catch(() => null);

  if (!res.ok) {
    const err = data?.error;
    const apiError = new ApiError(
      err?.code || "UNKNOWN",
      err?.message || "요청 처리 중 문제가 발생했습니다.",
      err?.details
    );
    apiError.status = res.status;
    // 429(RATE_LIMITED) 응답에서 재시도 대기 시간 안내용
    apiError.retryAfter = res.headers.get("Retry-After");
    throw apiError;
  }

  return data;
}

export const apiGet = (path) => request(path, { method: "GET" });
export const apiPost = (path, body, options = {}) =>
  request(path, { method: "POST", body, ...options });
