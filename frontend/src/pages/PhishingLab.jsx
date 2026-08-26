import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import PageHeader from "../components/PageHeader";

// ────────────────────────────────────────────────────────────
// 공용 소형 컴포넌트
// ────────────────────────────────────────────────────────────

function Marker({ id, label, isDanger, selected, onClick, className = "" }) {
  return (
    <button
      onClick={() => onClick(id)}
      className={`absolute -top-2 -right-2 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-extrabold border-2 z-10 shadow-sm transition-all shrink-0 ${
        selected
          ? isDanger
            ? "bg-red-500 border-red-500 text-white"
            : "bg-gray-400 border-gray-400 text-white"
          : "bg-white border-[#0052CC] text-[#0052CC] animate-pulse"
      } ${className}`}
    >
      {selected ? (isDanger ? "!" : "i") : label}
    </button>
  );
}

function InfoBox({ isDanger, children, onClose }) {
  return (
    <div
      className={`mt-2 rounded-xl p-3 border animate-fade-in flex items-start justify-between gap-2 ${
        isDanger ? "bg-red-50 border-red-200" : "bg-gray-50 border-gray-200"
      }`}
    >
      <div>
        <span className={`text-[11px] font-extrabold block mb-1 ${isDanger ? "text-red-600" : "text-gray-600"}`}>
          {isDanger ? "🚨 위험 포인트" : "ℹ️ 이 부분은 괜찮아요"}
        </span>
        <p className={`text-[11px] leading-relaxed break-keep ${isDanger ? "text-red-700" : "text-gray-600"}`}>
          {children}
        </p>
      </div>
      <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xs shrink-0 mt-0.5">
        ✕
      </button>
    </div>
  );
}

function StepBadge({ step, total }) {
  return (
    <span className="text-[10px] font-extrabold text-[#0052CC] bg-blue-50 px-2 py-0.5 rounded-md">
      STEP {step} / {total}
    </span>
  );
}

const QUIZ_MARKERS = {
  url: {
    label: 1,
    isDanger: true,
    text: "주소가 안전한 https가 아닌 http로 시작하고, 도메인도 공식 .or.kr이 아닌 낯선 주소(.co)입니다. 정상적인 금융·공공기관 사이트는 반드시 https와 공식 도메인을 사용합니다.",
  },
  typo: {
    label: 2,
    isDanger: true,
    text: '기관명에 오타("보혐")가 있습니다. 공식 기관은 이런 기본적인 오타를 내지 않으며, 피싱사이트는 이런 사소한 디테일에서 허점을 드러냅니다.',
  },
  badge: {
    label: 3,
    isDanger: false,
    text: '"공식 환급 안내" 같은 문구 자체는 정상 사이트에도 흔히 쓰입니다. 문구가 위험한 게 아니라, 실제로는 주소(URL)와 발신 경로로 사이트의 진위를 판단해야 합니다.',
  },
  urgency: {
    label: 4,
    isDanger: true,
    text: '"24시간 이내 미인증 시 정지"처럼 시간을 촉박하게 제한해서, 사용자가 차분히 생각할 틈 없이 서두르게 만드는 전형적인 압박 문구입니다.',
  },
  button: {
    label: 5,
    isDanger: false,
    text: "버튼의 디자인이나 문구 자체는 정상 사이트에도 흔히 있는 형태입니다. 버튼이 위험한 게 아니라, 버튼을 누르게 만드는 압박 문구(위쪽 배너)가 진짜 위험 신호입니다.",
  },
  footer: {
    label: 6,
    isDanger: true,
    text: '화면 맨 아래 아주 작은 회색 글씨로 "공식 사이트가 아닙니다"라는 문구를 숨겨놓았습니다. 법적 책임을 피하려는 수법으로, 사용자가 알아차리기 어렵게 설계됩니다.',
  },
};

