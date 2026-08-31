// src/context/TraineeContext.jsx
//
// 훈련생이 입력한 이름·나이·주소를 화면 사이에서 나르기 위한 저장소.
//
// ⚠️ localStorage 를 쓰지 않는다. 새로고침하면 사라지는 게 정상이고, 그게 의도다.
// 백엔드도 이 값을 DB 에 저장하지 않고 사기꾼 프롬프트에만 쓴다 (backend/training/trainee.py).
// "개인정보 수집·저장 없음" 이 기획서의 방어 논리라, 프론트도 같은 원칙을 지킨다.
//
// ⚠️ 이 파일은 컴포넌트(TraineeProvider)만 export 한다 (Fast Refresh 규칙).
// Context 객체는 traineeContextValue.js, 훅은 hooks/useTrainee.js 로 분리돼 있다.
// (파일명을 traineeContext.js 로 두면 Windows 가 대소문자를 구분하지 않아
//  TraineeContext.jsx 와 충돌한다. 그래서 이름을 확실히 다르게 두었다.)

import { useCallback, useMemo, useState } from "react";
import { EMPTY_TRAINEE, TraineeContext } from "./traineeContextValue";

export function TraineeProvider({ children }) {
  const [trainee, setTraineeState] = useState(EMPTY_TRAINEE);

  const setTrainee = useCallback((next) => {
    setTraineeState({
      name: next?.name?.trim() || "",
      age: next?.age?.trim() || "",
      address: next?.address?.trim() || "",
    });
  }, []);

  const clearTrainee = useCallback(() => setTraineeState(EMPTY_TRAINEE), []);

  // 매 턴 요청에 그대로 실어 보낼 형태.
  // 값이 하나도 없으면 undefined 를 반환해서 빈 객체가 오가지 않게 한다.
  const traineePayload = useMemo(() => {
    const hasAny = trainee.name || trainee.age || trainee.address;
    return hasAny ? { ...trainee } : undefined;
  }, [trainee]);

  const value = useMemo(
    () => ({ trainee, setTrainee, clearTrainee, traineePayload }),
    [trainee, setTrainee, clearTrainee, traineePayload],
  );

  return <TraineeContext.Provider value={value}>{children}</TraineeContext.Provider>;
}