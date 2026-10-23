# Milestone 2: ML analysis engine (weeks 3 and 4)

| Requirement in the plan | Where it is |
| --- | --- |
| CNN (EfficientNet) for soil type | `backend/app/ml/image.py` (trained in the Kaggle notebook; 8 classes incl. `Not_Soil`) |
| Gradient-boosted model on structured soil data | `backend/app/ml/tabular.py` (XGBoost fertilizer model) + rule ratings in `backend/app/services/soil_health.py` |
| Fusion of image and structured predictions | `backend/app/api/analysis.py` steps 3 and 5 (decision-level fusion, see below) |
| Grad-CAM | `app/ml/image.py`, saved as a PNG per analysis, shown on `/analysis` |
| SHAP | `app/ml/tabular.py` (`_explain`, TreeSHAP per prediction), shown as "Why this suggestion?" |
| FastAPI: health score, deficiency diagnosis, degradation risk | `POST /api/v1/fields/{id}/analyze` |

## Run it

```bash
cd backend
python -m pip install -r requirements.txt     # adds torch, torchvision, xgboost, scikit-learn, pandas, matplotlib
# copy the files from your notebooks into backend/models/ :
#   soil_cnn_D_hard_negatives.pt   fert_model.joblib   inference_config.json
uvicorn app.main:app --reload
# check they loaded:  http://localhost:8000/api/v1/analysis/status
```

No database migration is needed (the `analyses` table already existed). If a model file is missing the server still
starts: that part of the analysis is skipped and the response says so (`analysis.models_unavailable`).
`pytest` runs 121 tests using small stand-in models, so it needs no real model files.

## API

| Method and path | Purpose |
| --- | --- |
| `POST /fields/{id}/analyze` | body (all optional): `image_id`, `soil_test_id`, `confirmed_soil_class`, `crop_type`, `growth_stage`, `season`. Empty body = newest photo + newest lab test. Saves a row in `analyses`. |
| `GET /fields/{id}/analyses`, `GET /analyses/{id}` | saved results |
| `GET /analyses/{id}/gradcam` | heat-map PNG |
| `GET /analysis/status` | which models are loaded; the crop / stage / season values the fertilizer model accepts |

Result JSON: `image` (tier, soil_class, candidates, top3), `lab.ratings`, `health` (score 0-100, grade),
`degradation` (index 0-100, level, drivers), `diagnosis` (deficiencies, pH issue), `fertilizer_signal`
(top-3 + SHAP features), `fusion`, `warnings`. All text is returned as message keys that resolve in `messages/en.json`.

## How the pieces combine

1. **Photo** -> CNN on the `normalized` image -> tier: `confident` (>= 0.60), `confirm` (0.40-0.60, farmer picks one of two),
   `retake`, `not_soil`. Grad-CAM is produced for every tier except `not_soil`.
2. **Lab values** -> rating tables (`app/data/ratings.json`) -> low / medium / high per nutrient, pH class, health score
   (weighted mean of per-parameter scores) and degradation index (pH stress, organic matter, NPK depletion, soil-type susceptibility).
3. **Fusion** (decision level): the photo's soil class is used only when confident or confirmed by the farmer; when the CNN is
   unsure, the lab pH is used to suggest which candidate fits (`lab_hint`); a lab pH far outside the usual range of the chosen
   soil raises `fusion.ph_soil_mismatch`; the soil class feeds the fertilizer model (via `soil_to_fertilizer_type`) and the
   degradation index; the fertilizer model's top-3 must cover a low nutrient for the diagnosis to show "also suggested by the model".
4. **Fertilizer model** runs only when crop, growth stage and season are given.

A single neural network over image + lab features is not possible here, because no dataset has photos and lab results of
the same samples. Say this in the report as a design decision, not a gap.

## Things to confirm before the final report

- **Rating thresholds** (`ratings.json`) are provisional ICAR-style cut-offs. Ask your mentor which ones the project should use; edit the file only.
- **Weights, grades and soil susceptibility values** in the same file are my starting values, not research results.
- `soil_to_fertilizer_type` (Black -> Clay, etc.) is unreviewed. Gravel soil still has no CNN class.
- The fertilizer dataset looks synthetic and SSP is unreliable (F1 about 0.15); the app labels it as a hint.
- Everything was tested with stand-in models. Run it once with your real files and a real phone photo.
