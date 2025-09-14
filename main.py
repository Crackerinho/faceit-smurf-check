import smurf_detector
import requests
import json
import os
import time
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.text import Text
from rich.live import Live
from rich.table import Table

# ---------------- Load .env ----------------
load_dotenv()
FACEIT_API_KEY = os.getenv("FACEIT_API_KEY")
STEAM_API_KEY = os.getenv("STEAM_API_KEY")
BASE_FACEIT_URL = "https://open.faceit.com/data/v4"
BASE_STEAM_URL = "https://api.steampowered.com"
headers = {"Authorization": f"Bearer {FACEIT_API_KEY}"}

CACHE_DIR = "cache"
INDEX_FILE = os.path.join(CACHE_DIR, "index.json")
os.makedirs(CACHE_DIR, exist_ok=True)

RELEVANT_STATS = [
    "Current Win Streak",
    "Average Headshots %",
    "1v1 Win Rate",
    "Win Rate %",
    "Average K/D Ratio",
    "Entry Success Rate",
    "Matches",
    "Utility Damage per Round",
    "Utility Damage Success Rate",
    "Utility Usage per Round",
    "ADR",
    "Utility Success Rate",
    "Enemies Flashed per Round",
    "Total Matches",
    "1v2 Win Rate",
    "Flash Success Rate",
    "Flashes per Round",
    "Longest Win Streak",
    "Entry Rate"
]

console = Console()

# ---------------- Helpers ----------------
def convert_to_number(value):
    if isinstance(value, (int, float)):
        return value
    try:
        if '.' not in str(value):
            return int(value)
        return float(value)
    except:
        return value

def load_index():
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r") as f:
            return json.load(f)
    return {}

def save_index(index):
    with open(INDEX_FILE, "w") as f:
        json.dump(index, f, indent=4)

def is_cache_valid(nickname):
    index = load_index()
    if nickname in index and os.path.exists(os.path.join(CACHE_DIR, f"{nickname}.json")):
        cached_time = datetime.fromisoformat(index[nickname])
        if datetime.now(timezone.utc) - cached_time < timedelta(hours=24):
            return True
    return False

def api_request(url, params=None, headers=None, max_retries=5, backoff_factor=1):
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:  # Rate limit
                console.print(f"Rate limit hit. Retrying in {backoff_factor * attempt}s...", style="yellow")
            else:
                console.print(f"HTTP {response.status_code} for {url}", style="red")
        except requests.RequestException as e:
            console.print(f"Request failed: {e}", style="red")
        time.sleep(backoff_factor * attempt)
    console.print(f"Failed to fetch {url} after {max_retries} retries.", style="red")
    return {}

# ---------------- Faceit API ----------------
def get_faceit_player_id(nickname):
    url = f"{BASE_FACEIT_URL}/players?nickname={nickname}&game=cs2"
    data = api_request(url, headers=headers)
    return data.get("player_id"), data

def get_faceit_stats(player_id):
    url = f"{BASE_FACEIT_URL}/players/{player_id}/stats/cs2"
    return api_request(url, headers=headers)

def get_match_history(player_id, limit):
    url = f"{BASE_FACEIT_URL}/players/{player_id}/history"
    params = {"game": "cs2", "limit": limit}
    data = api_request(url, headers=headers, params=params)
    return data.get("items", [])

def get_match_details(match_id):
    url = f"{BASE_FACEIT_URL}/matches/{match_id}"
    return api_request(url, headers=headers)

def get_match_stats(match_id):
    url = f"{BASE_FACEIT_URL}/matches/{match_id}/stats"
    return api_request(url, headers=headers)

# ---------------- Steam API ----------------
def get_steam_hours(steam_id):
    url = f"{BASE_STEAM_URL}/IPlayerService/GetOwnedGames/v0001/"
    params = {"key": STEAM_API_KEY, "steamid": steam_id, "format": "json"}
    data = api_request(url, params=params)
    games = data.get("response", {}).get("games", [])
    for game in games:
        if game["appid"] == 730:
            return round(game["playtime_forever"] / 60, 2)
    return 0

