// src/hooks/useTrainee.js
//
// 사용 예: const { trainee, setTrainee, traineePayload } = useTrainee();

import { useContext } from "react";
import { TraineeContext } from "../context/traineeContextValue";

export function useTrainee() {
  const ctx = useContext(TraineeContext);
  if (!ctx) throw new Error("useTrainee 는 TraineeProvider 안에서만 쓸 수 있습니다.");
  return ctx;
}