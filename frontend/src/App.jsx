import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import TypeSelect from "./pages/TypeSelect"; // 신규 추가: 체험 모드 선택 (대화형 vs 피싱랩)
import ModeSelect from "./pages/ModeSelect";
import Survey from "./pages/Survey";
import SurveyLoading from "./pages/SurveyLoading";
import Recommendation from "./pages/Recommendation";
import CategorySelect from "./pages/CategorySelect";
import UserInfo from "./pages/UserInfo";
import CallIncoming from "./pages/CallIncoming";
import Simulation from "./pages/Simulation";
import Report from "./pages/Report";
import PhishingLab from "./pages/PhishingLab"; // 신규 추가: 피싱 사이트 정밀 분석 체험관

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* 공통 메인 홈 */}
        <Route path="/" element={<Home />} />

        {/* 1단계: 체험 방식 1차 선택 (실시간 AI 대화 훈련 vs 피싱 사이트 체험관) */}
        <Route path="/type-select" element={<TypeSelect />} />

        {/* 2단계 (대화 훈련 선택 시): 진입 방식 선택 (AI 맞춤 추천 vs 직접 선택) */}
        <Route path="/mode-select" element={<ModeSelect />} />

        {/* 트랙 A: AI 맞춤 추천 플로우 */}
        <Route path="/survey" element={<Survey />} />
        <Route path="/survey-loading" element={<SurveyLoading />} />
        <Route path="/recommendation" element={<Recommendation />} />

        {/* 트랙 B: 직접 선택 플로우 */}
        <Route path="/category-select" element={<CategorySelect />} />
        <Route path="/user-info" element={<UserInfo />} />

        {/* 트랙 A/B 공통 훈련 및 결과 리포트 플로우 */}
        <Route path="/call-incoming" element={<CallIncoming />} />
        <Route path="/simulation" element={<Simulation />} />
        <Route path="/report" element={<Report />} />

        {/* 독립 트랙: 피싱 사이트 정밀 분석 체험관 */}
        <Route path="/phishing-lab" element={<PhishingLab />} />
      </Routes>
    </BrowserRouter>
  );
}