# ---------------- Utils ----------------
def calculate_account_age(activated_at):
    activated_date = datetime.fromisoformat(activated_at.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    return (now - activated_date).days

def filter_stats(stats):
    filtered = {}
    for key in RELEVANT_STATS:
        if key in stats:
            filtered[key] = convert_to_number(stats[key])
    return filtered

def process_team_stats(team_data):
    team_info = {}
    team_info["name"] = team_data.get("name")
    team_info["average_skill"] = convert_to_number(team_data.get("stats", {}).get("skillLevel", {}).get("average"))
    team_info["min_skill"] = convert_to_number(team_data.get("stats", {}).get("skillLevel", {}).get("range", {}).get("min"))
    team_info["max_skill"] = convert_to_number(team_data.get("stats", {}).get("skillLevel", {}).get("range", {}).get("max"))
    team_info["players"] = []
    for p in team_data.get("roster", []):
        player_info = {
            "nickname": p.get("nickname"),
            "player_id": p.get("player_id"),
            "skill_level": convert_to_number(p.get("game_skill_level"))
        }
        team_info["players"].append(player_info)
    return team_info

def process_match_stats(match_stats):
    for team in match_stats.get("rounds", [])[0].get("teams", []):
        for player in team.get("players", []):
            for k, v in player["player_stats"].items():
                player["player_stats"][k] = convert_to_number(v)
    return match_stats

# ---------------- Match Fetching with Live ETA ----------------
def fetch_match_data(match, idx, total):
    match_id = match.get("match_id")
    match_detail = get_match_details(match_id)
    match_stats = process_match_stats(get_match_stats(match_id))

    teams_processed = {t_key: process_team_stats(t_data) for t_key, t_data in match_detail.get("teams", {}).items()}
    all_skills = [t["average_skill"] for t in teams_processed.values() if t["average_skill"] is not None]
    match_avg_skill = convert_to_number(sum(all_skills)/len(all_skills)) if all_skills else None
    match_min_skill = min([t["min_skill"] for t in teams_processed.values() if t["min_skill"] is not None], default=None)
    match_max_skill = max([t["max_skill"] for t in teams_processed.values() if t["max_skill"] is not None], default=None)

    return {
        "match_id": match_id,
        "demo_url": match_detail.get("demo_url"),
        "teams": teams_processed,
        "match_avg_skill": match_avg_skill,
        "match_min_skill": match_min_skill,
        "match_max_skill": match_max_skill,
        "match_stats": match_stats,
        "idx": idx,
        "total": total
    }

# ---------------- Fetch Player ----------------
def fetch_player_data(nickname, match_limit):
    player_id, profile_data = get_faceit_player_id(nickname)
    if not player_id:
        console.print("Player not found.", style="bold red")
        return None

    steam_id = profile_data.get("games", {}).get("cs2", {}).get("game_player_id")
    steam_hours = get_steam_hours(steam_id)
    activated_at = profile_data.get("activated_at")
    account_age_days = calculate_account_age(activated_at) if activated_at else None

    faceit_stats = get_faceit_stats(player_id)
    lifetime_stats = filter_stats(faceit_stats.get("lifetime", {}))

    match_history = get_match_history(player_id, match_limit)
    matches = []

    start_time = time.time()
    with Live(console=console, refresh_per_second=4) as live:
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_match_data, match, i+1, match_limit) for i, match in enumerate(match_history)]
            for future in as_completed(futures):
                match_data = future.result()
                matches.append(match_data)
                elapsed = time.time() - start_time
                eta = elapsed / match_data["idx"] * (match_limit - match_data["idx"])
                table = Table(show_header=False, show_edge=False)
                table.add_row(f"Collected {match_data['idx']}/{match_limit} matches | ETA: {eta:.1f}s")
                live.update(table)

    matches.sort(key=lambda x: x["idx"])  # Keep original order

    return {
        "nickname": profile_data.get("nickname"),
        "activated_at": activated_at,
        "account_age_days": account_age_days,
        "skill_level": profile_data.get("games", {}).get("cs2", {}).get("skill_level"),
        "elo": profile_data.get("games", {}).get("cs2", {}).get("faceit_elo"),
        "steam_id": steam_id,
        "steam_hours_cs2": steam_hours,
        "lifetime_stats": lifetime_stats,
        "matches": matches
    }

