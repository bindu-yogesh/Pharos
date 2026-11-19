from pathlib import Path
from collections.abc import Mapping
import yaml


RULES_FILE = Path(__file__).parent / "rules.yaml"


def load_rules():
    try:
        with open(RULES_FILE, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
    except yaml.YAMLError as error:
        raise ValueError("Risk rules YAML is invalid") from error

    if not isinstance(config, Mapping):
        raise ValueError("Risk rules configuration must be a mapping")

    required_config_keys = {"risk_rules", "risk_levels", "max_score"}
    if set(config) != required_config_keys:
        raise ValueError("Risk rules configuration has missing or unexpected keys")

    rules = config["risk_rules"]
    levels = config["risk_levels"]
    max_score = config["max_score"]

    required_factors = {
        "heavy_rain",
        "landslide_history",
        "steep_slope",
        "recent_hazard_report",
        "heavy_traffic",
        "low_visibility",
    }

    if not isinstance(rules, Mapping) or set(rules) != required_factors:
        raise ValueError("Risk rules must define exactly the supported risk factors")

    for factor, rule in rules.items():
        if not isinstance(rule, Mapping):
            raise ValueError(f"Rule '{factor}' must be a mapping")

        points = rule.get("points")
        description = rule.get("description")

        if (
            not isinstance(points, int)
            or isinstance(points, bool)
            or points < 0
        ):
            raise ValueError(f"Rule '{factor}' points must be a non-negative integer")

        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"Rule '{factor}' needs a non-empty description")

    if (
        not isinstance(max_score, int)
        or isinstance(max_score, bool)
        or max_score <= 0
    ):
        raise ValueError("max_score must be a positive integer")

    if not isinstance(levels, Mapping) or not levels:
        raise ValueError("risk_levels must be a non-empty mapping")

    validated_levels = []
    for name, boundaries in levels.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Risk level names must be non-empty strings")

        if not isinstance(boundaries, Mapping):
            raise ValueError(f"Risk level '{name}' must be a mapping")

        if set(boundaries) != {"min", "max"}:
            raise ValueError(f"Risk level '{name}' must define min and max")

        lower = boundaries["min"]
        upper = boundaries["max"]

        if any(
            not isinstance(value, int) or isinstance(value, bool)
            for value in (lower, upper)
        ):
            raise ValueError(f"Risk level '{name}' boundaries must be integers")

        if lower < 0 or upper < lower or upper > max_score:
            raise ValueError(f"Risk level '{name}' has invalid boundaries")

        validated_levels.append((lower, upper, name))

    validated_levels.sort()

    expected_minimum = 0
    for lower, upper, name in validated_levels:
        if lower != expected_minimum:
            raise ValueError("Risk level boundaries must be contiguous and non-overlapping")
        expected_minimum = upper + 1

    if expected_minimum != max_score + 1:
        raise ValueError("Risk levels must cover the full range from 0 to max_score")

    return rules, levels, max_score


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
