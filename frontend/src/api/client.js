// src/api/client.js
//
// 모든 API 호출이 거쳐가는 공용 래퍼.
// - credentials: 'same-origin' 고정 (익명 세션 쿠키가 항상 같이 전송되게)
// - 쿠키에서 csrftoken을 읽어 변경 요청(POST 등)에 X-CSRFToken 헤더 자동 첨부
// - 에러 응답의 { error: { code, message } } 형태를 파싱해서 던짐

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

async function request(path, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };

  // GET 등 안전한 메서드가 아니면 CSRF 토큰 첨부
  if (method !== "GET") {
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) headers["X-CSRFToken"] = csrfToken;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    credentials: "same-origin",
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  const data = await res.json().catch(() => null);

  if (!res.ok) {
    const err = data?.error;
    throw new ApiError(err?.code || "UNKNOWN", err?.message || "요청 처리 중 문제가 발생했습니다.", err?.details);
  }

  return data;
}

export const apiGet = (path) => request(path, { method: "GET" });
export const apiPost = (path, body) => request(path, { method: "POST", body });
