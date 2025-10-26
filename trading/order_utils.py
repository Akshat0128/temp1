from utils.load_tokken import load_scripmaster, get_exchange_from_scripmaster
import time

def get_scrip_row(token):
    """
    Returns the row from the scripmaster DataFrame for the given token.
    Uses your dynamic, auto-cached loader.
    """
    df = load_scripmaster()
    s = df[df["scripname"].str.strip().str.upper() == token.strip().upper()]
    if s.empty:
        raise ValueError(f"Scrip '{token}' not found in scripmaster!")
    return s.iloc[0]

def check_maxqty(token, order_qty):
    row = get_scrip_row(token)
    max_qty = int(row["maxqtyperorder"])
    if order_qty > max_qty:
        raise ValueError(f"Order quantity {order_qty} exceeds max allowed per order {max_qty} for {token}")

def get_retry_prices(mode, cmp, lcp, ucp):
    """
    Returns a list of (price, wait_sec) attempts per retry logic.
    mode = 'BUY' or 'SELL'
    """
    attempts = []
    if cmp < 10:
        for _ in range(3):
            if mode == 'BUY':
                cmp = min(cmp * 1.5, ucp)
            else:
                cmp = max(cmp * 0.5, lcp)
            attempts.append((round(cmp, 2), 1))
    elif cmp < 100:
        for _ in range(3):
            if mode == 'BUY':
                cmp = min(cmp * 1.2, ucp)
            else:
                cmp = max(cmp * 0.92, lcp)
            attempts.append((round(cmp, 2), 1))
    elif cmp < 250:
        if mode == 'BUY':
            cmp = min(cmp * 1.10, ucp)
        else:
            cmp = max(cmp * 0.95, lcp)
        attempts.append((round(cmp, 2), 1))
    return attempts

def clamp_price(price, lcp, ucp):
    return min(max(price, lcp), ucp)

def get_best_quote(token, mode, bridge):
    """
    Fetches best ASK (for buy) or BID (for sell) using your bridge API.
    Returns None if not available.
    """
    exchange = get_exchange_from_scripmaster(token)
    try:
        if mode == 'BUY':
            px = bridge.IB_ASK(exchange, token)
        else:
            px = bridge.IB_BID(exchange, token)
        if px is not None and px > 0:
            return px
        return None
    except Exception:
        return None