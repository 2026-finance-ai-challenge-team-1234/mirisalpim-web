import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchAllScenarios } from "../api/scenarioApi";
import PageHeader from "../components/PageHeader";

// 백엔드가 available: false로 주는 소분류는 아직 시나리오가 적재되지 않아 훈련 불가.
// (서버도 클라이언트를 믿지 않고 재검사해서, 시작하면 409 SCENARIO_NOT_AVAILABLE이 남)
// 백엔드 응답에 available이 아예 없는 옛 목업 데이터는 true로 간주함.
const isAvailable = (item) => item.available !== false;

export default function CategorySelect() {
  const navigate = useNavigate();

  const [step, setStep] = useState(1);
  const [mainCategory, setMainCategory] = useState(null);
  const [selectedSubGroup, setSelectedSubGroup] = useState(null);
  const [selectedTrack, setSelectedTrack] = useState(null);

  const [scenarios, setScenarios] = useState(null);

  useEffect(() => {
    fetchAllScenarios().then(setScenarios);
  }, []);

  const handleSelectMain = (type) => {
    setMainCategory(type);
    setSelectedSubGroup(null);
    setSelectedTrack(null);
    setStep(2);
  };

  const handleSelectSubGroup = (groupId) => {
    setSelectedSubGroup(groupId);
    setSelectedTrack(null);
    setStep(3);
  };

  const handleStart = () => {
    if (!mainCategory || !selectedTrack) return;

    localStorage.removeItem("selectedScenario");
    localStorage.setItem("selectedCategory", mainCategory);
    localStorage.setItem("selectedTrackId", selectedTrack.id);
    localStorage.setItem("selectedTrackName", selectedTrack.name);
    localStorage.setItem("selectedTrackCode", selectedTrack.code);
    localStorage.setItem("selectedPersonaKey", `${selectedTrack.code}_persona.json`);

    navigate("/user-info");
  };

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

  const currentCategoryList = scenarios
    ? mainCategory === "voice"
      ? scenarios.voice
      : scenarios.smishing
    : [];
  const currentGroupObj = currentCategoryList.find((g) => g.id === selectedSubGroup);

  // 중분류 안에 훈련 가능한 소분류가 몇 개인지 (0개면 들어가도 고를 게 없음)
  const availableCountOf = (cat) => (cat.subItems || []).filter(isAvailable).length;

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
          <PageHeader onBack={handleHeaderBack} bordered />

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

          {step === 1 && (
            <div className="space-y-3.5 animate-fade-in">
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

          {step === 2 && (
            <div className="space-y-3 animate-fade-in max-h-[460px] overflow-y-auto pr-1">
              {currentCategoryList.map((cat) => {
                const availableCount = availableCountOf(cat);
                const groupDisabled = availableCount === 0;

                return (
                  <div
                    key={cat.id}
                    onClick={() => !groupDisabled && handleSelectSubGroup(cat.id)}
                    className={`p-3.5 rounded-2xl border-2 transition ${
                      groupDisabled
                        ? "bg-gray-50 border-transparent opacity-50 cursor-not-allowed"
                        : "bg-[#F8F9FA] border-transparent hover:border-[#0052CC] hover:bg-blue-50/30 cursor-pointer"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1 gap-2">
                      <h3 className="text-xs sm:text-sm font-extrabold text-[#191F28]">
                        {cat.title}
                      </h3>
                      {groupDisabled ? (
                        <span className="text-[10px] font-bold text-gray-400 bg-gray-100 px-2 py-0.5 rounded-md shrink-0">
                          준비 중
                        </span>
                      ) : (
                        <span className="text-[10px] font-bold text-[#0052CC] bg-blue-50 px-2 py-0.5 rounded-md shrink-0">
                          {cat.badge}
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-[#8B95A1] leading-relaxed break-keep">
                      {cat.desc}
                    </p>
                    {!groupDisabled && (
                      <p className="text-[10px] text-[#0052CC] font-semibold mt-1.5">
                        체험 가능한 시나리오 {availableCount}개
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {step === 3 && currentGroupObj && (
            <div className="space-y-2.5 animate-fade-in max-h-[460px] overflow-y-auto pr-1">
              <div className="bg-blue-50/60 p-3 rounded-xl border border-blue-100 mb-3">
                <span className="text-[10px] font-bold text-[#0052CC] block">선택된 중분류</span>
                <span className="text-xs font-extrabold text-[#191F28]">{currentGroupObj.title}</span>
              </div>

              {currentGroupObj.subItems.map((item) => {
                const available = isAvailable(item);
                const isSelected = selectedTrack?.id === item.id;

                return (
                  <div
                    key={item.id}
                    onClick={() => available && setSelectedTrack(item)}
                    className={`p-3 rounded-xl border-2 transition-all flex justify-between items-center ${
                      !available
                        ? "bg-gray-50 border-gray-100 opacity-50 cursor-not-allowed"
                        : isSelected
                        ? "bg-blue-50/60 border-[#0052CC] shadow-2xs cursor-pointer"
                        : "bg-[#F8F9FA] border-gray-100 hover:border-gray-200 cursor-pointer"
                    }`}
                  >
                    <div className="flex items-center space-x-2 min-w-0">
                      <span className="text-[10px] font-bold text-gray-400 font-mono shrink-0">
                        {item.id}
                      </span>
                      <span className={`text-xs font-bold truncate ${available ? "text-[#191F28]" : "text-gray-400"}`}>
                        {item.name}
                      </span>
                    </div>
                    <span
                      className={`text-xs shrink-0 ml-2 ${
                        !available
                          ? "text-gray-400 font-semibold"
                          : isSelected
                          ? "text-[#0052CC] font-extrabold"
                          : "text-gray-300"
                      }`}
                    >
                      {!available ? "준비 중" : isSelected ? "✓ 선택됨" : "선택"}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

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
