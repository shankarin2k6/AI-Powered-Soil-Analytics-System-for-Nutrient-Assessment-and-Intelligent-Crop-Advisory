# Milestone 2 starting point

`soil_api.py` is the model API that already works (image tiers, Grad-CAM, crop and fertilizer
recommendations, 31 tests passed). It is NOT part of the Milestone 1 app and is not imported by it.

In Milestone 2 its code moves into `app/ml/` (loader, image, tabular) and a new router `app/api/analysis.py`
saves every result in the `analyses` table. See the main README, section "Milestone 2".
Until then it can still be run on its own for experiments:  `uvicorn ml_legacy.soil_api:app --port 8001`
(with the model files in `backend/models/`; it needs torch, torchvision, xgboost, scikit-learn and joblib).
