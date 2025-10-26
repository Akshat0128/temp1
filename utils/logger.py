import os, csv
from datetime import datetime
import config

LOG_DIR = os.path.join(config.LOG_FOLDER_PATH, "StrategyApp")

def ensure_log_dir():
    """Create log folder once, called by executer on import."""
    os.makedirs(LOG_DIR, exist_ok=True)

def _path_for_today() -> str:
    fname = datetime.now().strftime("%Y-%m-%d") + ".csv"
    return os.path.join(LOG_DIR, fname)

def log_event(strategy: str, action: str, msg: str = ""):
    """
    Append a row → Timestamp, Strategy, Action, Message
    """
    path = _path_for_today()
    new  = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["Timestamp", "Strategy", "Action", "Message"])
        w.writerow(
            [datetime.now().isoformat(sep=" ", timespec="seconds"),
             strategy, action, msg]
        )

    print(f"[{strategy}] {action} {msg}")