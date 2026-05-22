import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import Index from "./pages/Index";
import AnomalyFeed from "./pages/AnomalyFeed";
import AIExplanations from "./pages/AIExplanations";
import TrafficAnalytics from "./pages/TrafficAnalytics";
import SystemHealth from "./pages/SystemHealth";
import Reports from "./pages/Reports";
import PowerBI from "./pages/PowerBI";
import NotFound from "./pages/NotFound";
import Forecasts from "./pages/Forecasts";
import DataQuality from "./pages/DataQuality";
const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/anomalies" element={<AnomalyFeed />} />
          <Route path="/explanations" element={<AIExplanations />} />
          <Route path="/analytics" element={<TrafficAnalytics />} />
          <Route path="/health" element={<SystemHealth />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/powerbi" element={<PowerBI />} />
          <Route path="/forecasts" element={<Forecasts />} />
          <Route path="/data-quality" element={<DataQuality />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