# ---------------- Console Display ----------------
def color_skill_level(level):
    if level is None:
        return Text("N/A")
    if 1 <= level <= 3:
        return Text(str(level), style="green")
    elif 4 <= level <= 7:
        return Text(str(level), style="yellow")
    elif 8 <= level <= 9:
        return Text(str(level), style="orange1")
    elif level == 10:
        return Text(str(level), style="red")
    return Text(str(level))

def color_stat(key, value):
    if not isinstance(value, (int, float)):
        return Text(str(value))
    if "Win Rate" in key:
        if value >= 60: return Text(f"{value}", style="green")
        elif value >= 40: return Text(f"{value}", style="yellow")
        else: return Text(f"{value}", style="red")
    elif "K/D" in key or "Headshots" in key:
        if value >= 2 or value >= 50: return Text(f"{value}", style="green")
        elif value >= 1 or value >= 35: return Text(f"{value}", style="yellow")
        else: return Text(f"{value}", style="red")
    elif "Streak" in key:
        if value >= 5: return Text(f"{value}", style="green")
        elif value >= 3: return Text(f"{value}", style="yellow")
        else: return Text(f"{value}", style="red")
    return Text(str(value))

def display_player_summary(data):
    if not data:
        console.print("No data to display.", style="bold red")
        return

    console.print("\n=== PLAYER SUMMARY ===", style="bold cyan")
    console.print(f"Nickname      : {data['nickname']}")
    console.print(f"Faceit Elo    : {data['elo']} | Skill Level: ", end="")
    console.print(color_skill_level(data['skill_level']))
    console.print(f"Account Age   : {data['account_age_days']} days")
    console.print(f"Steam CS2 Hrs : {data['steam_hours_cs2']}")

    console.print("\n--- Lifetime Stats ---", style="bold cyan")
    lifetime_stats = data.get("lifetime_stats", {})
    for key in ["Win Rate %", "Average K/D Ratio", "Average Headshots %", "Current Win Streak"]:
        if key in lifetime_stats:
            value = lifetime_stats[key]
            console.print(f"{key:25}: ", end="")
            console.print(color_stat(key, value))

# ---------------- Main ----------------
def main():
    nickname = input("Enter Faceit nickname: ").strip()
    cache_file = os.path.join(CACHE_DIR, f"{nickname}.json")

    while True:
        try:
            match_limit = int(input("Enter number of matches to pull (30-100): "))
            if 30 <= match_limit <= 100:
                break
            else:
                print("Value must be between 30 and 100.")
        except ValueError:
            print("Invalid number.")

    if is_cache_valid(nickname):
        console.print(f"Loading {nickname} from cache (less than 24h old)...", style="yellow")
        with open(cache_file, "r") as f:
            output = json.load(f)
    else:
        console.print(f"Fetching data for {nickname}", style="cyan")
        output = fetch_player_data(nickname, match_limit)
        if not output:
            return
        with open(cache_file, "w") as f:
            json.dump(output, f, indent=4)
        index = load_index()
        index[nickname] = datetime.now(timezone.utc).isoformat()
        save_index(index)

    display_player_summary(output)

    # ---------------- Smurf Detector Integration ----------------
    console.print("\nRunning smurf detection...", style="bold magenta")
    report = smurf_detector.smurf_report(nickname)

    console.print(f"\nSmurf Detection Report for {report['nickname']}:", style="bold cyan")
    console.print(f"Verdict: {report['verdict']}", style="bold yellow")
    if report["flags"]:
        console.print("Flags:", style="bold red")
        for f in report["flags"]:
            console.print(f"  - {f}", style="red")
    else:
        console.print("No suspicious patterns found.", style="green")

if __name__ == "__main__":
    main()
