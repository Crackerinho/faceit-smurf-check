# **Faceit Smurf Detector 1.0.0-alpha**

## **Description**
A tool to detect potential smurf accounts on Faceit by scanning their statistics, match history and demos. Helps report suspected smurfs by helping you to fill out the ticket submission with relevant information.

---

## **Features**
- Fetches Faceit player data (statistics, match history, and more).
- Retrieves Steam playtime data for Counter-Strike 2 (It only works if the user sets it to public/friends only).
- Analyzes relevant player stats to detect potential smurf behavior.
- Provides a detailed summary of a player's profile and their match data.
- Displays a smurf detection report based on the player's activity.
- Caches data for efficient reuse (data is cached for 24 hours).
- Uses multi-threading to fetch match data in parallel, improving performance.

---

## **Requirements**

- Python 3.7+
- `requests`
- `dotenv`
- `rich`

---

## **Installation**

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/faceit-smurf-detector.git
   cd faceit-smurf-detector
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root and add your Faceit and Steam API keys:
   ```ini
   FACEIT_API_KEY=your_faceit_api_key
   STEAM_API_KEY=your_steam_api_key
   ```

4. Run the script:
   ```bash
   python faceit_smurf_detector.py
   ```

---

## **How it Works**

### **1. Faceit Player Data**
The tool begins by querying the Faceit API to retrieve data for a specific player based on their Faceit nickname. It retrieves:
- Player statistics (win rate, K/D ratio, streaks, etc.)
- Player match history (with the option to pull up to 100 recent matches)
  
The data is stored in a cache for 24 hours to avoid redundant API calls.

### **2. Steam Data**
For each player, the tool queries the Steam API to get the player’s Counter-Strike 2 playtime. This playtime is used as an additional indicator of experience, which is considered when analyzing smurf potential.

### **3. Smurf Detection**
The script uses the `smurf_detector` module to assess whether a player is likely a smurf. The module flags suspicious patterns based on factors like:
- Unusually high skill for their account age.
- High win rates and K/D ratios in early matches.

### **4. Displaying Results**
The tool displays a comprehensive player summary, including:
- Player profile (nickname, skill level, Faceit Elo, account age, etc.)
- Lifetime statistics with colored output indicating potential red flags (e.g., high K/D, win rates, etc.)
- Smurf detection report with a verdict and any flags that indicate suspicious activity.

---

## **Usage**

1. **Run the script**:
   ```bash
   python faceit_smurf_detector.py
   ```

2. **Input player nickname**: The script will prompt you to enter a Faceit nickname.
   
3. **Select match limit**: The script will ask for the number of recent matches to fetch (between 30 and 100).

4. **View player summary and smurf report**: Once the data is fetched and processed, you'll see the player's profile summary and the smurf detection report.

---

## **Example Output**

```
=== PLAYER SUMMARY ===
Nickname      : ExamplePlayer
Faceit Elo    : 2200 | Skill Level: 10 (Red)
Account Age   : 120 days
Steam CS2 Hrs : 150

--- Lifetime Stats ---
Win Rate %             : 72% (Red)
Average K/D Ratio      : 2.1 (Red)
Average Headshots %    : 55% (Red)
Current Win Streak     : 10 (Yellow)

Running smurf detection...

Smurf Detection Report for ExamplePlayer:
Verdict: Strong suspicion of smurfing. (Red)
Flags:
  - Unusually high K/D ratio in early matches
  - High win rate in the first 50 matches
```

---

## **Cache Management**
The tool caches data for up to 24 hours. If you run the script multiple times within this period, the tool will load data from the cache rather than making new API calls, improving performance.

---

## **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## **Contact**

For any questions or issues, feel free to open an issue or contact me on discord `fast_and_tactical`.

---