const SUMMARY_ITEMS = [
  "URL이 https인지, 도메인이 공식 주소인지 항상 확인하기",
  '"지금 안 하면 정지된다" 같은 압박형 문구는 의심하기',
  "로그인 시 비밀번호가 ●●●로 정상적으로 가려지는지 확인하기",
  "예상치 못한 이벤트·캐시백으로 결제를 유도하면 의심하기",
  "인증번호(OTP)는 어떤 상황에서도 타인에게 알려주지 않기",
];

export default function PhishingLab() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const TOTAL_STEPS = 4;

  const [selected, setSelected] = useState([]);
  const foundDangerCount = selected.filter((id) => QUIZ_MARKERS[id].isDanger).length;

  const [loginId, setLoginId] = useState("hong1234");
  const [loginPw, setLoginPw] = useState("test8282!");
  const [loginSubmitted, setLoginSubmitted] = useState(false);

  const [paymentClicked, setPaymentClicked] = useState(false);

  const [otpValue, setOtpValue] = useState("");
  const [otpSubmitted, setOtpSubmitted] = useState(false);
  const [otpTimer, setOtpTimer] = useState(180);

  useEffect(() => {
    if (step !== 4 || otpSubmitted) return;
    if (otpTimer <= 0) return;
    const t = setTimeout(() => setOtpTimer((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [step, otpTimer, otpSubmitted]);

  const formatTimer = (sec) => {
    const m = String(Math.floor(sec / 60)).padStart(2, "0");
    const s = String(sec % 60).padStart(2, "0");
    return `${m}:${s}`;
  };

  const toggleMarker = (id) => {
    setSelected((prev) => (prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]));
  };

  const goBack = () => {
    if (step === 0) navigate("/type-select");
    else setStep((s) => s - 1);
  };

  const handleFinish = () => navigate("/mode-select");

  return (
    <div className="min-h-[100dvh] bg-[#F8F9FA] flex justify-center items-center font-['Gothic_A1'] antialiased py-0 sm:py-6">
      <div className="w-full max-w-[393px] h-[100dvh] sm:h-auto sm:min-h-[780px] bg-white shadow-xl sm:rounded-3xl border-0 sm:border border-gray-100 flex flex-col p-6 relative overflow-y-auto">

        <PageHeader
          onBack={goBack}
          padding="pt-1 pb-4 mb-2"
          rightContent={step > 0 ? <StepBadge step={step} total={TOTAL_STEPS} /> : null}
        />

        {step === 0 && (
          <div className="flex-1 flex flex-col">
            <span className="text-[11px] font-bold text-amber-700 bg-amber-100/70 px-2.5 py-1 rounded-md self-start">
              🌐 시나리오 체험관
            </span>
            <h2 className="text-[21px] font-extrabold text-[#191F28] leading-[1.3] mt-3 tracking-tight">
              피싱 사이트, 어디까지<br />알아챌 수 있을까요?
            </h2>
            <p className="text-xs text-[#8B95A1] mt-2 leading-relaxed break-keep">
              가상의 가짜 금융 사이트를 단계별로 체험하며, 실제 피싱 사이트에서 자주 쓰이는 4가지 수법을 직접 찾아봅니다.
            </p>

            <div className="bg-[#F8F9FA] border border-gray-100 rounded-2xl p-4 mt-6 space-y-3">
              {[
                ["🔍", "이상한 부분 찾기", "화면 곳곳에 붙은 번호 중, 진짜 위험한 부분만 골라보세요."],
                ["🔐", "로그인 정보 노출", "비밀번호가 그대로 보이는 로그인 화면을 체험합니다."],
                ["💳", "결제 유도 체험", "예상치 못한 결제 유도가 어떻게 이뤄지는지 확인합니다."],
                ["📵", "인증번호 탈취", "인증번호를 입력하면 어떤 일이 벌어지는지 체험합니다."],
              ].map(([icon, title, desc], idx) => (
                <div key={idx} className="flex items-start space-x-2.5">
                  <span className="text-base">{icon}</span>
                  <div>
                    <p className="text-xs font-bold text-[#191F28]">{title}</p>
                    <p className="text-[10px] text-gray-500 leading-snug break-keep">{desc}</p>
                  </div>
                </div>
              ))}
            </div>

            <p className="text-[10px] text-center text-[#8B95A1] mt-4">
              💡 실제 정보는 입력되지 않으며, 모든 과정은 가상의 훈련입니다.
            </p>

            <div className="mt-auto pt-6">
              <button
                onClick={() => setStep(1)}
                className="w-full bg-[#0052CC] text-white py-3.5 rounded-xl text-sm font-bold shadow-md shadow-blue-500/20 hover:bg-blue-700 transition active:scale-[0.99]"
              >
                체험 시작하기 →
              </button>
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="flex-1 flex flex-col">
            <h2 className="text-base font-extrabold text-[#191F28] mb-1">화면에서 위험한 부분을 찾아보세요</h2>
            <p className="text-[11px] text-[#8B95A1] mb-3">
              번호 중 <b className="text-[#0052CC]">진짜 위험한 곳</b>만 골라보세요 · 위험 신호 {foundDangerCount} / 4개 발견
              <br />
              <span className="text-gray-400">(다시 누르면 선택이 취소돼요)</span>
            </p>

            <div className="relative border border-gray-300 rounded-2xl overflow-hidden shadow-sm select-none">
              <div className="bg-gray-100 pl-3 pr-3 py-2 text-[11px] font-mono border-b flex items-center gap-1.5">
                <span className="text-gray-400 shrink-0">🔓</span>
                <span className="text-red-600 font-bold truncate flex-1">http://nhis-security-check.co/login</span>
                <button
                  onClick={() => toggleMarker("url")}
                  className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-extrabold border-2 shrink-0 shadow-sm transition-all ${
                    selected.includes("url")
                      ? "bg-red-500 border-red-500 text-white"
                      : "bg-white border-[#0052CC] text-[#0052CC] animate-pulse"
                  }`}
                >
                  {selected.includes("url") ? "!" : QUIZ_MARKERS.url.label}
                </button>
              </div>

              <div className="bg-white p-4">
                <div className="flex items-center justify-between mb-4 gap-2">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span className="text-sm font-extrabold text-green-700 truncate">국민건강보혐공단</span>
                    <button
                      onClick={() => toggleMarker("typo")}
                      className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-extrabold border-2 shrink-0 shadow-sm transition-all ${
                        selected.includes("typo")
                          ? "bg-red-500 border-red-500 text-white"
                          : "bg-white border-[#0052CC] text-[#0052CC] animate-pulse"
                      }`}
                    >
                      {selected.includes("typo") ? "!" : QUIZ_MARKERS.typo.label}
                    </button>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <span className="text-[10px] text-gray-400">공식 환급 안내</span>
                    <button
                      onClick={() => toggleMarker("badge")}
                      className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-extrabold border-2 shrink-0 shadow-sm transition-all ${
                        selected.includes("badge")
                          ? "bg-gray-400 border-gray-400 text-white"
                          : "bg-white border-[#0052CC] text-[#0052CC] animate-pulse"
                      }`}
                    >
                      {selected.includes("badge") ? "i" : QUIZ_MARKERS.badge.label}
                    </button>
                  </div>
                </div>

                <div className="relative bg-red-50 border border-red-200 rounded-lg p-2.5 pr-9 mb-3">
                  <p className="text-[11px] font-bold text-red-600 leading-snug break-keep">
                    ⚠️ 24시간 이내 미인증 시 계좌가 정지됩니다!
                  </p>
                  <Marker id="urgency" label={QUIZ_MARKERS.urgency.label} isDanger={QUIZ_MARKERS.urgency.isDanger} selected={selected.includes("urgency")} onClick={toggleMarker} />
                </div>

                <p className="text-[11px] text-gray-600 leading-relaxed break-keep mb-4">
                  회원님께 지급되지 않은 환급금이 확인되어, 본인 인증 절차를 안내드립니다. 아래 버튼을 눌러 즉시 인증을 완료해 주세요.
                </p>

                <div className="relative pr-1 mb-6">
                  <div className="w-full bg-[#0052CC] text-white text-center text-xs font-bold py-2.5 rounded-lg">
                    지금 즉시 인증하기
                  </div>
                  <Marker id="button" label={QUIZ_MARKERS.button.label} isDanger={QUIZ_MARKERS.button.isDanger} selected={selected.includes("button")} onClick={toggleMarker} className="!border-white" />
                </div>

                <div className="relative pr-8 inline-block max-w-full">
                  <p className="text-[8px] text-gray-300 leading-snug">
                    본 사이트는 국민건강보험공단의 공식 사이트가 아닙니다.
                  </p>
                  <Marker id="footer" label={QUIZ_MARKERS.footer.label} isDanger={QUIZ_MARKERS.footer.isDanger} selected={selected.includes("footer")} onClick={toggleMarker} />
                </div>
              </div>
            </div>

            {selected.map((id) => (
              <InfoBox key={id} isDanger={QUIZ_MARKERS[id].isDanger} onClose={() => toggleMarker(id)}>
                {QUIZ_MARKERS[id].text}
              </InfoBox>
            ))}

            <div className="mt-auto pt-4">
              <button
                disabled={foundDangerCount < 4}
                onClick={() => setStep(2)}
                className={`w-full py-3.5 rounded-xl text-sm font-bold transition ${
                  foundDangerCount < 4
                    ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                    : "bg-[#0052CC] text-white shadow-md shadow-blue-500/20 hover:bg-blue-700 active:scale-[0.99]"
                }`}
              >
                {foundDangerCount < 4 ? `위험 신호 ${4 - foundDangerCount}곳 더 찾아보세요` : "다음 단계로 →"}
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="flex-1 flex flex-col">
            <h2 className="text-base font-extrabold text-[#191F28] mb-1">아래 정보로 로그인해보세요</h2>
            <p className="text-[11px] text-[#8B95A1] mb-4 break-keep">
              체험용 계정입니다. 아이디와 비밀번호가 이미 입력되어 있어요.
            </p>

            <div className="border border-gray-200 rounded-2xl overflow-hidden shadow-sm">
              <div className="bg-gray-100 px-3 py-2 text-[11px] font-mono border-b flex items-center space-x-1.5">
                <span className="text-gray-400">🔓</span>
                <span className="text-red-600 font-bold truncate">http://nhis-security-check.co/login</span>
              </div>

              <div className="p-5">
                <p className="text-xs font-extrabold text-[#191F28] mb-4 text-center">국민건강보혐공단 통합 로그인</p>

                <div className="space-y-2.5">
                  <input
                    value={loginId}
                    onChange={(e) => setLoginId(e.target.value)}
                    className="w-full p-3 rounded-xl border border-gray-200 text-xs focus:border-[#0052CC] focus:outline-none"
                    placeholder="아이디"
                  />
                  <div>
                    <input
                      type="text"
                      value={loginPw}
                      onChange={(e) => setLoginPw(e.target.value)}
                      className="w-full p-3 rounded-xl border-2 border-red-300 text-xs focus:border-red-400 focus:outline-none tracking-wide"
                      placeholder="비밀번호"
                    />
                    <p className="text-[10px] text-red-500 font-bold mt-1.5 flex items-center space-x-1">
                      <span>⚠️</span>
                      <span>비밀번호가 ●●●로 가려지지 않고 그대로 보이고 있어요</span>
                    </p>
                  </div>
                </div>

                <button
                  onClick={() => setLoginSubmitted(true)}
                  className="w-full bg-[#0052CC] text-white py-3 rounded-xl text-xs font-bold mt-4 hover:bg-blue-700 transition"
                >
                  로그인하기
                </button>
              </div>
            </div>

            {loginSubmitted && (
              <InfoBox isDanger>
                정상적인 사이트라면 비밀번호 입력 칸은 항상 ●●●로 가려져야 합니다. 이 화면처럼 비밀번호가 그대로 노출되면, 옆에서 화면을 보거나 화면을 녹화하는 것만으로도 비밀번호가 그대로 유출될 수 있습니다.
              </InfoBox>
            )}

            <div className="mt-auto pt-4">
              <button
                disabled={!loginSubmitted}
                onClick={() => setStep(3)}
                className={`w-full py-3.5 rounded-xl text-sm font-bold transition ${
                  !loginSubmitted
                    ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                    : "bg-[#0052CC] text-white shadow-md shadow-blue-500/20 hover:bg-blue-700 active:scale-[0.99]"
                }`}
              >
                다음 단계로 →
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="flex-1 flex flex-col">
            <h2 className="text-base font-extrabold text-[#191F28] mb-1">로그인에 성공했습니다</h2>
            <p className="text-[11px] text-[#8B95A1] mb-4 break-keep">
              메인 화면에 떠 있는 배너를 눌러보세요.
            </p>

            <div className="border border-gray-200 rounded-2xl overflow-hidden shadow-sm bg-white">
              <div className="bg-gradient-to-br from-[#0052CC] to-blue-700 text-white p-4">
                <p className="text-[10px] opacity-80">홍길동님 환영합니다</p>
                <p className="text-lg font-extrabold mt-1">1,532,400원</p>
                <p className="text-[10px] opacity-70 mt-0.5">국민건강보혐 통합계좌</p>
              </div>

              <div className="grid grid-cols-4 text-center text-[10px] text-gray-500 py-3 border-b">
                <span>홈</span>
                <span>이체</span>
                <span>결제</span>
                <span>전체</span>
              </div>

              <div className="p-4">
                {!paymentClicked ? (
                  <button
                    onClick={() => setPaymentClicked(true)}
                    className="w-full bg-amber-50 border-2 border-amber-300 rounded-xl p-4 text-left animate-pulse hover:animate-none transition"
                  >
                    <span className="text-[10px] font-extrabold text-amber-700 bg-amber-100 px-2 py-0.5 rounded-md">
                      🎉 지금만
                    </span>
                    <p className="text-xs font-extrabold text-[#191F28] mt-2">
                      지금 결제하면 캐시백 3만원 즉시 지급!
                    </p>
                    <p className="text-[10px] text-gray-500 mt-1">눌러서 확인하기 →</p>
                  </button>
                ) : (
                  <div className="w-full bg-gray-50 border border-gray-200 rounded-xl p-4">
                    <p className="text-xs font-extrabold text-[#191F28]">캐시백 이벤트 결제 진행 중...</p>
                  </div>
                )}
              </div>
            </div>

            {paymentClicked && (
              <InfoBox isDanger>
                실제 피싱 사이트는 예상치 못한 이벤트나 캐시백을 미끼로 결제를 유도해, 사용자가 계획에 없던 행동을 하도록 만듭니다. 갑작스러운 혜택 제안은 항상 의심해야 합니다.
              </InfoBox>
            )}

            <div className="mt-auto pt-4">
              <button
                disabled={!paymentClicked}
                onClick={() => setStep(4)}
                className={`w-full py-3.5 rounded-xl text-sm font-bold transition ${
                  !paymentClicked
                    ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                    : "bg-[#0052CC] text-white shadow-md shadow-blue-500/20 hover:bg-blue-700 active:scale-[0.99]"
                }`}
              >
                다음 단계로 →
              </button>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="flex-1 flex flex-col">
            <h2 className="text-base font-extrabold text-[#191F28] mb-1">결제 인증이 필요합니다</h2>
            <p className="text-[11px] text-[#8B95A1] mb-4 break-keep">
              문자로 전송된 6자리 인증번호를 입력해 주세요. (아무 숫자나 입력해도 체험이 진행됩니다)
            </p>

            <div className="border border-gray-200 rounded-2xl overflow-hidden shadow-sm bg-white p-5 text-center">
              <div className="w-10 h-10 bg-blue-50 text-[#0052CC] rounded-full flex items-center justify-center mx-auto mb-3 font-bold text-sm">
                📲
              </div>
              <p className="text-xs font-extrabold text-[#191F28] mb-1">본인 결제 인증</p>
              <p className={`text-[11px] font-mono font-bold mb-4 ${otpTimer < 30 ? "text-red-500" : "text-gray-400"}`}>
                남은 시간 {formatTimer(otpTimer)}
              </p>

              <input
                type="text"
                inputMode="numeric"
                maxLength={6}
                value={otpValue}
                onChange={(e) => setOtpValue(e.target.value.replace(/[^0-9]/g, ""))}
                placeholder="인증번호 6자리"
                className="w-full p-3 rounded-xl border border-gray-200 text-center text-sm font-bold tracking-[0.4em] focus:border-[#0052CC] focus:outline-none"
              />

              <button
                onClick={() => setOtpSubmitted(true)}
                disabled={otpValue.length !== 6}
                className={`w-full py-3 rounded-xl text-xs font-bold mt-3 transition ${
                  otpValue.length !== 6
                    ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                    : "bg-[#0052CC] text-white hover:bg-blue-700"
                }`}
              >
                인증하기
              </button>
            </div>

            {otpSubmitted && (
              <div className="mt-2 bg-red-600 text-white rounded-2xl p-4 animate-fade-in">
                <span className="text-2xl block mb-1.5">🚨</span>
                <h4 className="text-sm font-extrabold mb-1.5">인증번호가 탈취되었습니다!</h4>
                <p className="text-[11px] leading-relaxed opacity-90 break-keep">
                  실제 상황이었다면 방금 입력한 인증번호가 피싱범에게 그대로 전송되어, 수 초 안에 결제나 계좌이체가 진행되었을 것입니다. 인증번호(OTP)는 어떤 상황에서도 타인에게 알려주면 안 됩니다.
                </p>
              </div>
            )}

            <div className="mt-auto pt-4">
              <button
                disabled={!otpSubmitted}
                onClick={() => setStep(5)}
                className={`w-full py-3.5 rounded-xl text-sm font-bold transition ${
                  !otpSubmitted
                    ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                    : "bg-[#0052CC] text-white shadow-md shadow-blue-500/20 hover:bg-blue-700 active:scale-[0.99]"
                }`}
              >
                결과 확인하기 →
              </button>
            </div>
          </div>
        )}

        {step === 5 && (
          <div className="flex-1 flex flex-col">
            <span className="text-[11px] font-bold text-[#0052CC] bg-blue-50 px-2.5 py-1 rounded-md self-start">
              체험 완료
            </span>
            <h2 className="text-[21px] font-extrabold text-[#191F28] leading-[1.3] mt-3 tracking-tight">
              오늘 4가지 위험 신호를<br />모두 찾아냈어요!
            </h2>
            <p className="text-xs text-[#8B95A1] mt-2 leading-relaxed break-keep">
              실제 피싱 사이트를 마주쳤을 때, 아래 체크리스트를 꼭 기억해 주세요.
            </p>

            <div className="bg-gradient-to-br from-blue-50/80 to-indigo-50/50 border border-blue-200/60 rounded-2xl p-4 mt-5">
              <ul className="space-y-2.5">
                {SUMMARY_ITEMS.map((item, idx) => (
                  <li key={idx} className="text-[11px] text-[#191F28] leading-relaxed flex items-start space-x-1.5 font-medium break-keep">
                    <span className="text-[#0052CC] font-bold">✓</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="mt-auto pt-6 space-y-2">
              <button
                onClick={handleFinish}
                className="w-full bg-[#0052CC] text-white py-3.5 rounded-xl text-sm font-bold shadow-md shadow-blue-500/20 hover:bg-blue-700 transition active:scale-[0.99]"
              >
                다른 훈련도 체험해보기 →
              </button>
              <button
                onClick={() => navigate("/")}
                className="w-full bg-[#F8F9FA] text-[#8B95A1] border border-gray-200 py-2.5 rounded-xl text-xs font-semibold hover:bg-gray-100 transition"
              >
                🏠 홈으로 돌아가기
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
