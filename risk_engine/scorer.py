from pathlib import Path
import math
import yaml


RULES_FILE = Path(__file__).parent / "rules.yaml"


def load_rules():
    with open(RULES_FILE, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict):
        raise ValueError("Risk rules configuration must be a YAML mapping")

    risk_rules = config.get("risk_rules")
    risk_levels = config.get("risk_levels")
    max_score = config.get("max_score")

    if not isinstance(risk_rules, dict) or not risk_rules:
        raise ValueError("risk_rules must be a non-empty mapping")

    if not isinstance(risk_levels, dict) or not risk_levels:
        raise ValueError("risk_levels must be a non-empty mapping")

    for name, rule in risk_rules.items():
        if not isinstance(rule, dict):
            raise ValueError(f"Risk rule '{name}' must be a mapping")

        points = rule.get("points")
        if (
            isinstance(points, bool)
            or not isinstance(points, (int, float))
            or not math.isfinite(points)
            or points < 0
        ):
            raise ValueError(
                f"Risk rule '{name}' must have a finite, non-negative points value"
            )

    if (
        isinstance(max_score, bool)
        or not isinstance(max_score, (int, float))
        or not math.isfinite(max_score)
        or max_score <= 0
    ):
        raise ValueError("max_score must be a finite positive number")

    return risk_rules, risk_levels, max_score


def calculate_risk(
    heavy_rain=None,
    landslide_history=None,
    steep_slope=None,
    recent_hazard_report=None,
    heavy_traffic=None,
    low_visibility=None,
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

    missing_inputs = [
        name for name, value in conditions.items()
        if value is None
    ]

    invalid_inputs = [
        name for name, value in conditions.items()
        if value is not None and not isinstance(value, bool)
    ]

    if invalid_inputs:
        raise ValueError(
            f"Risk flags must be booleans: {invalid_inputs}"
        )

    reasons = [
        name.replace("_", " ").capitalize()
        for name, value in conditions.items()
        if value is True
    ]

    if missing_inputs:
        return {
            "risk_assessment": "incomplete",
            "risk_data_gaps": missing_inputs,
            "score": None,
            "level": None,
            "reasons": reasons,
        }

    score = 0
    for rule_name, is_active in conditions.items():
        if is_active:
            score += rules[rule_name]["points"]

    score = min(score, max_score)

    level = next(
        (
            name.capitalize()
            for name, bounds in risk_levels.items()
            if bounds["min"] <= score <= bounds["max"]
        ),
        None,
    )

    if level is None:
        raise ValueError(
            f"No configured risk level covers score {score}"
        )

    return {
        "risk_assessment": "complete",
        "risk_data_gaps": [],
        "score": score,
        "level": level,
        "reasons": reasons,
    }
