import { createContext, useEffect, useState } from "react";
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

// 나중에 useBootstrap()이 필요해지면 별도 useBootstrap.js 파일로 분리한다.
