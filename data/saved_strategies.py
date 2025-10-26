import os
import json
import csv
from datetime import datetime, time
import config

# Default save path for "auto-load at startup" logic (not CSV)
SAVE_PATH = os.path.join(os.getcwd(), "strategies.json")

def is_after_expiry():
    now = datetime.now()
    return now.time() >= time(hour=getattr(config, "STRATEGY_EXPIRY_HOUR", 5))  # default to 5AM if not set

# ---------- JSON Auto-Save/Auto-Load Logic (for background "remember my strategies" feature) ----------
def save_strategies(strategy_list):
    with open(SAVE_PATH, 'w') as f:
        json.dump(strategy_list, f, indent=2)
    print(f"💾 Strategies saved to {SAVE_PATH}")

def load_strategies():
    if not os.path.exists(SAVE_PATH):
        return []

    if is_after_expiry():
        print("⏳ Strategy file expired, ignoring saved strategies")
        os.remove(SAVE_PATH)
        return []

    with open(SAVE_PATH, 'r') as f:
        data = json.load(f)
        print(f"📂 Loaded {len(data)} saved strategies")
        return data

# ---------- CSV Save/Load for User Import/Export/Backup ----------
def save_strategies_csv(strategy_list, filename):
    """
    Save all strategies in a list of dicts to a CSV file.
    Each strategy dict should have keys like "Name", "Diff", ..., and for each leg: "Token1", "Side1", etc.
    """
    if not strategy_list:
        return

    # Build full column set (fixed + 8 legs)
    columns = ["Name", "Diff", "SL", "TP", "P&L"]
    for i in range(1, 9):
        columns += [f"Token{i}", f"Side{i}", f"TotalQty{i}", f"OrderQty{i}", f"TradedQty{i}"]

    with open(filename, "w", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for strat in strategy_list:
            # Always ensure 'Diff' is present
            if not strat.get("Diff"):
                strat["Diff"] = strat.get("Diff Threshold", "") or ""
            row = {key: strat.get(key, "") for key in columns}
            writer.writerow(row)

def load_strategies_csv(filename):
    """
    Load strategies from a CSV file.
    Returns a list of dicts (one per strategy), with proper handling for "Diff", "Diff Threshold", "Name", and "Strategy Name".
    """
    strategies = []
    try:
        with open(filename, "r", newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Map old/alternative field names to new
                if not row.get("Diff"):
                    row["Diff"] = row.get("Diff Threshold", "") or ""
                if not row.get("Strategy Name"):
                    row["Strategy Name"] = row.get("Name", "")
                if not row.get("Name"):
                    row["Name"] = row.get("Strategy Name", "")
                for k, v in row.items():
                    if isinstance(v, str) and v.strip().lower() == "nan":
                        row[k] = ""
                strategies.append(dict(row))
    except FileNotFoundError:
        pass
    return strategies

