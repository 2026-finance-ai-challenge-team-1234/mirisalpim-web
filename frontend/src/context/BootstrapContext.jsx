// src/context/BootstrapContext.jsx
//
// P-01. 앱이 처음 켜질 때 딱 한 번 GET /api/v1/bootstrap을 호출한다.
// - 익명 세션 쿠키 / CSRF 쿠키는 브라우저가 응답 헤더 보고 알아서 저장함 (여기서 직접 다룰 필요 없음)
// - 응답의 features/limits는 Context로 앱 전체에 공유해서, 나중에 어느 화면에서든
//   "지금 voice 기능 켜져있나?" 같은 걸 바로 참조할 수 있게 함
//
// 백엔드가 아직 없어도 앱이 멈추지 않도록, 실패하면 기본값(전부 true)으로 대체하고 넘어감.

import { createContext, useContext, useEffect, useState } from "react";
import { apiGet } from "../api/client";

const DEFAULT_STATE = {
  ready: false,
  features: { voice: true, smishing: true, phishing: true },
  limits: { maxInputChars: 500 },
};

const BootstrapContext = createContext(DEFAULT_STATE);

export function BootstrapProvider({ children }) {
  const [state, setState] = useState(DEFAULT_STATE);

  useEffect(() => {
    let cancelled = false;

    apiGet("/bootstrap")
      .then((data) => {
        if (cancelled) return;
        setState({
          ready: true,
          features: data.features ?? DEFAULT_STATE.features,
          limits: data.limits ?? DEFAULT_STATE.limits,
        });
      })
      .catch((err) => {
        console.warn("[bootstrap] 초기화 호출 실패, 기본값으로 진행합니다:", err.message);
        if (!cancelled) setState((prev) => ({ ...prev, ready: true }));
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return <BootstrapContext.Provider value={state}>{children}</BootstrapContext.Provider>;
}

// 사용 예: const { features, limits } = useBootstrap();
export function useBootstrap() {
  return useContext(BootstrapContext);
}
