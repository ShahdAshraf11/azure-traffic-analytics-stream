

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


#  CONFIG

DEFAULT_MODEL = "gemini-2.5-flash-lite"
DEFAULT_MAX_TOKENS = 220
DEFAULT_TEMPERATURE = 0.4
DEFAULT_CACHE_TTL_SECONDS = 240   # 4 min cache


#  PROMPT TEMPLATE
SYSTEM_PROMPT = """You are a traffic analyst writing brief, helpful insights for a Cairo traffic dashboard.

Your job: read a JSON snapshot of current traffic and write 2-3 sentences summarizing what's happening RIGHT NOW.

STRICT RULES:
1. Length: 2-3 sentences, max 60 words total.
2. Tone: professional, factual, useful. No fluff, no emojis, no marketing language.
3. Mention specific locations and numbers from the snapshot — don't be generic.
4. ONLY use facts from the JSON. Never invent locations, numbers, or weather not in the data.
5. If the city is mostly free-flowing, say so plainly.
6. If congestion is building up (negative trends), point it out.
7. Don't repeat the time/date — the dashboard already shows it.

STYLE EXAMPLES (note specificity and tight phrasing):

Snapshot: heavy congestion downtown, free flow elsewhere, no rain.
"Traffic is heavy in Downtown Cairo with Tahrir Square down to 11 km/h. Most other districts including Maadi and Heliopolis remain free-flowing. Conditions should ease after 6 PM rush."

Snapshot: severe traffic in Giza building up, light rain.
"Severe slowdowns are emerging on Giza routes — El Haram St dropped to 6 km/h with conditions worsening rapidly. Light rain may extend the disruption. Avoid Pyramids Road for the next hour."

Snapshot: city-wide free flow, mild weather.
"Cairo traffic is flowing well across all districts with city-wide average speed at 28 km/h. No active hotspots or weather concerns."

Now produce a summary for the snapshot below. Output ONLY the summary text — no preamble, no JSON wrapping, no quotes around the answer.
"""


#  HELPERS

def _hash_snapshot(snapshot: dict) -> str:
    """Stable hash of the snapshot for cache lookup."""
    s = json.dumps(snapshot, sort_keys=True, default=str)
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def _format_snapshot(snapshot: dict) -> str:
    """Render the snapshot as a clean JSON block for Gemini."""
    return json.dumps(snapshot, indent=2, default=str, ensure_ascii=False)


#  RESPONSE WRAPPER
@dataclass
class SummaryResult:
    """Wraps the model's response with metadata for the dashboard."""
    text: str                    # the summary itself
    cached: bool                 # was this from cache?
    elapsed_ms: int              # API latency
    tokens_in: int = 0           # input token usage
    tokens_out: int = 0          # output token usage
    error: Optional[str] = None  # set if generation failed

    def to_dict(self) -> dict:
        return {
            "text":        self.text,
            "cached":      self.cached,
            "elapsed_ms":  self.elapsed_ms,
            "tokens_in":   self.tokens_in,
            "tokens_out":  self.tokens_out,
            "error":       self.error,
        }


