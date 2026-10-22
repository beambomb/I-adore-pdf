import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import CompressPage from "./pages/CompressPage";
import HomePage from "./pages/HomePage";
import ImageToPdfPage from "./pages/ImageToPdfPage";
import MergePage from "./pages/MergePage";
import NotFoundPage from "./pages/NotFoundPage";
import OcrPage from "./pages/OcrPage";
import ScanPage from "./pages/ScanPage";
import SplitPage from "./pages/SplitPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="merge" element={<MergePage />} />
        <Route path="split" element={<SplitPage />} />
        <Route path="image-to-pdf" element={<ImageToPdfPage />} />
        <Route path="compress" element={<CompressPage />} />
        <Route path="scan" element={<ScanPage />} />
        <Route path="ocr" element={<OcrPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
