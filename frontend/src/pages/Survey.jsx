import { useState } from "react";
import { useNavigate } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import { useTrainee } from "../hooks/useTrainee";

const q1Options = [
  { code: "AGE_10", label: "10대" },
  { code: "AGE_20", label: "20대" },
  { code: "AGE_30", label: "30대" },
  { code: "AGE_40", label: "40대" },
  { code: "AGE_50", label: "50대" },
  { code: "AGE_60", label: "60대 이상" },
];

const q2Options = [
  { code: "ACT_MOBILE_BANKING", label: "모바일 뱅킹", icon: "📱" },
  { code: "ACT_ONLINE_SHOPPING", label: "온라인 쇼핑", icon: "🛍️" },
  { code: "ACT_SECONDHAND", label: "중고거래", icon: "🔄" },
  { code: "ACT_INVESTMENT", label: "주식·코인 투자", icon: "📈" },
  { code: "ACT_PAYMENT", label: "카드·간편결제", icon: "💳" },
  { code: "ACT_LOAN_INSURANCE", label: "대출·보험", icon: "🏦" },
  { code: "ACT_JOB", label: "구직·아르바이트", icon: "💼" },
  { code: "ACT_MESSENGER", label: "메신저로 지인 연락", icon: "💬" },
  { code: "ACT_NONE", label: "해당 없음", icon: "❓" },
];

const q3Options = [
  { code: "CONCERN_01", label: '📞 "고객님 계좌가 범죄에 연루되었습니다."' },
  { code: "CONCERN_02", label: '👨‍👩‍👧 "가족이 급하게 돈을 요청해요."' },
  { code: "CONCERN_03", label: '📱 "휴대폰이 고장났다며 다른 번호로 연락"' },
  { code: "CONCERN_04", label: '📦 "택배 배송에 문제가 있다는 연락"' },
  { code: "CONCERN_05", label: '💳 "해외에서 큰 금액이 결제됐다는 연락"' },
  { code: "CONCERN_06", label: '💼 "고수익 아르바이트 제안"' },
  { code: "CONCERN_07", label: '📈 "원금 보장·고수익 투자 제안"' },
  { code: "CONCERN_08", label: '🏦 "정부지원 대출 대상자로 선정됐다는 연락"' },
  { code: "CONCERN_09", label: '🔐 "보안 강화를 위해 앱 설치·화면공유를 요구"' },
  { code: "CONCERN_10", label: '🚨 "지금 처리 안 하면 계좌·서비스가 정지된다는 압박"' },
  { code: "CONCERN_11", label: '👮 "출석 요구·수사 협조 요청"' },
  { code: "CONCERN_12", label: '💌 "모바일 청첩장·부고 등 경조사 안내 문자"' },
  { code: "CONCERN_13", label: '🎁 "설문조사·경품 당첨 안내 문자"' },
  { code: "CONCERN_14", label: '💕 "SNS·메신저로 친해진 사람이 투자를 권유하거나 돈을 요청"' },
  { code: "CONCERN_15", label: '☎️ "통신요금 미납이나 서비스 이용료를 안내하는 전화"' },
  { code: "CONCERN_16", label: '🚔 "교통범칙금·과태료 또는 세금 환급을 안내하는 문자"' },
  { code: "CONCERN_17", label: '😊 "온라인에서 알게 된 사람이 호감을 표현하며 접근"' },
  { code: "CONCERN_18", label: "🤔 잘 모르겠어요" },
];

const q4Options = [
  { code: "HABIT_HANGUP", label: "📵 바로 끊는다" },
  { code: "HABIT_LISTEN", label: "👂 일단 상대방 이야기를 들어본다" },
  { code: "HABIT_VERIFY_PERSON", label: "🔎 상대방의 신원을 먼저 확인한다" },
  { code: "HABIT_ASK_FAMILY", label: "👨‍👩‍👧 가족이나 지인에게 물어본다" },
  { code: "HABIT_VERIFY_OFFICIAL", label: "📞 해당 기관 공식 번호로 직접 확인한다" },
  { code: "HABIT_ASK_DETAIL", label: "💬 상대방에게 자세한 내용을 다시 물어본다" },
  { code: "HABIT_FOLLOW", label: "👍 특별히 의심되지 않으면 일단 따른다" },
  { code: "HABIT_VARIABLE", label: "🤔 상황에 따라 다르다" },
];

