import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

export default function Recommendation() {
  const navigate = useNavigate();
  const [recommendData, setRecommendData] = useState(null);
  
  // 신규 추가: 안내 팝업 모달 상태
  const [showNoticeModal, setShowNoticeModal] = useState(false);

  useEffect(() => {
    // 1. 사용자 설문 답변 불러오기
    const saved = localStorage.getItem("userSurveyData");
    const survey = saved ? JSON.parse(saved) : {};
    const userName = survey.userName || "고객";

    // 2. 가중치 점수 계산 (전화 T01 우대)
    const scores = { T01: 2, T02: 0, T03: 0, T04: 0, T05: 0, T06: 0 };

    if (survey.age === "60대 이상") { scores.T01 += 8; scores.T05 += 4; }
    else if (survey.age === "50대") { scores.T01 += 6; scores.T05 += 3; }
    else if (survey.age === "30대" || survey.age === "40대") { scores.T01 += 4; scores.T06 += 4; }

    if (survey.activities?.includes("모바일 뱅킹")) { scores.T01 += 5; scores.T06 += 4; }
    if (survey.activities?.includes("온라인 쇼핑")) { scores.T03 += 3; }

    if (survey.concerns?.some(c => c.includes("범죄 연루"))) { scores.T01 += 12; }
    if (survey.concerns?.some(c => c.includes("앱 설치"))) { scores.T01 += 6; scores.T03 += 4; }
    if (survey.concerns?.some(c => c.includes("엄마, 나 핸드폰"))) { scores.T02 += 8; }
    if (survey.concerns?.some(c => c.includes("택배") || c.includes("링크"))) { scores.T03 += 6; }

    if (survey.habit?.includes("들어본다") || survey.habit?.includes("따른다")) { scores.T01 += 4; }

    // 최고 점수 훈련 추출
    let topType = "T01";
    let maxScore = -1;
    let totalScore = 0;

    Object.keys(scores).forEach((type) => {
      totalScore += scores[type];
      if (scores[type] > maxScore) {
        maxScore = scores[type];
        topType = type;
      }
    });

    const calculatedMatch = Math.min(98, Math.max(88, Math.round(80 + (maxScore / (totalScore || 1)) * 30)));

    // 6가지 훈련 데이터 매핑
    const trainingMap = {
      T01: {
        id: "T01",
        isVoice: true, // 전화 연동 여부
        title: "전화 기반 기관사칭 대응 훈련",
        channel: "📞 음성 통화 (Voice)",
        desc: "검찰·금융감독원을 사칭한 압박형 음성 통화에 대응하는 훈련입니다.",
        reasons: ["기관 사칭 음성 연락 우려", "모바일 금융 계좌 보안 필요", "긴급 상황에서의 판단력 훈련"]
      },
      T02: {
        id: "T02",
        isVoice: false,
        title: "메신저 피싱 (자녀·지인 사칭)",
        channel: "💬 메신저 (Messenger)",
        desc: "가족이나 지인을 사칭해 긴급 송금을 요구하는 메시지 대응 훈련입니다.",
        reasons: ["가족 사칭 메시지 취약", "메신저 자주 이용", "긴급 입금 요청 거절 훈련"]
      },
      T03: {
        id: "T03",
        isVoice: false,
        title: "택배·공공기관 스미싱 대응",
        channel: "📱 문자 URL (SMS)",
        desc: "출처가 불분명한 문자 링크(URL) 및 악성 앱 설치 요구 대응 훈련입니다.",
        reasons: ["온라인 쇼핑 이용", "문자 URL 클릭 우려", "악성 앱 설치 차단 훈련"]
      },
      T04: {
        id: "T04",
        isVoice: true, // 전화 연동
        title: "고수익 투자 리딩방 사기 훈련",
        channel: "📈 메신저/통화",
        desc: "원금 보장 및 고수익으로 현혹하는 투자 사기 대응 훈련입니다.",
        reasons: ["주식·코인 투자 관심", "고수익 제안 스미싱 노출", "투자 사기 예방 필요"]
      },
      T05: {
        id: "T05",
        isVoice: true, // 전화 연동
        title: "정부지원 대출 사기 대응",
        channel: "🏦 통화/문자",
        desc: "저금리 대출 전환을 미끼로 수수료를 요구하는 사기 대응 훈련입니다.",
        reasons: ["대출·금융상품 관심", "금융기관 사칭 우려", "수수료 요구 거절 연습"]
      },
      T06: {
        id: "T06",
        isVoice: false,
        title: "해외 이상결제 대응 훈련",
        channel: "💳 음성/문자",
        desc: "본인 미승인 결제 문자로 당황을 유도하는 이상거래 대응 훈련입니다.",
        reasons: ["카드·간편결제 이용", "해외 결제 문자 우려", "공식 기관 확인 습관 필요"]
      }
    };

    setRecommendData({
      userName,
      match: `${calculatedMatch}%`,
      ...trainingMap[topType]
    });
  }, []);

  // [이 체험 시작하기] 버튼 클릭 시 모달 오픈
  const handleStartTraining = () => {
    if (!recommendData) return;
    setShowNoticeModal(true);
  };

  // 모달 안에서 [확인하고 체험 시작] 클릭 시 실제 페이지 이동
  const handleConfirmStart = () => {
    setShowNoticeModal(false);
    localStorage.setItem("selectedScenario", JSON.stringify(recommendData));

    if (recommendData.isVoice) {
      navigate("/call-incoming");
    } else {
      navigate("/simulation");
    }
  };

  if (!recommendData) return null;

  return (
    <div className="min-h-[100dvh] bg-[#F8F9FA] flex justify-center items-center font-['Gothic_A1'] antialiased py-0 sm:py-6">
      <div className="w-full max-w-[393px] h-[100dvh] sm:h-auto sm:min-h-[780px] bg-white shadow-xl flex flex-col justify-between p-6 relative overflow-y-auto">
        
        <div>
          {/* Top Header */}
          <header className="flex justify-between items-center pt-2 pb-4 mb-2">
            <button 
              onClick={() => navigate("/survey")}
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

          {/* Sub Title */}
          <div className="mb-4">
            <span className="text-[11px] font-bold text-[#0052CC] bg-blue-50 px-2.5 py-1 rounded-md">
              AI 분석 완료
            </span>
            <h2 className="text-[20px] font-extrabold text-[#191F28] leading-[1.3] mt-2 tracking-tight">
              {recommendData.userName}님에게<br />가장 필요한 훈련이에요.
            </h2>
          </div>

          {/* 메인 추천 카드 */}
          <div className="bg-gradient-to-br from-blue-50 to-indigo-50/50 border-2 border-[#0052CC] rounded-2xl p-5 mb-5 shadow-xs">
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs font-bold text-[#0052CC]">
                {recommendData.channel}
              </span>
              <span className="text-xs bg-[#0052CC] text-white px-2 py-0.5 rounded-full font-bold">
                적합도 {recommendData.match}
              </span>
            </div>

            <h3 className="text-base font-extrabold text-[#191F28] mb-1.5">
              {recommendData.title}
            </h3>
            <p className="text-xs text-gray-600 leading-relaxed mb-4">
              {recommendData.desc}
            </p>

            {/* 추천 이유 */}
            <div className="bg-white/80 rounded-xl p-3 border border-blue-100">
              <span className="text-[11px] font-bold text-[#191F28] block mb-1.5">
                💡 왜 이 훈련을 추천했나요?
              </span>
              <ul className="space-y-1">
                {recommendData.reasons.map((reason, idx) => (
                  <li key={idx} className="text-[11px] text-gray-600 flex items-center space-x-1.5">
                    <span className="text-[#0052CC] font-bold">✓</span>
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        {/* Bottom Actions */}
        <div className="pt-2 space-y-2">
          <button
            onClick={handleStartTraining}
            className="w-full bg-[#0052CC] text-white py-3.5 rounded-xl text-xs sm:text-sm font-bold shadow-md shadow-blue-500/20 hover:bg-blue-700 transition active:scale-[0.99]"
          >
            이 체험 시작하기 →
          </button>
          
          <div className="grid grid-cols-2 gap-2 pt-1">
            <button
              onClick={() => navigate("/survey")}
              className="w-full bg-[#F8F9FA] border border-gray-200 text-[#191F28] py-2.5 rounded-xl text-xs font-semibold hover:bg-gray-100 transition"
            >
              🔄 설문 다시하기
            </button>
            <button
              onClick={() => navigate("/category-select")}
              className="w-full bg-[#F8F9FA] border border-gray-200 text-[#191F28] py-2.5 rounded-xl text-xs font-semibold hover:bg-gray-100 transition"
            >
              🎯 직접 선택하기
            </button>
          </div>
        </div>

        {/* 신규 추가: 실전 훈련 안내 모달 팝업 */}
        {showNoticeModal && (
          <div className="absolute inset-0 bg-black/60 backdrop-blur-xs flex justify-center items-center p-5 z-50 animate-fade-in">
            <div className="bg-white rounded-3xl p-6 text-center max-w-[320px] shadow-2xl border border-gray-100 space-y-4">
              <div className="w-12 h-12 bg-blue-50 text-[#0052CC] rounded-full flex items-center justify-center text-xl font-bold mx-auto">
                💡
              </div>
              
              <div>
                <h3 className="text-base font-extrabold text-[#191F28] mb-2">
                  실전 모의 훈련 안내
                </h3>
                <p className="text-xs text-gray-600 leading-relaxed break-keep">
                훈련에는 <b className="text-red-500">실제 사기 상황</b>뿐만 아니라,<br />
                <b className="text-[#0052CC]">정상적인 상황</b>도 함께 섞여 있어요.<br /><br />
                무조건 의심하기보다, 상황을 차분히 살펴보고<br />
                판단하는 연습이라고 생각해 주세요!
              </p>
              </div>

              <button
                onClick={handleConfirmStart}
                className="w-full bg-[#0052CC] text-white py-3.5 rounded-xl text-xs font-bold hover:bg-blue-700 transition shadow-md shadow-blue-500/20"
              >
                이해했습니다 (체험 시작) →
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}