#  AI SUMMARY SERVICE (Gemini)
class AISummaryService:
    """Generates traffic summaries via Google Gemini API.

    Stateless except for the cache. Safe to call from any thread.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY not set. Pass api_key= or set the env var. "
                "Get a free key at https://aistudio.google.com/apikey"
            )
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.cache_ttl = cache_ttl_seconds

        # Lazy-import to allow this module to be imported in environments
        # without google-genai installed (e.g., during testing).
        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        except ImportError:
            raise RuntimeError(
                "Install the Gemini SDK first: pip install google-genai"
            )

        # In-memory cache: hash → (timestamp, SummaryResult)
        self._cache: dict[str, tuple[float, SummaryResult]] = {}

    # Public 
    def generate_summary(self, snapshot: dict) -> SummaryResult:
        """Generate a 2-3 sentence summary from the snapshot.

        Cached for 4 min by default — calling twice with the same data
        returns the cached result without hitting the API.
        """
        #  Cache lookup 
        key = _hash_snapshot(snapshot)
        now = time.time()
        if key in self._cache:
            ts, cached = self._cache[key]
            if now - ts < self.cache_ttl:
                logger.debug("Returning cached summary")
                cached.cached = True
                return cached

        #  Build the user message 
        user_message = (
            "Snapshot:\n```json\n"
            + _format_snapshot(snapshot)
            + "\n```"
        )

        #  Call Gemini 
        start = time.time()
        try:
            from google.genai import types

            response = self._client.models.generate_content(
                model=self.model,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    max_output_tokens=self.max_tokens,
                    temperature=self.temperature,
                ),
            )
            elapsed_ms = int((time.time() - start) * 1000)

            # Extract text content
            text = (response.text or "").strip()
            # Cleanup: occasionally model wraps in quotes — strip them
            text = text.strip('"').strip("'").strip()

            # Token usage
            tokens_in = 0
            tokens_out = 0
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                tokens_in = response.usage_metadata.prompt_token_count or 0
                tokens_out = response.usage_metadata.candidates_token_count or 0

            result = SummaryResult(
                text=text,
                cached=False,
                elapsed_ms=elapsed_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )

            # Cache it
            self._cache[key] = (now, result)
            self._prune_cache(now)
            return result

        except Exception as e:
            elapsed_ms = int((time.time() - start) * 1000)
            logger.error(f"Gemini API call failed: {e}")
            return SummaryResult(
                text="Traffic summary unavailable.",
                cached=False,
                elapsed_ms=elapsed_ms,
                error=str(e),
            )

    #  Internal 
    def _prune_cache(self, now: float) -> None:
        """Remove entries older than 2× TTL to bound memory."""
        threshold = now - 2 * self.cache_ttl
        stale = [k for k, (ts, _) in self._cache.items() if ts < threshold]
        for k in stale:
            del self._cache[k]


#  SNAPSHOT BUILDER (helper used by consumer to assemble snapshot)
def build_snapshot(
    current_records: list,
    n_hotspots: int = 4,
    n_free_flowing: int = 2,
) -> dict:
    """Assemble a Gemini-ready snapshot from a list of latest readings.

    Args:
        current_records: list of dicts, one per location, with at minimum:
            location_name, district, current_speed, congestion_level,
            congestion_ratio, speed_drop_pct, weather_main, rain_mm,
            temperature, request_time
            (optional) trend_30min: speed change over last 30 min

    Returns: snapshot dict ready to pass to AISummaryService.
    """
    if not current_records:
        return {
            "timestamp":      None,
            "city_avg_speed": None,
            "city_heavy_pct": 0.0,
            "city_severe_pct": 0.0,
            "top_hotspots":   [],
            "free_flowing":   [],
            "weather":        {},
            "anomaly_count":  0,
        }

    n = len(current_records)
    speeds = [r.get("current_speed", 0.0) for r in current_records
              if r.get("current_speed") is not None]
    avg_speed = sum(speeds) / max(len(speeds), 1)

    # Class counts
    heavy_count = sum(1 for r in current_records if r.get("congestion_level") == "Heavy")
    severe_count = sum(1 for r in current_records if r.get("congestion_level") == "Severe")
    closed_count = sum(1 for r in current_records if r.get("congestion_level") == "Closed")

    # Sort by congestion: Severe first, then by lowest ratio
    severity_rank = {"Severe": 0, "Closed": 1, "Heavy": 2, "Moderate": 3, "Free Flow": 4}
    sorted_recs = sorted(
        current_records,
        key=lambda r: (
            severity_rank.get(r.get("congestion_level", "Free Flow"), 5),
            r.get("congestion_ratio", 1.0),
        ),
    )

    hotspots = []
    for r in sorted_recs[:n_hotspots]:
        if r.get("congestion_level") in ("Severe", "Heavy", "Closed"):
            hotspots.append({
                "name":         r.get("location_name"),
                "district":     r.get("district"),
                "speed":        round(float(r.get("current_speed", 0)), 1),
                "class":        r.get("congestion_level"),
                "trend_30min":  round(float(r.get("trend_30min", 0)), 1)
                                  if r.get("trend_30min") is not None else None,
            })

    # Free-flowing: best ratios
    free_flowing_recs = sorted(
        current_records,
        key=lambda r: -r.get("congestion_ratio", 0),
    )
    free_flowing = []
    for r in free_flowing_recs[:n_free_flowing]:
        if r.get("congestion_level") == "Free Flow":
            free_flowing.append({
                "name":  r.get("location_name"),
                "speed": round(float(r.get("current_speed", 0)), 1),
                "class": r.get("congestion_level"),
            })

    # Weather (assume city-wide)
    first = current_records[0]
    weather = {
        "main":         first.get("weather_main", "Clear"),
        "rain_mm":      float(first.get("rain_mm", 0.0)),
        "temperature":  float(first.get("temperature", 0.0)),
    }

    # Anomalies
    anomaly_count = sum(1 for r in current_records if r.get("is_anomaly", 0) == 1)

    return {
        "timestamp":       first.get("request_time"),
        "city_avg_speed":  round(avg_speed, 1),
        "city_heavy_pct":  round(heavy_count / n * 100, 1),
        "city_severe_pct": round(severe_count / n * 100, 1),
        "city_closed_pct": round(closed_count / n * 100, 1),
        "n_locations":     n,
        "top_hotspots":    hotspots,
        "free_flowing":    free_flowing,
        "weather":         weather,
        "anomaly_count":   anomaly_count,
    }
