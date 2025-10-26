import requests
import pandas as pd
from io import StringIO
from pathlib import Path

# Directory in the user’s home where we store cached scripmaster files
CACHE_DIR = Path.home() / ".difference_engine"
# Template name: scripmaster_{date}.txt
CACHE_FILE = CACHE_DIR / "scripmaster_{date}.txt"

# Mapping from your “UI dropdown UNDERLYING” to the codes used by the exchange-CSV endpoint
UNDERLYING_MAP = {
    "NIFTY":     "NIFTY",
    "BANKNIFTY": "BANKNIFTY",
    "SENSEX":    "BSX",
    "BANKEX":    "BKX",
}

_MASTER_DF = None

def load_scripmaster() -> pd.DataFrame:
    """
    Load (or download) today’s scripmaster files from Motilal Oswal and cache in ./cache.
    Returns a DataFrame with both NSEFO and BSEFO data concatenated.
    """
    global _MASTER_DF

    # Use ./cache in the current directory
    CACHE_DIR = Path("./cache")
    CACHE_DIR.mkdir(exist_ok=True)
    today = pd.Timestamp.now().strftime("%Y-%m-%d")
    cache_path = CACHE_DIR / f"scripmaster_{today}.csv"

    if cache_path.exists():
        _MASTER_DF = pd.read_csv(cache_path, dtype=str)
        return _MASTER_DF

    frames = []
    for exch in ["NSEFO", "BSEFO"]:
        url = f"https://openapi.motilaloswal.com/getscripmastercsv?name={exch}"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        # Most likely the first row is the header
        df = pd.read_csv(StringIO(resp.text), dtype=str)
        frames.append(df)
    
    master_df = pd.concat(frames, ignore_index=True)
    # Standardize columns
    master_df.columns = [c.strip().lower() for c in master_df.columns]
    if "scripname" in master_df.columns:
        master_df["scripname"] = master_df["scripname"].str.strip().str.upper()
    # Save to disk
    master_df.to_csv(cache_path, index=False)

    _MASTER_DF = master_df.copy()
    return _MASTER_DF


def get_valid_expiries(code: str) -> list:
    global _MASTER_DF
    if _MASTER_DF is None:
        load_scripmaster()
    code = code.strip().upper()

    code = UNDERLYING_MAP.get(code, code)  # Map to scripmaster code
    expiries = set()
    for s in _MASTER_DF["scripname"]:
        parts = s.split()
        if len(parts) >= 4 and parts[0].upper() == code:
            expiries.add(parts[1])
    return sorted(expiries, key=lambda x: pd.Timestamp(x))


def get_valid_strikes(code: str, expiry: str, opt_type: str) -> list:
    global _MASTER_DF
    if _MASTER_DF is None:
        load_scripmaster()
    code = code.strip().upper()
    code = UNDERLYING_MAP.get(code, code)
    expiry = expiry.strip().upper()
    opt_type = opt_type.strip().upper()
    strikes = set()
    for s in _MASTER_DF["scripname"]:
        parts = s.split()
        if (len(parts) >= 4 and
            parts[0].upper() == code and
            parts[1].upper() == expiry and
            parts[2].upper() == opt_type):
            strikes.add(parts[3])
    return sorted(strikes, key=lambda x: float(x))

def get_lot_size(token: str):
    global _MASTER_DF
    if _MASTER_DF is None:
        load_scripmaster()
    parts = token.strip().split()
    if len(parts) < 4:
        return None
    code, expiry, opt_type, strike = parts[0].upper(), parts[1].upper(), parts[2].upper(), parts[3]
    # Apply mapping for SENSEX/BANKEX etc
    from utils.load_tokken import UNDERLYING_MAP
    code = UNDERLYING_MAP.get(code, code)
    row = _MASTER_DF[
        (_MASTER_DF["scripname"].str.upper() == f"{code} {expiry} {opt_type} {strike}") |
        (_MASTER_DF["scripname"].str.upper().str.startswith(f"{code} {expiry} {opt_type} {strike}"))
    ]
    if not row.empty:
        try:
            return int(row.iloc[0]["marketlot"])
        except Exception:
            pass
    return None

def get_exchange_from_scripmaster(token: str):
    global _MASTER_DF
    if _MASTER_DF is None:
        load_scripmaster()
    row = _MASTER_DF[_MASTER_DF["scripname"].str.upper() == token.upper()]
    if not row.empty:
        if row.iloc[0]["exchangename"]=="NSEFO":
            return "NFO"
        else:
            return "BFO"
    return None
