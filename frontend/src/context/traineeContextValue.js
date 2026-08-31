// src/context/traineeContextValue.js
//
// Context 객체와 기본값만 둔다 (컴포넌트도 훅도 아니라 Fast Refresh 규칙 대상이 아님).

import { createContext } from "react";

export const EMPTY_TRAINEE = { name: "", age: "", address: "" };

export const TraineeContext = createContext(null);