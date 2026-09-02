import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiPost } from "../api/client";
import PageHeader from "../components/PageHeader";
import { useTrainee } from "../hooks/useTrainee";

export default function UserInfo() {
  const navigate = useNavigate();
  const { setTrainee } = useTrainee();

  const [userName, setUserName] = useState("");
  const [age, setAge] = useState("");
  const [address, setAddress] = useState("");

  const [showNoticeModal, setShowNoticeModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleStartTraining = () => {
    if (!userName.trim()) return;
    setShowNoticeModal(true);
  };

  const handleConfirmStart = async () => {
    setSubmitting(true);

    try {
      await apiPost("/user-info", {
        name: userName.trim(),
        age: age.trim() || null,
        address: address.trim() || null,
        trackId: localStorage.getItem("selectedTrackId"),
        category: localStorage.getItem("selectedCategory"),
      });
    } catch (err) {
      console.warn("[UserInfo] 서버 저장 실패, 로컬 데이터로 계속 진행합니다:", err.message);
    }

    setSubmitting(false);
    setShowNoticeModal(false);

    // 개인정보는 저장하지 않고 메모리(Context)에만 담아 다음 화면으로 나른다.
    // 백엔드도 이 값을 DB 에 넣지 않고 프롬프트에만 쓴다 (backend/training/trainee.py).
    setTrainee({ name: userName.trim(), age: age.trim(), address: address.trim() });

    const selectedCategory = localStorage.getItem("selectedCategory");

    if (selectedCategory === "voice") {
      navigate("/call-incoming");
    } else {
      navigate("/simulation");
    }
  };

  return (
    <div className="min-h-[100dvh] bg-[#F8F9FA] flex justify-center items-center font-['Gothic_A1'] antialiased py-0 sm:py-6">
      <div className="w-full max-w-[393px] h-[100dvh] sm:h-auto sm:min-h-[780px] bg-white shadow-xl flex flex-col justify-between p-6 relative overflow-y-auto">

        <div>
          <PageHeader
            onBack={() => navigate("/category-select")}
            variant="title"
            label="기본 정보 입력"
          />

          <section className="mb-4">
            <h2 className="text-[20px] font-extrabold text-[#191F28] leading-[1.3] mb-3 tracking-tight break-keep">
              더 현실감 있는 훈련을 위해<br />기본 정보를 입력해주세요.
            </h2>

            <div className="bg-blue-50/60 border border-blue-100 rounded-xl p-3.5 mb-5">
              <p className="text-xs text-[#0052CC] leading-relaxed font-semibold break-keep">
                입력하신 정보는 <b>저장되지 않고 대화 중에만 사용</b>됩니다.<br />
                <span className="text-[11px] font-normal text-gray-500">
                  (몰입도 높은 체험을 위해 실명 또는 닉네임을 권장드립니다.
                  나이·주소는 선택이며, 주소는 시·구까지만 사용됩니다.)
                </span>
              </p>
            </div>
          </section>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-[#191F28] mb-1.5">
                사용자 이름 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={userName}
                onChange={(e) => setUserName(e.target.value)}
                placeholder="실명 또는 닉네임"
                className="w-full p-3.5 rounded-xl border border-gray-200 bg-[#F8F9FA] text-xs font-medium text-[#191F28] placeholder-gray-400 focus:bg-white focus:border-[#0052CC] focus:outline-none transition"
              />
            </div>

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
                disabled={submitting}
                className="w-full bg-[#0052CC] text-white py-3.5 rounded-xl text-xs font-bold hover:bg-blue-700 transition shadow-md shadow-blue-500/20 disabled:opacity-60"
              >
                {submitting ? "저장하는 중..." : "이해했습니다 (체험 시작) →"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}