export default function Survey() {
  const navigate = useNavigate();
  const { setTrainee } = useTrainee();
  const [step, setStep] = useState(1);

  const [answers, setAnswers] = useState({
    age: "",
    activities: [],
    concerns: [],
    habit: "",
    userName: "",
  });

  const toggleMultiSelect = (field, code) => {
    setAnswers((prev) => {
      const list = prev[field];
      if (list.includes(code)) {
        return { ...prev, [field]: list.filter((c) => c !== code) };
      } else {
        return { ...prev, [field]: [...list, code] };
      }
    });
  };

  const handleNext = () => {
    if (step < 5) {
      setStep(step + 1);
      return;
    }

    // 개인정보는 localStorage 대신 메모리(Context)에만 둔다.
    // 나이는 AGE_60 같은 코드라, 프롬프트에 쓸 사람이 읽는 문구로 바꿔서 넘긴다.
    const ageLabel = q1Options.find((opt) => opt.code === answers.age)?.label || "";
    setTrainee({ name: answers.userName, age: ageLabel, address: "" });

    navigate("/survey-loading", { state: { surveyAnswers: answers } });
  };

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
          <PageHeader onBack={handleBack} />

          <section className="mb-4">
            <h2 className="text-[20px] font-extrabold text-[#191F28] leading-[1.3] mb-1 break-keep">
              나에게 맞는 체험을<br />찾아볼게요.
            </h2>
            <p className="text-xs text-[#8B95A1] break-keep">
              몇 가지 질문에 답하면 지금 가장 필요한 훈련을 추천해드려요.
            </p>
          </section>

          <div className="inline-block bg-blue-50 text-[#0052CC] font-extrabold text-xs px-2.5 py-1 rounded-md mb-2">
            Q{step}
          </div>

          {step === 1 && (
            <div>
              <h3 className="text-sm font-bold text-[#191F28] mb-4">연령대를 알려주세요.</h3>
              <div className="grid grid-cols-2 gap-2.5">
                {q1Options.map((opt) => (
                  <button
                    key={opt.code}
                    onClick={() => setAnswers({ ...answers, age: opt.code })}
                    className={`py-3.5 rounded-xl text-xs font-bold transition border-2 ${
                      answers.age === opt.code
                        ? "bg-blue-50/50 border-[#0052CC] text-[#0052CC]"
                        : "bg-[#F8F9FA] border-transparent text-[#191F28] hover:border-gray-200"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 2 && (
            <div>
              <h3 className="text-sm font-bold text-[#191F28] mb-1">평소 어떤 활동을 자주 하시나요?</h3>
              <p className="text-[11px] text-[#8B95A1] mb-3">여러 개를 선택할 수 있어요.</p>
              <div className="grid grid-cols-2 gap-2">
                {q2Options.map((opt) => {
                  const isSelected = answers.activities.includes(opt.code);
                  return (
                    <button
                      key={opt.code}
                      onClick={() => toggleMultiSelect("activities", opt.code)}
                      className={`p-2.5 rounded-xl text-left text-xs font-semibold transition border-2 flex items-center space-x-1.5 ${
                        isSelected
                          ? "bg-blue-50/50 border-[#0052CC] text-[#0052CC]"
                          : "bg-[#F8F9FA] border-transparent text-[#191F28]"
                      }`}
                    >
                      <span>{opt.icon}</span>
                      <span className="truncate">{opt.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {step === 3 && (
            <div>
              <h3 className="text-sm font-bold text-[#191F28] mb-1">가장 당황스러울 것 같은 상황은?</h3>
              <p className="text-[11px] text-[#8B95A1] mb-3">여러 개를 선택할 수 있어요.</p>
              <div className="space-y-1.5 max-h-[320px] overflow-y-auto pr-1">
                {q3Options.map((opt) => {
                  const isSelected = answers.concerns.includes(opt.code);
                  return (
                    <button
                      key={opt.code}
                      onClick={() => toggleMultiSelect("concerns", opt.code)}
                      className={`w-full p-2.5 rounded-xl text-left text-[11px] font-medium transition border-2 break-keep ${
                        isSelected
                          ? "bg-blue-50/50 border-[#0052CC] text-[#0052CC] font-bold"
                          : "bg-[#F8F9FA] border-transparent text-[#191F28]"
                      }`}
                    >
                      {opt.label}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {step === 4 && (
            <div>
              <h3 className="text-sm font-bold text-[#191F28] mb-1">모르는 번호로 금융 연락이 오면 나는..</h3>
              <p className="text-[11px] text-[#8B95A1] mb-3">평소 나의 습관을 알려주세요.</p>
              <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1">
                {q4Options.map((opt) => (
                  <button
                    key={opt.code}
                    onClick={() => setAnswers({ ...answers, habit: opt.code })}
                    className={`w-full p-3 rounded-xl text-left text-xs font-semibold transition border-2 break-keep ${
                      answers.habit === opt.code
                        ? "bg-blue-50/50 border-[#0052CC] text-[#0052CC]"
                        : "bg-[#F8F9FA] border-transparent text-[#191F28]"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 5 && (
            <div>
              <h3 className="text-sm font-bold text-[#191F28] mb-1">마지막으로 이름을 알려주세요.</h3>
              <p className="text-[11px] text-[#8B95A1] mb-4">실제 체험 중 몰입도를 높이기 위해 사용됩니다.</p>

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