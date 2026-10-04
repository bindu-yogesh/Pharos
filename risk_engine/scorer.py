from pathlib import Path
import yaml


RULES_FILE = Path(__file__).parent / "rules.yaml"


def load_rules():
    with open(RULES_FILE, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    return config["risk_rules"], config["max_score"]


def calculate_risk(
    heavy_rain=False,
    landslide_history=False,
    steep_slope=False,
    recent_hazard_report=False,
    heavy_traffic=False,
    low_visibility=False,
):
    rules, max_score = load_rules()

    score = 0
    reasons = []

    conditions = {
        "heavy_rain": heavy_rain,
        "landslide_history": landslide_history,
        "steep_slope": steep_slope,
        "recent_hazard_report": recent_hazard_report,
        "heavy_traffic": heavy_traffic,
        "low_visibility": low_visibility,
    }

    for rule_name, is_active in conditions.items():
        if is_active:
            score += rules[rule_name]["points"]
            reasons.append(rule_name.replace("_", " ").capitalize())

    score = min(score, max_score)

    if score <= 30:
        level = "Green"
    elif score <= 50:
        level = "Yellow"
    elif score <= 75:
        level = "Orange"
    else:
        level = "Red"

    return {
        "score": score,
        "level": level,
        "reasons": reasons,
    }