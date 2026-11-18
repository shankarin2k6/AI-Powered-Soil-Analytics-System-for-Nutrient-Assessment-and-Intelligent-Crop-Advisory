# Milestone 3 (part 1): crop suggestions and soil health trend

| Part | Where |
| --- | --- |
| Crop suitability ranking (pH, N/P/K demand, soil type) | `backend/app/services/crops.py`, rules in `backend/app/data/crops.json` |
| Added to every analysis as `result.crops` | `backend/app/api/analysis.py` |
| Soil health trend (direction + rough 90-day estimate) | `backend/app/services/trend.py`, `GET /api/v1/fields/{id}/trend` (`backend/app/api/trend.py`) |
| Screens | crops section in `AnalysisView.tsx`, chart in `TrendCard.tsx` (top of History) |
| Languages | `crops.*`, `crop.*`, `trend.*` keys in en/hi/kn/ta |

How the crop score works: 40% pH fit (full marks inside the crop's range, fading to zero 1.5 pH units outside), 35% nutrient fit
(N, P, K compared with the crop's low/medium/high demand), 25% soil type (well suited 1.0, fair 0.7, other 0.4; left out when the
soil type is unknown). 75+ very suitable, 55+ suitable, 40+ possible with care; the best 5 are shown.

The crop list, pH ranges, demands and weights in `crops.json` are PROVISIONAL. Confirm them with your mentor or a local agriculture
officer; only that file needs editing. The trend needs 3 analyses over 14 days or more and is a straight-line estimate.

Still to do in Milestone 3: PDF report, Sarvam voice, PWA install/offline, step-by-step fertiliser plan, deployment.
