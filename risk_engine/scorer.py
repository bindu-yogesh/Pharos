from pathlib import Path
import yaml


RULES_FILE = Path(__file__).parent / "rules.yaml"


def load_rules():
    with open(RULES_FILE, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    return (
        config["risk_rules"],
        config["risk_levels"],
        config["max_score"],
    )


def calculate_risk(
    heavy_rain=False,
    landslide_history=False,
    steep_slope=False,
    recent_hazard_report=False,
    heavy_traffic=False,
    low_visibility=False,
):
    rules, risk_levels, max_score = load_rules()

    conditions = {
        "heavy_rain": heavy_rain,
        "landslide_history": landslide_history,
        "steep_slope": steep_slope,
        "recent_hazard_report": recent_hazard_report,
        "heavy_traffic": heavy_traffic,
        "low_visibility": low_visibility,
    }

    score = 0
    reasons = []
    missing_factors = []

    for rule_name, is_active in conditions.items():
        if is_active is None:
            missing_factors.append(rule_name)
            continue

        if not isinstance(is_active, bool):
            raise TypeError(f"{rule_name} must be True, False, or None")

        if is_active:
            score += rules[rule_name]["points"]
            reasons.append(rule_name.replace("_", " ").capitalize())

    score = min(score, max_score)

    if missing_factors:
        return {
            "score": None,
            "known_score": score,
            "level": None,
            "reasons": reasons,
            "status": "incomplete",
            "missing_factors": missing_factors,
        }

    level = None

    for level_name, boundaries in risk_levels.items():
        if boundaries["min"] <= score <= boundaries["max"]:
            level = level_name.capitalize()
            break

    if level is None:
        raise ValueError(f"Risk score {score} does not fit any configured risk level")

    return {
        "score": score,
        "known_score": score,
        "level": level,
        "reasons": reasons,
        "status": "complete",
        "missing_factors": [],
    }
