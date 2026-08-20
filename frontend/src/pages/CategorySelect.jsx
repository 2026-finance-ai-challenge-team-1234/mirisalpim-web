import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchAllScenarios } from "../api/scenarioApi";

export default function CategorySelect() {
  const navigate = useNavigate();

  // 1. 선택 단계 관리 (1: 전화/문자 대분류, 2: 8대 중분류 선택, 3: 세부 소분류 시나리오 선택)
  const [step, setStep] = useState(1);

  // 2. 선택된 데이터 상태 관리
  const [mainCategory, setMainCategory] = useState(null); // 'voice' | 'smishing'
  const [selectedSubGroup, setSelectedSubGroup] = useState(null); // 중분류 ID (T01~T08, S01~S08)
  const [selectedTrack, setSelectedTrack] = useState(null); // 트랙(소분류) 객체 { id, name, code } — 예: id="T01-1"

  // 3. P-03-01: 서버에서 전체 시나리오 목록 불러오기 (실패 시 자동으로 기존 데이터 사용)
  const [scenarios, setScenarios] = useState(null); // { voice: [...], smishing: [...] }

  useEffect(() => {
    fetchAllScenarios().then(setScenarios);
  }, []);

  // [단계 1] 메인 카테고리(전화 vs 문자) 선택
  const handleSelectMain = (type) => {
    setMainCategory(type);
    setSelectedSubGroup(null);
    setSelectedTrack(null);
    setStep(2); // 둘 다 2단계(8대 중분류 선택)로 직행
  };

  // [단계 2] 8대 중분류 선택
  const handleSelectSubGroup = (groupId) => {
    setSelectedSubGroup(groupId);
    setSelectedTrack(null);
    setStep(3); // 3단계(세부 소분류 선택)로 이동
  };

  // [최종 제출] 다음 페이지(UserInfo)로 이동
  const handleStart = () => {
    if (!mainCategory || !selectedTrack) return;

    // ⚠️ "selectedScenario"는 Track A(추천) 플로우가 Simulation 시작 시 쓰는 별개의 키라 그대로 둠
    localStorage.removeItem("selectedScenario");
    localStorage.setItem("selectedCategory", mainCategory);
    localStorage.setItem("selectedTrackId", selectedTrack.id);       // 예: "T01-1"
    localStorage.setItem("selectedTrackName", selectedTrack.name);
    localStorage.setItem("selectedTrackCode", selectedTrack.code);

    // AI 대화 연동 시 필요한 페르소나 키값 매핑
    localStorage.setItem("selectedPersonaKey", `${selectedTrack.code}_persona.json`);

    navigate("/user-info");
  };

  // 상단 뒤로가기 핸들러
  const handleHeaderBack = () => {
    if (step === 3) {
      setStep(2);
      setSelectedTrack(null);
    } else if (step === 2) {
      setStep(1);
      setSelectedSubGroup(null);
      setMainCategory(null);
    } else {
      navigate("/mode-select");
    }
  };

  // 현재 활성화된 카테고리 목록 및 선택된 중분류 객체 (scenarios 로딩 전엔 빈 배열로 처리)
  const currentCategoryList = scenarios
    ? mainCategory === "voice"
      ? scenarios.voice
      : scenarios.smishing
    : [];
  const currentGroupObj = currentCategoryList.find((g) => g.id === selectedSubGroup);

  // 데이터 로딩 중에는 스피너만 보여줌 (거의 즉시 끝남 - 실패해도 목업으로 바로 대체되므로)
  if (!scenarios) {
    return (
      <div className="min-h-[100dvh] bg-[#F8F9FA] flex justify-center items-center font-['Gothic_A1'] antialiased">
        <div className="w-8 h-8 border-4 border-blue-100 border-t-[#0052CC] rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="min-h-[100dvh] bg-[#F8F9FA] flex justify-center items-center font-['Gothic_A1'] antialiased py-0 sm:py-6">
      <div className="w-full max-w-[393px] h-[100dvh] sm:h-auto sm:min-h-[780px] bg-white shadow-xl flex flex-col justify-between p-6 relative overflow-y-auto">

        <div>
          {/* Header */}
          <header className="flex justify-between items-center pt-2 pb-4 mb-2 border-b border-gray-100">
            <button
              onClick={handleHeaderBack}
              aria-label="뒤로가기"
              className="text-[#191F28] hover:opacity-70 transition p-1 -ml-1 flex items-center justify-center"
            >
              <svg className="w-5 h-5 fill-none stroke-current stroke-2" viewBox="0 0 24 24">
                <path d="M15 18l-6-6 6-6" />
              </svg>
            </button>
            <h1
              onClick={() => navigate("/")}
              className="text-lg font-extrabold text-[#0052CC] cursor-pointer tracking-tight"
            >
              미리살핌
            </h1>
            <button aria-label="알림" className="text-[#191F28] hover:opacity-70 transition p-1 -mr-1">
              <svg className="w-5 h-5 fill-none stroke-current stroke-2" viewBox="0 0 24 24">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0"/>
              </svg>
            </button>
          </header>

          {/* Title Section */}
          <section className="mb-4">
            <span className="text-[10px] font-bold text-[#0052CC] bg-blue-50 px-2 py-0.5 rounded-md">
              직접 선택 훈련 • STEP {step}/3
            </span>
            <h2 className="text-[20px] font-extrabold text-[#191F28] leading-[1.3] mt-2 mb-1 tracking-tight break-keep">
              {step === 1 && <>어떤 금융사기를<br />체험해볼까요?</>}
              {step === 2 && (
                mainCategory === "voice"
                  ? <>보이스피싱 중분류를<br />선택해 주세요.</>
                  : <>스미싱 중분류를<br />선택해 주세요.</>
              )}
              {step === 3 && <>상세 시나리오를<br />선택해 주세요.</>}
            </h2>
            <p className="text-xs text-[#8B95A1] leading-relaxed break-keep">
              {step === 1 && "체험하고 싶은 금융사기 채널(통화 또는 문자)을 선택하세요."}
              {step === 2 && (
                mainCategory === "voice"
                  ? "체험을 원하는 보이스피싱 핵심 수법을 골라주세요."
                  : "체험을 원하는 스미싱 주요 유형을 골라주세요."
              )}
              {step === 3 && "훈련받을 구체적인 상황을 직접 지정해 보세요."}
            </p>
          </section>

          {/* STEP 1: 전화(보이스피싱) vs 문자(스미싱) 대분류 선택 */}
          {step === 1 && (
            <div className="space-y-3.5 animate-fade-in">
              {/* 보이스피싱 카드 */}
              <div
                onClick={() => handleSelectMain("voice")}
                className={`p-4 rounded-2xl border-2 transition-all cursor-pointer ${
                  mainCategory === "voice"
                    ? "bg-blue-50/40 border-[#0052CC] shadow-xs"
                    : "bg-[#F8F9FA] border-transparent hover:border-gray-200"
                }`}
              >
                <div className="mb-2">
                  <span className="inline-block text-[10px] font-bold px-2 py-0.5 rounded-md bg-[#0052CC] text-white">
                    📞 실시간 음성 통화 대응
                  </span>
                </div>
                <h3 className="text-sm font-extrabold text-[#191F28] mb-1">
                  전화 사기 (보이스피싱)
                </h3>
                <p className="text-xs text-[#8B95A1] leading-relaxed mb-2 break-keep">
                  검찰·금융기관·가족을 사칭한 실시간 음성 압박 통화에 침착하게 대응해보는 훈련이에요.
                </p>
                <div className="text-[11px] font-semibold text-[#0052CC]">
                  8대 중분류 및 소분류 선택하기 →
                </div>
              </div>

              {/* 스미싱 카드 */}
              <div
                onClick={() => handleSelectMain("smishing")}
                className={`p-4 rounded-2xl border-2 transition-all cursor-pointer ${
                  mainCategory === "smishing"
                    ? "bg-blue-50/40 border-[#0052CC] shadow-xs"
                    : "bg-[#F8F9FA] border-transparent hover:border-gray-200"
                }`}
              >
                <div className="mb-2">
                  <span className="inline-block text-[10px] font-bold px-2 py-0.5 rounded-md bg-emerald-500 text-white">
                    💬 문자 속 악성 URL 대응
                  </span>
                </div>
                <h3 className="text-sm font-extrabold text-[#191F28] mb-1">
                  문자 사기 (스미싱)
                </h3>
                <p className="text-xs text-[#8B95A1] leading-relaxed mb-2 break-keep">
                  택배, 공공기관 알림, 청첩장 등 일상 문자 속 악성 링크와 가짜 페이지 유입에 대응하는 훈련이에요.
                </p>
                <div className="text-[11px] font-semibold text-[#0052CC]">
                  8대 중분류 및 소분류 선택하기 →
                </div>
              </div>
            </div>
          )}

          {/* STEP 2: 8대 중분류 선택 */}
          {step === 2 && (
            <div className="space-y-3 animate-fade-in max-h-[460px] overflow-y-auto pr-1">
              {currentCategoryList.map((cat) => (
                <div
                  key={cat.id}
                  onClick={() => handleSelectSubGroup(cat.id)}
                  className="p-3.5 rounded-2xl border-2 border-transparent bg-[#F8F9FA] hover:border-[#0052CC] hover:bg-blue-50/30 transition cursor-pointer"
                >
                  <div className="flex items-center justify-between mb-1">
                    <h3 className="text-xs sm:text-sm font-extrabold text-[#191F28]">
                      {cat.title}
                    </h3>
                    <span className="text-[10px] font-bold text-[#0052CC] bg-blue-50 px-2 py-0.5 rounded-md">
                      {cat.badge}
                    </span>
                  </div>
                  <p className="text-[11px] text-[#8B95A1] leading-relaxed break-keep">
                    {cat.desc}
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* STEP 3: 세부 소분류 시나리오 선택 */}
          {step === 3 && currentGroupObj && (
            <div className="space-y-2.5 animate-fade-in max-h-[460px] overflow-y-auto pr-1">
              <div className="bg-blue-50/60 p-3 rounded-xl border border-blue-100 mb-3">
                <span className="text-[10px] font-bold text-[#0052CC] block">선택된 중분류</span>
                <span className="text-xs font-extrabold text-[#191F28]">{currentGroupObj.title}</span>
              </div>

              {currentGroupObj.subItems.map((item) => {
                const isSelected = selectedTrack?.id === item.id;
                return (
                  <div
                    key={item.id}
                    onClick={() => setSelectedTrack(item)}
                    className={`p-3 rounded-xl border-2 transition-all cursor-pointer flex justify-between items-center ${
                      isSelected
                        ? "bg-blue-50/60 border-[#0052CC] shadow-2xs"
                        : "bg-[#F8F9FA] border-gray-100 hover:border-gray-200"
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <span className="text-[10px] font-bold text-gray-400 font-mono">
                        {item.id}
                      </span>
                      <span className="text-xs font-bold text-[#191F28]">
                        {item.name}
                      </span>
                    </div>
                    <span className={`text-xs shrink-0 ${isSelected ? "text-[#0052CC] font-extrabold" : "text-gray-300"}`}>
                      {isSelected ? "✓ 선택됨" : "선택"}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* 하단 실행 버튼 */}
        <div className="pt-4 border-t border-gray-100 bg-white">
          <button
            onClick={handleStart}
            disabled={
              (step === 1 && !mainCategory) ||
              (step === 2) ||
              (step === 3 && !selectedTrack)
            }
            className={`w-full py-3.5 rounded-xl text-xs sm:text-sm font-bold transition ${
              (step === 3 && selectedTrack)
                ? "bg-[#0052CC] text-white shadow-md shadow-blue-500/20 hover:bg-blue-700 active:scale-[0.99]"
                : "bg-gray-200 text-gray-400 cursor-not-allowed"
            }`}
          >
            {step === 1 && "금융사기 유형을 먼저 선택해 주세요"}
            {step === 2 && "위 중분류 목록 중 하나를 선택해 주세요"}
            {step === 3 && (selectedTrack ? `[${selectedTrack.name}] 훈련 시작하기 →` : "세부 시나리오를 선택해 주세요")}
          </button>
        </div>

      </div>
    </div>
  );
}
