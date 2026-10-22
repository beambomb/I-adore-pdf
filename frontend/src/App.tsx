import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import HomePage from "./pages/HomePage";
import MergePage from "./pages/MergePage";
import NotFoundPage from "./pages/NotFoundPage";
import SplitPage from "./pages/SplitPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="merge" element={<MergePage />} />
        <Route path="split" element={<SplitPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
