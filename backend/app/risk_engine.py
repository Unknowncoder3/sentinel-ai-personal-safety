from datetime import datetime


def calculate_risk(*, latitude: float, longitude: float, eta: datetime, battery_level: float | None, previous_points: list[tuple[float, float, datetime]]) -> tuple[int, list[str]]:
    """Transparent baseline risk engine. It is intentionally explainable and deterministic."""
    score = 0
    reasons: list[str] = []
    now = datetime.utcnow()

    if now.hour >= 22 or now.hour < 5:
        score += 15
        reasons.append("Night journey +15")

    if battery_level is not None and battery_level < 15:
        score += 10
        reasons.append("Low battery +10")

    if now > eta:
        minutes_late = int((now - eta).total_seconds() // 60)
        if minutes_late >= 10:
            score += 20
            reasons.append(f"ETA exceeded by {minutes_late} min +20")

    # Detect a prolonged stop from recent points. A full geospatial route
    # corridor check is added in the next iteration once a planned route is stored.
    if len(previous_points) >= 2:
        lat0, lon0, t0 = previous_points[-1]
        lat1, lon1, t1 = previous_points[0]
        elapsed_minutes = (t1 - t0).total_seconds() / 60 if t1 > t0 else 0
        distance_m = ((lat1 - lat0) ** 2 + (lon1 - lon0) ** 2) ** 0.5 * 111_000
        if elapsed_minutes >= 10 and distance_m < 50:
            score += 20
            reasons.append("Stationary for 10+ min +20")

    return min(score, 100), reasons
