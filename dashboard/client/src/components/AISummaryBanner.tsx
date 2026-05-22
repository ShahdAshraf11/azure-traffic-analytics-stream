import { Sparkles, Clock, RefreshCw } from "lucide-react";
import { useState, useEffect } from "react";

const API = "http://localhost:5000/api";

interface AISummary {
  generated_at: string;
  summary_text: string;
  tokens_in?: number;
  tokens_out?: number;
  elapsed_ms?: number;
  cached?: boolean;
  error?: string;
}

/**
 * AI Summary Banner
 * ─────────────────
 * Displays the most recent Gemini-generated traffic summary.
 * Auto-refreshes every 60 seconds (the AI service updates every 5 min,
 * but checking more often catches new ones quickly).
 *
 * Reads from: GET /api/ai-summary/latest
 */
export function AISummaryBanner() {
  const [summary, setSummary] = useState<AISummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSummary = () => {
      fetch(`${API}/ai-summary/latest`)
        .then((r) => r.json())
        .then((data) => {
          if (data && data.summary_text) {
            setSummary(data);
          }
          setLoading(false);
        })
        .catch(() => setLoading(false));
    };

    fetchSummary();
    const interval = setInterval(fetchSummary, 60_000); // every 1 min
    return () => clearInterval(interval);
  }, []);

  // ── Helpers ──
  const getRelativeTime = (timestamp: string) => {
    if (!timestamp) return "—";
    const generated = new Date(timestamp).getTime();
    const now = Date.now();
    const ageMinutes = Math.floor((now - generated) / 60_000);
    if (ageMinutes < 1) return "just now";
    if (ageMinutes < 60) return `${ageMinutes} min ago`;
    const ageHours = Math.floor(ageMinutes / 60);
    return `${ageHours}h ${ageMinutes % 60}m ago`;
  };

  // ── Loading state ──
  if (loading) {
    return (
      <div className="bg-gradient-to-r from-primary/5 via-primary/10 to-primary/5 border border-primary/20 rounded-lg p-4">
        <div className="flex items-center gap-2 text-muted-foreground">
          <RefreshCw className="w-4 h-4 animate-spin" />
          <span className="text-xs">Loading AI insights...</span>
        </div>
      </div>
    );
  }

  // ── Empty state — AI not yet generated or service down ──
  if (!summary) {
    return (
      <div className="bg-card border border-border rounded-lg p-4">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-muted-foreground" />
          <span className="text-xs text-muted-foreground font-medium tracking-wider">
            AI INSIGHTS
          </span>
        </div>
        <p className="text-xs text-muted-foreground mt-1.5">
          AI summary not available yet. Check that GEMINI_API_KEY is set
          and the consumer is running.
        </p>
      </div>
    );
  }

  // ── Normal state — show the AI summary ──
  return (
    <div className="bg-gradient-to-r from-primary/5 via-primary/10 to-primary/5 border border-primary/20 rounded-lg p-4 relative overflow-hidden">
      {/* Subtle shimmer effect on left edge */}
      <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-primary/40 via-primary to-primary/40" />

      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className="w-8 h-8 rounded-lg bg-primary/15 flex items-center justify-center shrink-0 mt-0.5">
          <Sparkles className="w-4 h-4 text-primary" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold tracking-wider text-primary">
              AI INSIGHTS
            </span>
            <span className="text-[10px] text-muted-foreground">·</span>
            <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
              <Clock className="w-2.5 h-2.5" />
              <span>{getRelativeTime(summary.generated_at)}</span>
            </div>
            <span className="text-[10px] text-muted-foreground">·</span>
            <span className="text-[10px] text-muted-foreground">
              Powered by Gemini
            </span>
          </div>
          <p className="text-sm text-foreground leading-relaxed">
            {summary.summary_text}
          </p>
        </div>
      </div>
    </div>
  );
}
