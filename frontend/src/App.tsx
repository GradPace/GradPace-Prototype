import { Route, Routes } from "react-router-dom";
import HomePage from "./pages/HomePage/HomePage";
{
  /* Routes is what nests <Route>s
   * Route maps URLs to components
   */
}
function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
    </Routes>
  );
}

export default App;
