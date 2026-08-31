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

async function request(
  path,
  { method = "GET", body, rawBody, contentType = "application/json", idempotencyKey } = {},
) {
  // contentType이 null이면 Content-Type을 지정하지 않는다.
  // FormData는 브라우저가 boundary까지 포함해 직접 헤더를 만들어야 해서, 여기서 덮으면 전송이 깨진다.
  const headers = contentType ? { "Content-Type": contentType } : {};

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
    body: rawBody ?? (body ? JSON.stringify(body) : undefined),
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
export const apiPostRaw = (path, rawBody, options = {}) =>
  request(path, { method: "POST", rawBody, ...options });

function parseSseBlock(block) {
  let event = "message";
  const dataLines = [];

  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
  }

  if (!dataLines.length) return null;
  try {
    return { event, data: JSON.parse(dataLines.join("\n")) };
  } catch {
    throw new ApiError("INVALID_STREAM", "실시간 응답 형식이 올바르지 않습니다.");
  }
}

// EventSource는 POST 본문을 보낼 수 없으므로 fetch의 ReadableStream으로 SSE를 읽는다.
// ReadableStream을 지원하지 않는 브라우저도 응답 전체를 받은 뒤 같은 파서로 처리한다.
export async function apiPostRawSse(
  path,
  rawBody,
  { contentType = "application/octet-stream", idempotencyKey, signal, onEvent } = {},
) {
  // contentType이 null이면 Content-Type을 생략한다 (FormData 대응, request()와 동일한 이유).
  const headers = contentType
    ? { "Content-Type": contentType, Accept: "text/event-stream" }
    : { Accept: "text/event-stream" };
  const csrfToken = getCookie("csrftoken");
  if (csrfToken) headers["X-CSRFToken"] = csrfToken;
  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;

  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    credentials: "same-origin",
    headers,
    body: rawBody,
    signal,
  });

  if (!res.ok) {
    const payload = await res.json().catch(() => null);
    const err = payload?.error;
    const apiError = new ApiError(
      err?.code || "UNKNOWN",
      err?.message || "요청 처리 중 문제가 발생했습니다.",
      err?.details,
    );
    apiError.status = res.status;
    apiError.retryAfter = res.headers.get("Retry-After");
    throw apiError;
  }

  const emitBlocks = async (text, flush = false) => {
    let normalized = text.replace(/\r\n/g, "\n");
    const blocks = normalized.split("\n\n");
    const remainder = flush ? "" : blocks.pop();
    if (flush && blocks.at(-1) === "") blocks.pop();

    for (const block of blocks) {
      if (!block.trim()) continue;
      const parsed = parseSseBlock(block);
      if (parsed) await onEvent?.(parsed.event, parsed.data);
    }
    if (flush && remainder?.trim()) {
      const parsed = parseSseBlock(remainder);
      if (parsed) await onEvent?.(parsed.event, parsed.data);
    }
    return remainder || "";
  };

  if (!res.body?.getReader) {
    await emitBlocks(await res.text(), true);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      buffer = await emitBlocks(buffer);
    }
    buffer += decoder.decode();
    await emitBlocks(buffer, true);
  } catch (error) {
    await reader.cancel().catch(() => {});
    throw error;
  } finally {
    reader.releaseLock();
  }
}