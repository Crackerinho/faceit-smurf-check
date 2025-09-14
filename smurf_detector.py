import json
import os

CACHE_DIR = "cache"

def load_player_data(nickname):
    """Load cached JSON file for a player."""
    path = os.path.join(CACHE_DIR, f"{nickname}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"No cache found for {nickname}")
    with open(path, "r") as f:
        return json.load(f)

def analyze_lifetime_stats(player_data):
    """Analyze lifetime stats and return smurf suspicion flags."""
    stats = player_data.get("lifetime_stats", {})
    level = player_data.get("skill_level", None)
    matches = stats.get("Matches", 0)

    flags = []

    # Headshot %
    hs = stats.get("Average Headshots %", 0)
    if hs >= 55 and level <= 5:
        flags.append(f"High HS% ({hs}%) for low level {level}")

    # 1v1 Win Rate
    win1v1 = stats.get("1v1 Win Rate", 0)
    if win1v1 >= 0.5:
        flags.append(f"Unusually high 1v1 win rate ({win1v1})")

    # Win Rate %
    win_rate = stats.get("Win Rate %", 0)
    if win_rate >= 65:
        flags.append(f"High win rate ({win_rate}%)")

    # K/D ratio
    kd = stats.get("Average K/D Ratio", 0)
    if kd >= 1.3:
        flags.append(f"High K/D ratio ({kd})")

    # ADR
    adr = stats.get("ADR", 0)
    if adr >= 85:
        flags.append(f"High ADR ({adr})")

    # 1v2 Win Rate
    win1v2 = stats.get("1v2 Win Rate", 0)
    if win1v2 >= 0.3:
        flags.append(f"High 1v2 win rate ({win1v2})")

    # Low matches but high level
    if matches < 100 and level and level >= 8:
        flags.append(f"Low matches ({matches}) but high level ({level})")

    return flags

def smurf_report(nickname):
    """Generate a smurf suspicion report for a player."""
    player_data = load_player_data(nickname)
    flags = analyze_lifetime_stats(player_data)

    if not flags:
        verdict = "No strong signs of smurfing."
    elif len(flags) == 1:
        verdict = "Mild suspicion of smurfing."
    elif 2 <= len(flags) <= 3:
        verdict = "Moderate suspicion of smurfing."
    else:
        verdict = "Strong suspicion of smurfing."

    return {
        "nickname": nickname,
        "flags": flags,
        "verdict": verdict
    }
