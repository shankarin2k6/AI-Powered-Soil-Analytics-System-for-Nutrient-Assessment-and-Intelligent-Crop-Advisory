"""Soil health over time, from a field's saved analyses (pure Python).

The direction and the 90-day estimate come from a straight line fitted through the health scores. That is a rough
guide only: it needs at least 3 analyses spread over at least 14 days, and it is shown as an estimate.
"""
from datetime import datetime
from typing import Optional

MIN_POINTS, MIN_DAYS = 3, 14
STEADY_BAND = 2.0          # points per 30 days; inside +-2 counts as steady


def build_trend(rows: list[tuple[int, datetime, dict]]) -> dict:
    """`rows` = (analysis id, created_at, result) in any order. Analyses without lab values are skipped."""
    points = []
    for analysis_id, created, result in sorted(rows, key=lambda r: (r[1], r[0])):
        health, deg = result.get("health"), result.get("degradation")
        if not health:
            continue
        points.append({"analysis_id": analysis_id, "date": created.isoformat(), "health_score": health["score"],
                       "degradation_index": deg["index"] if deg else None})
    out: dict = {"points": points, "enough_data": False, "direction": None, "change_per_month": None,
                 "estimate_90d": None, "message_key": "trend.not_enough"}
    if len(points) < MIN_POINTS:
        return out
    t0 = datetime.fromisoformat(points[0]["date"])
    xs = [(datetime.fromisoformat(p["date"]) - t0).total_seconds() / 86400 for p in points]
    ys = [p["health_score"] for p in points]
    if xs[-1] < MIN_DAYS:
        return out
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    var = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / var          # points per day
    per_month = round(slope * 30, 1)
    direction = "improving" if per_month > STEADY_BAND else ("declining" if per_month < -STEADY_BAND else "steady")
    estimate = max(0.0, min(100.0, round(ys[-1] + slope * 90, 1)))
    out.update(enough_data=True, direction=direction, change_per_month=per_month, estimate_90d=estimate,
               message_key=f"trend.{direction}")
    return out
