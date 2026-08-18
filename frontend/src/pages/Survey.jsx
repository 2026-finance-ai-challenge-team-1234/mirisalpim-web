import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function Survey() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);

  const [answers, setAnswers] = useState({
    age: "",
    activities: [],
    concerns: [],
    habit: "",
    userName: "",
  });

  const q1Options = ["10대", "20대", "30대", "40대", "50대", "60대 이상"];

  const q2Options = [
    { label: "모바일 뱅킹", icon: "📱" },
    { label: "온라인 쇼핑", icon: "🛍️" },
    { label: "중고거래", icon: "🔄" },
    { label: "주식·코인 투자", icon: "📈" },
    { label: "카드·간편결제", icon: "💳" },
    { label: "대출·보험", icon: "🏦" },
    { label: "구직·아르바이트", icon: "💼" },
    { label: "메신저로 지인 연락", icon: "💬" },
    { label: "해당 없음", icon: "❓" },
  ];

  const q3Options = [
    '📞 "고객님 계좌가 범죄에 연루되었습니다."',
    '👨‍👩‍👧 "엄마, 나 핸드폰 고장났어. 급하게 돈 보내줘."',
    '📦 "배송지 오류로 택배가 반송될 예정입니다."',
    '💳 "해외에서 350만원이 결제되었습니다."',
    '💼 "고수익 알바인데 계좌만 빌려주시면 됩니다."',
    '📈 "지금 들어가면 원금 3배 보장합니다."',
    '🏦 "정부지원 대출 대상자로 선정되었습니다."',
    '📱 "본인 확인을 위해 이 앱을 설치해주세요."',
    '🚨 "지금 처리 안 하면 계좌 정지됩니다."',
    '💬 "아래 링크에서 배송 정보를 확인해주세요."',
    '🤔 잘 모르겠어요 (AI 추천 필요)',
  ];

  const q4Options = [
    "📵 바로 끊는다",
    "👂 일단 상대방 이야기를 들어본다",
    "🔎 상대방의 신원을 먼저 확인한다",
    "👨‍👩‍👧 가족이나 지인에게 물어본다",
    "📞 해당 기관 공식 번호로 직접 확인한다",
    "💬 상대방에게 자세한 내용을 다시 물어본다",
    "👍 특별히 의심되지 않으면 일단 따른다",
    "🤔 상황에 따라 다르다",
  ];

  const toggleMultiSelect = (field, item) => {
    setAnswers((prev) => {
      const list = prev[field];
      if (list.includes(item)) {
        return { ...prev, [field]: list.filter((i) => i !== item) };
      } else {
        return { ...prev, [field]: [...list, item] };
      }
    });
  };

  const handleNext = () => {
    if (step < 5) {
      setStep(step + 1);
    } else {
      localStorage.setItem("userSurveyData", JSON.stringify(answers));
      navigate("/survey-loading");
    }
  };

  // 뒤로가기 로직: Q1이면 ModeSelect로, Q2~Q5면 이전 Step으로 이동
  const handleBack = () => {
    if (step > 1) {
      setStep(step - 1);
    } else {
      navigate("/mode-select");
    }
  };

  return (
    <div className="min-h-[100dvh] bg-[#F8F9FA] flex justify-center items-center font-['Gothic_A1'] antialiased py-0 sm:py-6">
      <div className="w-full max-w-[393px] h-[100dvh] sm:h-auto sm:min-h-[780px] bg-white shadow-xl flex flex-col justify-between p-6 relative overflow-y-auto">
        
        <div>
          {/* Top Header */}
          <header className="flex justify-between items-center pt-2 pb-4 mb-2">
            <button 
              onClick={handleBack}
              aria-label="뒤로가기"
              className="text-[#191F28] hover:opacity-70 transition p-1 -ml-1"
            >
              <svg className="w-5 h-5 fill-none stroke-current stroke-2" viewBox="0 0 24 24">
                <path d="M15 18l-6-6 6-6" />
              </svg>
            </button>
            <h1 onClick={() => navigate("/")} className="text-lg font-extrabold text-[#0052CC] cursor-pointer">
              미리살핌
            </h1>
            <div className="w-5"></div>
          </header>

          {/* Title Area */}
          <section className="mb-4">
            <h2 className="text-[20px] font-extrabold text-[#191F28] leading-[1.3] mb-1 break-keep">
              나에게 맞는 체험을<br />찾아볼게요.
            </h2>
            <p className="text-xs text-[#8B95A1] break-keep">
              몇 가지 질문에 답하면 지금 가장 필요한 훈련을 추천해드려요.
            </p>
          </section>

          {/* Question Badge */}
          <div className="inline-block bg-blue-50 text-[#0052CC] font-extrabold text-xs px-2.5 py-1 rounded-md mb-2">
            Q{step}
          </div>

          {/* Q1: 연령대 */}
          {step === 1 && (
            <div>
              <h3 className="text-sm font-bold text-[#191F28] mb-4">
                연령대를 알려주세요.
              </h3>
              <div className="grid grid-cols-2 gap-2.5">
                {q1Options.map((age) => (
                  <button
                    key={age}
                    onClick={() => setAnswers({ ...answers, age })}
                    className={`py-3.5 rounded-xl text-xs font-bold transition border-2 ${
                      answers.age === age
                        ? "bg-blue-50/50 border-[#0052CC] text-[#0052CC]"
                        : "bg-[#F8F9FA] border-transparent text-[#191F28] hover:border-gray-200"
                    }`}
                  >
                    {age}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Q2: 금융/온라인 활동 */}
          {step === 2 && (
            <div>
              <h3 className="text-sm font-bold text-[#191F28] mb-1">
                평소 어떤 활동을 자주 하시나요?
              </h3>
              <p className="text-[11px] text-[#8B95A1] mb-3">여러 개를 선택할 수 있어요.</p>
              <div className="grid grid-cols-2 gap-2">
                {q2Options.map((item) => {
                  const isSelected = answers.activities.includes(item.label);
                  return (
                    <button
                      key={item.label}
                      onClick={() => toggleMultiSelect("activities", item.label)}
                      className={`p-2.5 rounded-xl text-left text-xs font-semibold transition border-2 flex items-center space-x-1.5 ${
                        isSelected
                          ? "bg-blue-50/50 border-[#0052CC] text-[#0052CC]"
                          : "bg-[#F8F9FA] border-transparent text-[#191F28]"
                      }`}
                    >
                      <span>{item.icon}</span>
                      <span className="truncate">{item.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Q3: 취약 상황 */}
          {step === 3 && (
            <div>
              <h3 className="text-sm font-bold text-[#191F28] mb-1">
                가장 당황스러울 것 같은 상황은?
              </h3>
              <p className="text-[11px] text-[#8B95A1] mb-3">여러 개를 선택할 수 있어요.</p>
              <div className="space-y-1.5 max-h-[320px] overflow-y-auto pr-1">
                {q3Options.map((item) => {
                  const isSelected = answers.concerns.includes(item);
                  return (
                    <button
                      key={item}
                      onClick={() => toggleMultiSelect("concerns", item)}
                      className={`w-full p-2.5 rounded-xl text-left text-[11px] font-medium transition border-2 break-keep ${
                        isSelected
                          ? "bg-blue-50/50 border-[#0052CC] text-[#0052CC] font-bold"
                          : "bg-[#F8F9FA] border-transparent text-[#191F28]"
                      }`}
                    >
                      {item}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Q4: 행동 성향 */}
          {step === 4 && (
            <div>
              <h3 className="text-sm font-bold text-[#191F28] mb-1">
                모르는 번호로 금융 연락이 오면 나는..
              </h3>
              <p className="text-[11px] text-[#8B95A1] mb-3">평소 나의 습관을 알려주세요.</p>
              <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1">
                {q4Options.map((item) => (
                  <button
                    key={item}
                    onClick={() => setAnswers({ ...answers, habit: item })}
                    className={`w-full p-3 rounded-xl text-left text-xs font-semibold transition border-2 break-keep ${
                      answers.habit === item
                        ? "bg-blue-50/50 border-[#0052CC] text-[#0052CC]"
                        : "bg-[#F8F9FA] border-transparent text-[#191F28]"
                    }`}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Q5: 이름 입력 */}
          {step === 5 && (
            <div>
              <h3 className="text-sm font-bold text-[#191F28] mb-1">
                마지막으로 이름을 알려주세요.
              </h3>
              <p className="text-[11px] text-[#8B95A1] mb-4">
                실제 체험 중 몰입도를 높이기 위해 사용됩니다.
              </p>
              
              <input
                type="text"
                placeholder="홍길동"
                value={answers.userName}
                onChange={(e) => setAnswers({ ...answers, userName: e.target.value })}
                className="w-full p-3.5 rounded-xl border-2 border-gray-200 focus:border-[#0052CC] focus:outline-none text-sm font-bold text-[#191F28] bg-[#F8F9FA] mb-2"
              />
              <p className="text-[10px] text-[#8B95A1]">
                입력하신 이름은 체험 중 호칭 및 결과 리포트에만 활용됩니다.
              </p>
            </div>
          )}

        </div>

        {/* Progress Bar & Bottom Button */}
        <div className="pt-3">
          <div className="flex items-center justify-between text-[10px] text-[#8B95A1] mb-1.5 font-bold">
            <span>진행률</span>
            <span>{step} / 5</span>
          </div>
          <div className="w-full h-1.5 bg-gray-100 rounded-full mb-4 overflow-hidden">
            <div 
              className="h-full bg-[#0052CC] transition-all duration-300"
              style={{ width: `${(step / 5) * 100}%` }}
            ></div>
          </div>

          <button
            onClick={handleNext}
            disabled={
              (step === 1 && !answers.age) ||
              (step === 4 && !answers.habit) ||
              (step === 5 && !answers.userName.trim())
            }
            className={`w-full py-3.5 rounded-xl text-xs sm:text-sm font-bold transition ${
              (step === 1 && !answers.age) ||
              (step === 4 && !answers.habit) ||
              (step === 5 && !answers.userName.trim())
                ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                : "bg-[#0052CC] text-white shadow-md shadow-blue-500/20 hover:bg-blue-700"
            }`}
          >
            {step === 5 ? "맞춤형 체험 추천받기 →" : "다음 질문으로"}
          </button>
        </div>

      </div>
    </div>
  );
}