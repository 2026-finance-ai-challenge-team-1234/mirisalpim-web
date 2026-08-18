import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function UserInfo() {
  const navigate = useNavigate();

  // 입력 폼 상태 관리
  const [userName, setUserName] = useState("");
  const [age, setAge] = useState("");
  const [address, setAddress] = useState("");

  // 신규 추가: 안내 팝업 모달 상태
  const [showNoticeModal, setShowNoticeModal] = useState(false);

  // [맞춤 훈련 시작하기] 버튼 클릭 시 모달 오픈
  const handleStartTraining = () => {
    if (!userName.trim()) return;
    setShowNoticeModal(true);
  };

  // 모달 안에서 [확인하고 체험 시작] 클릭 시 실제 페이지 이동
  const handleConfirmStart = () => {
    setShowNoticeModal(false);

    const userInfo = {
      userName: userName.trim(),
      age: age.trim(),
      address: address.trim(),
    };
    localStorage.setItem("userSurveyData", JSON.stringify(userInfo));

    const selectedCategory = localStorage.getItem("selectedCategory");

    if (selectedCategory === "voice") {
      navigate("/call-incoming");
    } else {
      navigate("/simulation");
    }
  };

  return (
    <div className="min-h-[100dvh] bg-[#F8F9FA] flex justify-center items-center font-['Gothic_A1'] antialiased py-0 sm:py-6">
      {/* 모바일 컨테이너 프레임 - 100dvh & 스크롤 제로 핏 */}
      <div className="w-full max-w-[393px] h-[100dvh] sm:h-auto sm:min-h-[780px] bg-white shadow-xl flex flex-col justify-between p-6 relative overflow-y-auto">
        
        <div>
          {/* 1. Top Header */}
          <header className="flex justify-between items-center pt-2 pb-4 mb-2">
            <button 
              onClick={() => navigate("/category-select")}
              aria-label="뒤로가기"
              className="text-[#191F28] hover:opacity-70 transition p-1 -ml-1"
            >
              <svg className="w-5 h-5 fill-none stroke-current stroke-2" viewBox="0 0 24 24">
                <path d="M15 18l-6-6 6-6" />
              </svg>
            </button>
            <h1 className="text-sm font-bold text-[#191F28]">
              기본 정보 입력
            </h1>
            <button aria-label="알림" className="text-[#191F28] hover:opacity-70 transition">
              <svg className="w-5 h-5 fill-none stroke-current stroke-2" viewBox="0 0 24 24">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0"/>
              </svg>
            </button>
          </header>

          {/* 2. Form Title Area */}
          <section className="mb-4">
            <h2 className="text-[20px] font-extrabold text-[#191F28] leading-[1.3] mb-3 tracking-tight break-keep">
              더 현실감 있는 훈련을 위해<br />기본 정보를 입력해주세요.
            </h2>

            {/* 실명 권장 안내 박스 */}
            <div className="bg-blue-50/60 border border-blue-100 rounded-xl p-3.5 mb-5">
              <p className="text-xs text-[#0052CC] leading-relaxed font-semibold break-keep">
                AI 피싱범과의 대화 몰입도를 높이기 위해 사용자 이름은 실명 입력을 권장합니다.<br />
                <span className="text-[11px] font-normal text-gray-500">
                  (나이, 주소 등 기타 정보는 자유롭게 입력하셔도 됩니다.)
                </span>
              </p>
            </div>
          </section>

          {/* 3. Input Form Fields */}
          <div className="space-y-4">
            {/* Field 1: 사용자 이름 */}
            <div>
              <label className="block text-xs font-bold text-[#191F28] mb-1.5">
                사용자 이름 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={userName}
                onChange={(e) => setUserName(e.target.value)}
                placeholder="실제와 같은 체감을 위해 실명을 입력해주세요."
                className="w-full p-3.5 rounded-xl border border-gray-200 bg-[#F8F9FA] text-xs font-medium text-[#191F28] placeholder-gray-400 focus:bg-white focus:border-[#0052CC] focus:outline-none transition"
              />
            </div>

            {/* Field 2: 나이 */}
            <div>
              <label className="block text-xs font-bold text-[#191F28] mb-1.5">
                나이 (선택)
              </label>
              <input
                type="text"
                value={age}
                onChange={(e) => setAge(e.target.value)}
                placeholder="나이를 입력해주세요."
                className="w-full p-3.5 rounded-xl border border-gray-200 bg-[#F8F9FA] text-xs font-medium text-[#191F28] placeholder-gray-400 focus:bg-white focus:border-[#0052CC] focus:outline-none transition"
              />
            </div>

            {/* Field 3: 주소 */}
            <div>
              <label className="block text-xs font-bold text-[#191F28] mb-1.5">
                주소 (선택)
              </label>
              <input
                type="text"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="주소를 입력해주세요."
                className="w-full p-3.5 rounded-xl border border-gray-200 bg-[#F8F9FA] text-xs font-medium text-[#191F28] placeholder-gray-400 focus:bg-white focus:border-[#0052CC] focus:outline-none transition"
              />
            </div>
          </div>
        </div>

        {/* 4. Bottom Fixed CTA Area */}
        <div className="pt-4">
          <button
            onClick={handleStartTraining}
            disabled={!userName.trim()}
            className={`w-full py-3.5 rounded-xl text-xs sm:text-sm font-bold transition ${
              userName.trim()
                ? "bg-[#0052CC] text-white shadow-md shadow-blue-500/20 hover:bg-blue-700 active:scale-[0.99]"
                : "bg-gray-200 text-gray-400 cursor-not-allowed"
            }`}
          >
            맞춤 훈련 시작하기 →
          </button>
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