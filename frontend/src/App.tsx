import { Route, Routes } from "react-router-dom";
import HomePage from "./pages/HomePage/HomePage";
import LoginPage from "./pages/LoginPage/LoginPage";
import SignupPage from "./pages/SignupPage/SignupPage";
import ProfileSetupPage from "./pages/ProfileSetupPage/ProfileSetupPage";
import ProfilePage from "./pages/ProfilePage/ProfilePage";
import HowItWorksPage from "./pages/HowItWorksPage/HowItWorksPage";
import FeaturesPage from "./pages/FeaturesPage/FeaturesPage";
import Feedback from "./pages/Feedback/Feedback";

{
  /* Routes is what nests <Route>s
   * Route maps URLs to components
   */
}
function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/profileSetup" element={<ProfileSetupPage />} />
      <Route path="/profile" element={<ProfilePage />} />
      <Route path="/how-it-works" element={<HowItWorksPage />} />
      <Route path="/features" element={<FeaturesPage />} />
      <Route path="/feedback" element={<Feedback />} />
    </Routes>
  );
}

export default App;
