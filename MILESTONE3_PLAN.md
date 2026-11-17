# Step-by-step fertiliser plan

Shown on the analysis page under the result (needs lab values). The farmer picks the crop, where the crop is now and the field size.
The page then lists **what to buy** and **each step: when, what, how much and how to apply**.

## How the amounts are made (backend/app/services/plan.py)
1. Standard dose per crop in kg of N, P2O5, K2O per hectare (`backend/app/data/fertilizer_plans.json`, 20 crops).
2. Soil test adjustment per nutrient: low = +25 %, medium = standard, high = -25 % (unknown = standard).
3. Converted to real fertilisers per acre: DAP gives the phosphorus (and some nitrogen), MOP the potash, urea the rest of the nitrogen.
   Each nutrient is split over the application steps of that crop (base dose, top-dressings by days after sowing).
4. Extras: farmyard manure (double when organic matter is low), lime for acidic soil, gypsum for groundnut.
5. The crop stage marks steps as passed / do now / coming up; the shopping list leaves out passed steps.
   Trees and plantation crops (coffee, tea) use rounds instead of days.
6. The page scales the per-acre amounts to the field size (acres or hectares).

## Endpoints
- `GET /api/v1/fertilizer-plan/crops`
- `GET /api/v1/analyses/{id}/fertilizer-plan?crop=rice&stage=before|early|middle|late`

## To confirm with your mentor / an agriculture officer
The doses are typical package-of-practices values, not exact for any one state, variety or season. Edit only `fertilizer_plans.json`
(doses, splits, days, the +/-25 % factors, lime and manure amounts); no code changes are needed. Soil test cut-offs come from `ratings.json`.
