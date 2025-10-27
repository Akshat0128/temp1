from PyQt5.QtCore import QThread, pyqtSignal
import time
from trading.xts_market import get_ltp as xts_get_ltp
from utils.logger import log_event
from trading.order_utils import check_maxqty, get_scrip_row, get_retry_prices, clamp_price, get_best_quote
from trading.xts_order import bridge as order_bridge
from utils.load_tokken import get_exchange_from_scripmaster
import threading
import datetime
from utils.load_tokken import get_lot_size
from math import gcd
from functools import reduce
import math
 
def calculate_locked_leg1_price(
    initial_leg1_price,
    initial_other_prices,
    current_other_prices,
    ratios,
    sides
):
    price = initial_leg1_price
    r1 = ratios[0]
    for i in range(1, len(ratios)):
        r = ratios[i]
        side = sides[i].upper()
        sign = 1 if side == "BUY" else -1
        price += sign * (current_other_prices[i-1] - initial_other_prices[i-1]) * (abs(r)/abs(r1))
    return price

class OrderLegWorker(threading.Thread):
    def __init__(self, strat, state, idx, user_id, on_update, on_finish):
        super().__init__()
        self.strat = strat
        self.state = state
        self.idx = idx
        self.user_id = user_id
        self.on_update = on_update
        self.on_finish = on_finish
        self._stop = threading.Event()
        self.setDaemon(True)

    def stop(self):
        self._stop.set()

    def _wait_with_killcheck(self, seconds):
        # Wait in small increments, bail out immediately if killed
        for _ in range(int(seconds * 10)):
            if self._stop.is_set():
                return True  # interrupted
            time.sleep(0.2)
        return False  # not interrupted

    def run(self):
        strat = self.strat
        state = self.state
        idx = self.idx

        token = strat[f"Token{idx}"]
        side = strat.get(f"Side{idx}", "BUY")
        lots = int(strat.get(f"Lots{idx}", 1))
        lot_size = state.get(f"order_qty{idx}", 1) // lots if lots > 0 else 1
        order_qty = lots * lot_size
        prev_traded = state.get(f"traded_qty{idx}", 0)
        to_trade = order_qty - prev_traded
        fill_accum = 0
        prev_entry_total = state.get(f"entry_price_total{idx}", 0.0)
        left_to_fill = to_trade

        try:
            check_maxqty(token, to_trade)
            row = get_scrip_row(token)
            lcp = float(row["lowerexchcircuitprice"])
            ucp = float(row["upperexchcircuitprice"])
            cmp = xts_get_ltp(token)
            mode = side.upper()
            exchange = get_exchange_from_scripmaster(token)
            retry_prices = get_retry_prices(mode, cmp, lcp, ucp)
            # --- Market order first ---
            if left_to_fill > 0 and not self._stop.is_set():
                if self._stop.is_set():
                    return
                req_id = order_bridge.IB_PlaceOrderAdv(
                    UniqueID=0,
                    StrategyTag=strat["Strategy Name"],
                    UserID=self.user_id,
                    Exchange=exchange,
                    Symbol=token,
                    TransactionType=mode,
                    OrderType="MKT",
                    ProductType="NRML",
                    Price=0,
                    TriggerPrice=0,
                    ProfitValue="",
                    StoplossValue="",
                    Quantity=left_to_fill,
                    CancelIfNotCompleteInSeconds=1,
                )
                state.setdefault("order_request_ids", []).append(req_id)
                if self._wait_with_killcheck(1):
                    return
                if self._stop.is_set():
                    return
                filled_qty = order_bridge.IB_OrderFilledQty(req_id)
                if self._stop.is_set():
                    return
                if filled_qty is None:
                    filled_qty = 0

                prev_traded = state.get(f"traded_qty{idx}", 0)
                prev_entry_total = state.get(f"entry_price_total{idx}", 0.0)
                fill_price = xts_get_ltp(token)
                new_qty = prev_traded + filled_qty
                new_entry_total = prev_entry_total + filled_qty * fill_price
                state[f"traded_qty{idx}"] = new_qty
                state[f"entry_price_total{idx}"] = new_entry_total
                state[f"entry_price{idx}"] = new_entry_total / new_qty if new_qty > 0 else 0.0

                fill_accum += filled_qty
                left_to_fill -= filled_qty

                self.on_update()
            # --- Retry/fallback as before ---
            for px, wait_sec in retry_prices:
                if left_to_fill <= 0 or self._stop.is_set():
                    break
                if self._stop.is_set():
                    return
                req_id = order_bridge.IB_PlaceOrderAdv(
                    UniqueID=0,
                    StrategyTag=strat["Strategy Name"],
                    UserID=self.user_id,
                    Exchange=exchange,
                    Symbol=token,
                    TransactionType=mode,
                    OrderType="LMT",
                    ProductType="NRML",
                    Price=px,
                    TriggerPrice=0,
                    ProfitValue="",
                    StoplossValue="",
                    Quantity=left_to_fill,
                    CancelIfNotCompleteInSeconds=1,
                )
                state.setdefault("order_request_ids", []).append(req_id)
                if self._wait_with_killcheck(wait_sec):
                    return
                if self._stop.is_set():
                    return
                filled_qty = order_bridge.IB_OrderFilledQty(req_id)
                if self._stop.is_set():
                    return
                if filled_qty is None:
                    filled_qty = 0

                prev_traded = state.get(f"traded_qty{idx}", 0)
                prev_entry_total = state.get(f"entry_price_total{idx}", 0.0)
                fill_price = px
                new_qty = prev_traded + filled_qty
                new_entry_total = prev_entry_total + filled_qty * fill_price
                state[f"traded_qty{idx}"] = new_qty
                state[f"entry_price_total{idx}"] = new_entry_total
                state[f"entry_price{idx}"] = new_entry_total / new_qty if new_qty > 0 else 0.0

                fill_accum += filled_qty
                left_to_fill -= filled_qty
                self.on_update()
            # --- Fallback/circuit order if still unfilled ---
            if left_to_fill > 0 and not self._stop.is_set():
                if self._stop.is_set():
                    return
                best_quote = get_best_quote(token, mode, order_bridge)
                final_px = clamp_price(
                    best_quote if best_quote is not None else (ucp if mode == "BUY" else lcp),
                    lcp, ucp
                )
                req_id = order_bridge.IB_PlaceOrderAdv(
                    UniqueID=0,
                    StrategyTag=strat["Strategy Name"],
                    UserID=self.user_id,
                    Exchange=exchange,
                    Symbol=token,
                    TransactionType=mode,
                    OrderType="LMT",
                    ProductType="NRML",
                    Price=final_px,
                    TriggerPrice=0,
                    ProfitValue="",
                    StoplossValue="",
                    Quantity=left_to_fill,
                    CancelIfNotCompleteInSeconds=0,
                )
                state.setdefault("order_request_ids", []).append(req_id)
                self.on_update()
        except Exception as e:

            log_event(strat["Strategy Name"], "Order Error", str(e))
        self.on_finish(self.idx)

class StrategyExecutor(QThread):
    update_pnl_signal = pyqtSignal(str, float)
    update_diff_signal = pyqtSignal(str, float)
    update_status_signal = pyqtSignal(str, str)
    update_qty_signal = pyqtSignal(str, list)  # For (order_qty, traded_qty) per leg

    def __init__(self, user_id, parent=None, max_loss_global=float('inf')):
        super().__init__(parent)
        self.user_id = user_id
        self.active_strategies = {}
        self.running = True
        self.market = getattr(parent, "market", None) if parent is not None else None
        self.leg_workers = {}
        self.leg_workers_finished = {}
        self.max_loss_global = max_loss_global
        self.global_stop = False


    def add_strategy(self, strat):
        name = strat.get("Strategy Name")
        if not name:
            return
        state = {
            "strategy": strat,
            "status": "waiting",
            "last_diff": 0.0,
            "entry_diff": 0.0,
        }
        for i in range(1, 9):
            lots = int(strat.get(f"Lots{i}", 0))
            token = strat.get(f"Token{i}", None)
            if token and lots > 0:
                lot_size = int(get_lot_size(token) or 1)
                state[f"order_qty{i}"] = lots * lot_size
                state.setdefault(f"traded_qty{i}", 0)
                strat[f"OrderQty{i}"] = state[f"order_qty{i}"]
                strat[f"TradedQty{i}"] = state[f"traded_qty{i}"]
                strat[f"TotalQty{i}"] = state[f"order_qty{i}"]   # For display
            else:
                state[f"order_qty{i}"] = 0
                state[f"traded_qty{i}"] = 0
                strat[f"OrderQty{i}"] = 0
                strat[f"TradedQty{i}"] = 0
                strat[f"TotalQty{i}"] = 0

        self.active_strategies[name] = state

    def remove_strategy(self, name):
        if name in self.active_strategies:
            del self.active_strategies[name]

    def resume_strategy(self, name):
        if name in self.active_strategies:
            state = self.active_strategies[name]
            if state["status"] == "disabled":
                state["status"] = "waiting"
                self.update_status_signal.emit(name, "waiting")
                self._tick(state)   # Ensure logic is re-activated!
                log_event(name, "Strategy Resumed", "Strategy status reset to waiting after being disabled.")


    def pause_strategy(self, name):
        if name in self.active_strategies:
            self.active_strategies[name]["status"] = "disabled"

    def stop(self):
        self.running = False
        self.quit()
        self.wait()

    
    def run(self):
        while self.running:
            for state in list(self.active_strategies.values()):
                self._tick(state, force_emit_diff=True)
            time.sleep(0.1)

    def square_off(self, state):
        strat = state["strategy"]

        for i in range(1, 9):  # Up to 8 legs
            token_key = f"Token{i}"
            side_key = f"Side{i}"
            lots_key = f"Lots{i}"
            traded_key = f"traded_qty{i}"


            token_value = strat.get(token_key) # Get the actual token string
            if token_value: # Check if the token string exists
                total_qty = int(strat.get(lots_key, 0))
                traded_qty = int(state.get(traded_key, 0))
                open_qty = total_qty - traded_qty
                
                # Use the 'token_value' here, not 'token_key'
                exchange = get_exchange_from_scripmaster(token_value) 

                if open_qty > 0:
                    original_side = strat.get(side_key, "BUY").upper()
                    counter_side = "SELL" if original_side == "BUY" else "BUY"
                    try:
                        req_id = order_bridge.IB_PlaceOrderAdv(
                            UniqueID=0,
                            StrategyTag=strat["Strategy Name"],
                            UserID=state["user_id"],
                            Exchange=exchange,  
                            Symbol=strat[token_key],
                            TransactionType=counter_side,
                            OrderType="MKT",
                            ProductType="NRML",
                            Price=0,
                            TriggerPrice=0,
                            ProfitValue="",
                            StoplossValue="",
                            Quantity=open_qty,
                            CancelIfNotCompleteInSeconds=0,
                        )
                        state.setdefault("order_request_ids", []).append(req_id)
                        log_event(strat["Strategy Name"], "Square Off", f"Market {counter_side} {open_qty} of {strat[token_key]}")
                    except Exception as e:
                        log_event(strat["Strategy Name"], "Square Off Error", f"Leg {i}: {e}")

        state["status"] = "squared_off"
        self.update_status_signal.emit(strat["Strategy Name"], "squared_off")
        log_event(strat["Strategy Name"], "Square Off", "All open positions sent for square off at market.")

    def _tick(self, state, force_emit_diff=False):
        strat = state["strategy"]
        status = state["status"]

        legs = []
        order_qtys = []
        traded_qtys = []

        # Collect only valid legs
        for i in range(1, 9):
            token = strat.get(f"Token{i}", "").strip().upper()
            side = strat.get(f"Side{i}", "").strip().upper()
            qty = float(strat.get(f"TotalQty{i}", 0) or 0)
            if not token or not side or qty == 0:
                continue  # Skip unused/blank legs
            price = xts_get_ltp(token) or 0.0
            try:
                lot_size = int(get_lot_size(token) or 1)
            except Exception:
                lot_size = 1
            lots = int(strat.get(f"Lots{i}", 1))
            legs.append((side, lots, price, lot_size, token))
            order_qtys.append(state.get(f"order_qty{i}", lots * lot_size))
            traded_qtys.append(state.get(f"traded_qty{i}", 0))

        num_legs = len(legs)
        if num_legs == 0:
            # No valid legs, cannot proceed
            self.update_diff_signal.emit(strat.get("Strategy Name", ""), 0.0)
            return

        # --- MODIFICATION START ---
        # --- New Difference Calculation Logic based on user request ---
        # Formula: (total amount buy - total amount sell) / (total shares buyed (accross all leg))
        
        total_buy_value = sum(abs(lots) * lot_size * price for (side, lots, price, lot_size, _) in legs if side == "BUY")
        total_sell_value = sum(abs(lots) * lot_size * price for (side, lots, price, lot_size, _) in legs if side == "SELL")

        # Denominator is the total quantity of *all BUY legs*
        total_buy_quantity = sum(abs(lots) * lot_size for (side, lots, _, lot_size, _) in legs if side == "BUY")

        net = 0.0
        if total_buy_quantity > 0:
            net = (total_buy_value - total_sell_value) / total_buy_quantity
        # --- MODIFICATION END ---


        # Always emit diff for GUI, even if disabled
        self.update_diff_signal.emit(strat.get("Strategy Name", ""), net)
        self.update_qty_signal.emit(strat.get("Strategy Name", ""), list(zip(order_qtys, traded_qtys)))

        threshold = float(strat.get("Diff Threshold") or 0)

        if status == "waiting":
            if net>=threshold:

                state["entry_diff"] = net
                state["status"] = "triggered"
                self.update_status_signal.emit(strat["Strategy Name"], "triggered")
                log_event(strat["Strategy Name"], "Triggered", f"at diff {net:.2f}")

                def fire_leg_k(k, qty_k, state, strat, tokens, sides, self_ref, leg1_fill_price, entry_diff, side1):
                    try:
                        token_k = tokens[k]
                        side_k = sides[k].upper()
                        exchange_k = get_exchange_from_scripmaster(token_k)

                        # Step 1: Anchored limit price logic
                        if side1 == "BUY" and side_k == "SELL":
                            limit_price_k = leg1_fill_price - entry_diff
                        elif side1 == "SELL" and side_k == "BUY":
                            limit_price_k = leg1_fill_price + entry_diff
                        else:
                            limit_price_k = leg1_fill_price

                        row_k = get_scrip_row(token_k)
                        lcp_k = float(row_k["lowerexchcircuitprice"])
                        ucp_k = float(row_k["upperexchcircuitprice"])
                        limit_price_k = clamp_price(limit_price_k, lcp_k, ucp_k)

                        # First attempt: limit order at anchored price
                        reqid_k = order_bridge.IB_PlaceOrderAdv(
                            UniqueID=0,
                            StrategyTag=strat["Strategy Name"],
                            UserID=self_ref.user_id,
                            Exchange=exchange_k,
                            Symbol=token_k,
                            TransactionType=side_k,
                            OrderType="LMT",
                            ProductType="NRML",
                            Price=limit_price_k,
                            TriggerPrice=0,
                            ProfitValue="",
                            StoplossValue="",
                            Quantity=qty_k,
                            CancelIfNotCompleteInSeconds=1,
                        )
                        state.setdefault("order_request_ids", []).append(reqid_k)

                        filled_qty_k = 0
                        elapsed = 0
                        poll_interval = 0.1
                        while elapsed < 1.0:
                            filled_qty_now = order_bridge.IB_OrderFilledQty(reqid_k) or 0
                            if filled_qty_now > 0:
                                filled_qty_k = filled_qty_now
                                break
                            time.sleep(poll_interval)
                            elapsed += poll_interval

                        # If still unfilled, use retry ladder
                        if filled_qty_k < qty_k:
                            unfilled_qty = qty_k - filled_qty_k
                            cmp = limit_price_k
                            retry_prices = get_retry_prices(side_k, cmp, lcp_k, ucp_k)
                            for retry_price, wait_sec in retry_prices:
                                reqid_k_retry = order_bridge.IB_PlaceOrderAdv(
                                    UniqueID=0,
                                    StrategyTag=strat["Strategy Name"],
                                    UserID=self_ref.user_id,
                                    Exchange=exchange_k,
                                    Symbol=token_k,
                                    TransactionType=side_k,
                                    OrderType="LMT",
                                    ProductType="NRML",
                                    Price=retry_price,
                                    TriggerPrice=0,
                                    ProfitValue="",
                                    StoplossValue="",
                                    Quantity=unfilled_qty,
                                    CancelIfNotCompleteInSeconds=wait_sec,
                                )
                                state.setdefault("order_request_ids", []).append(reqid_k_retry)
                                # Wait for fill or timeout
                                elapsed_retry = 0
                                while elapsed_retry < wait_sec:
                                    filled_qty_now = order_bridge.IB_OrderFilledQty(reqid_k_retry) or 0
                                    if filled_qty_now > 0:
                                        filled_qty_k += filled_qty_now
                                        break
                                    time.sleep(poll_interval)
                                    elapsed_retry += poll_interval
                                if filled_qty_k >= qty_k:
                                    break  # done

                            # If still not filled, fallback to best quote or circuit
                            if filled_qty_k < qty_k:
                                best_quote = get_best_quote(token_k, side_k, order_bridge)
                                fallback_price = (
                                    best_quote if best_quote is not None else (ucp_k if side_k == "BUY" else lcp_k)
                                )
                                reqid_k_fallback = order_bridge.IB_PlaceOrderAdv(
                                    UniqueID=0,
                                    StrategyTag=strat["Strategy Name"],
                                    UserID=self_ref.user_id,
                                    Exchange=exchange_k,
                                    Symbol=token_k,
                                    TransactionType=side_k,
                                    OrderType="LMT",
                                    ProductType="NRML",
                                    Price=fallback_price,
                                    TriggerPrice=0,
                                    ProfitValue="",
                                    StoplossValue="",
                                    Quantity=qty_k - filled_qty_k,
                                    CancelIfNotCompleteInSeconds=0,  # Good till filled/cancelled
                                )
                                state.setdefault("order_request_ids", []).append(reqid_k_fallback)
                                # No wait: let risk management or manual intervention handle further

                        # Update state as before
                        prev_traded_k = state.get(f"traded_qty{k+1}", 0)
                        state[f"traded_qty{k+1}"] = prev_traded_k + filled_qty_k
                        state[f"entry_price_total{k+1}"] = state.get(f"entry_price_total{k+1}", 0.0) + filled_qty_k * limit_price_k
                        state[f"entry_price{k+1}"] = (
                            state[f"entry_price_total{k+1}"] / state[f"traded_qty{k+1}"] if state[f"traded_qty{k+1}"] > 0 else 0.0
                        )
                    except Exception as e:
                        log_event(strat["Strategy Name"], f"Leg {k+1} hedge order error", str(e))

                def leg1_diff_locked_executor():
                    num_legs = len(legs)
                    sides = [leg[0] for leg in legs]
                    ratios = [leg[1] for leg in legs]
                    lot_sizes = [leg[3] for leg in legs]
                    tokens = [strat[f"Token{i}"] for i in range(1, num_legs+1)]
                    initial_ltps = [xts_get_ltp(t) for t in tokens]
                    initial_leg1_price = initial_ltps[0]
                    initial_other_prices = initial_ltps[1:]

                    order_qtys = [state.get(f"order_qty{i+1}", ratios[i] * lot_sizes[i]) for i in range(num_legs)]
                    traded_qtys = [state.get(f"traded_qty{i+1}", 0) for i in range(num_legs)]
                    to_trade = order_qtys[0] - traded_qtys[0]
                    if to_trade <= 0:
                        return

                    row = get_scrip_row(tokens[0])
                    lcp = float(row["lowerexchcircuitprice"])
                    ucp = float(row["upperexchcircuitprice"])
                    mode = sides[0].upper()
                    exchange = get_exchange_from_scripmaster(tokens[0])
                    leg1_price = clamp_price(initial_leg1_price, lcp, ucp)
                    req_id = order_bridge.IB_PlaceOrderAdv(
                        UniqueID=0,
                        StrategyTag=strat["Strategy Name"],
                        UserID=self.user_id,
                        Exchange=exchange,
                        Symbol=tokens[0],
                        TransactionType=mode,
                        OrderType="LMT",
                        ProductType="NRML",
                        Price=leg1_price,
                        TriggerPrice=0,
                        ProfitValue="",
                        StoplossValue="",
                        Quantity=to_trade,
                        CancelIfNotCompleteInSeconds=1,
                    )
                    state.setdefault("order_request_ids", []).append(req_id)
                    last_leg1_price = leg1_price
                    total_filled_leg1 = 0
                    start_time = time.time()
                    already_filled = 0

                    start_time = time.time()
                    log_event(strat["Strategy Name"], "LEG1_ROLLING_LOOP_START", str(start_time))
                    deadline = time.time() + 1.0
                    while (to_trade - total_filled_leg1 > 0):
                        iter_start = time.time()
                        if iter_start >= deadline:
                            break
                        current_other_prices = [xts_get_ltp(t) for t in tokens[1:]]
                        new_leg1_price = calculate_locked_leg1_price(
                            initial_leg1_price,
                            initial_other_prices,
                            current_other_prices,
                            ratios,
                            sides
                        )
                        new_leg1_price = clamp_price(new_leg1_price, lcp, ucp)
                        if abs(new_leg1_price - last_leg1_price) > 0.01:
                            try:
                                order_bridge.IB_ModifyOrder(req_id, Price=new_leg1_price, TriggerPrice=0, ProfitValue="", StoplossValue="", Quantity=to_trade - total_filled_leg1)
                                last_leg1_price = new_leg1_price
                            except Exception as e:
                                log_event(strat["Strategy Name"], "Order Modify Error", str(e))

                        filled_now = order_bridge.IB_OrderFilledQty(req_id) or 0
                        partial_filled = filled_now - already_filled
                        
                        # This is the quantity of LEG 1 that just got filled in this iteration
                        filled_qty_leg1 = partial_filled 

                        if filled_qty_leg1 > 0:
                            qty1 = order_qtys[0] 
                            if qty1 > 0:
                                for k in range(1, num_legs):
                                    qty_k = order_qtys[k]
                                   
                                    hedge_qty = int((qty_k / qty1) * filled_qty_leg1) 
                                    
                                    if hedge_qty > 0:
                                        t = threading.Thread(
                                            target=fire_leg_k,
                                            args=(
                                                k,  # Use the 0-based index 'k'
                                                hedge_qty,
                                                state,
                                                strat,
                                                tokens,
                                                sides,
                                                self,
                                                last_leg1_price,
                                                state["entry_diff"],
                                                sides[0].upper()
                                            )
                                        )
                                        t.daemon = True
                                        t.start()
                            if hedge_qty > 0:
                                t = threading.Thread(
                                    target=fire_leg_k,
                                    args=(
                                        k - 1,  
                                        hedge_qty,
                                        state,
                                        strat,
                                        tokens,
                                        sides,
                                        self,
                                        last_leg1_price,
                                        state["entry_diff"],
                                        sides[0].upper()
                                    )
                                )
                                t.daemon = True
                                t.start()

                            self.update_qty_signal.emit(strat.get("Strategy Name", ""), [(order_qtys[i], state.get(f"traded_qty{i+1}", 0)) for i in range(num_legs)])
                        iter_end = time.time()
                        if iter_end - start_time >= 1.0:
                                break
                        time.sleep(max(0,0.05-(iter_end - iter_start)))
                    try:
                        order_bridge.IB_CancelOrExitOrder(req_id)
                        log_event(strat["Strategy Name"], "Order Cancel", f"Unfilled qty cancelled after 1s")
                    except Exception as e:
                        log_event(strat["Strategy Name"], "Cancel error", str(e))
                    total_filled_leg1 = state.get("traded_qty1", 0)  # Or whatever variable tracks this in your logic
                    target_qty = state.get("order_qty1", 0)

                    if total_filled_leg1 == 0:
                        if state["status"] != "disabled":
                            state["status"] = "waiting"
                            self.update_status_signal.emit(strat["Strategy Name"], "waiting")
                            log_event(strat["Strategy Name"], "LEG1_CANCELLED", "No fill after all retries, status reset to waiting.")
                        else:
                            log_event(strat["Strategy Name"], "LEG1_CANCELLED", "No fill, but user disabled strategy, so not resetting to waiting.")
                        return

                    if total_filled_leg1 < target_qty:
                        if state["status"] != "disabled":
                            state["status"] = "waiting"
                            self.update_status_signal.emit(strat["Strategy Name"], "waiting")
                            log_event(
                                strat["Strategy Name"],
                                "LEG1_PARTIAL_CANCEL",
                                f"Partial fill: filled {total_filled_leg1} of {target_qty}; status reset to waiting for next trigger."
                            )
                        else:
                            log_event(
                                strat["Strategy Name"],
                                "LEG1_PARTIAL_CANCEL",
                                f"Partial fill: filled {total_filled_leg1} of {target_qty}; but user disabled, so not resetting to waiting."
                            )
                        return

                thread = threading.Thread(target=leg1_diff_locked_executor)
                thread.daemon = True
                thread.start()
                self.update_status_signal.emit(strat.get("Strategy Name", ""), state["status"])
                self.update_pnl_signal.emit(strat.get("Strategy Name", ""), 0.0)
                
        # ---- ABSOLUTE P&L CALCULATION ----
        if status == "triggered":
            abs_pnl = 0
            for idx, (side, lots, _, lot_size, token) in enumerate(legs, 1):
                traded_qty = state.get(f"traded_qty{idx}", 0)
                entry_price = state.get(f"entry_price{idx}", None)
                if traded_qty > 0 and entry_price is not None:
                    current_price = xts_get_ltp(token)
                    if side == "BUY":
                        leg_pnl = (current_price - entry_price) * traded_qty
                    else:
                        leg_pnl = (entry_price - current_price) * traded_qty
                    abs_pnl += leg_pnl
            strat['P&L'] = round(abs_pnl, 2)
            self.update_pnl_signal.emit(strat['Strategy Name'], abs_pnl)

            entry_diff = float(state.get("entry_diff", net))
            sl_raw = strat.get("SL", 0)
            tp_raw = strat.get("TP", 0)
            sl_mode = strat.get("SL_Mode", "diff")
            tp_mode = strat.get("TP_Mode", "diff")

            def parse_sl_tp(value, entry):
                try:
                    if isinstance(value, str) and value.strip().endswith('%'):
                        pct = float(value.strip().rstrip('%'))
                        return (pct / 100.0) * abs(entry)
                    return float(value)
                except Exception:
                    return 0

            tp = parse_sl_tp(tp_raw, entry_diff)
            sl = parse_sl_tp(sl_raw, entry_diff)

            # TP logic
            if tp:
                if tp_mode == "abs":
                    if entry_diff >= 0 and net >= tp:
                        state["status"] = "tp_hit"
                        log_event(strat["Strategy Name"], "TP Hit", f"(Abs, Buy) net={net:.2f} >= tp={tp:.2f}")
                        self.square_off(state)
                        self.update_status_signal.emit(strat.get("Strategy Name", ""), state["status"])
                        return
                    elif entry_diff < 0 and net <= tp:
                        state["status"] = "tp_hit"
                        log_event(strat["Strategy Name"], "TP Hit", f"(Abs, Sell) net={net:.2f} <= tp={tp:.2f}")
                        self.square_off(state)
                        self.update_status_signal.emit(strat.get("Strategy Name", ""), state["status"])
                        return
                else:  
                    if entry_diff >= 0 and net >= entry_diff + abs(tp):
                        state["status"] = "tp_hit"
                        log_event(strat["Strategy Name"], "TP Hit", f"(Diff, Buy) net={net:.2f} >= entry+tp={entry_diff+abs(tp):.2f}")
                        self.square_off(state)
                        self.update_status_signal.emit(strat.get("Strategy Name", ""), state["status"])
                        return
                    elif entry_diff < 0 and net <= entry_diff - abs(tp):
                        state["status"] = "tp_hit"
                        log_event(strat["Strategy Name"], "TP Hit", f"(Diff, Sell) net={net:.2f} <= entry-tp={entry_diff-abs(tp):.2f}")
                        self.square_off(state)
                        self.update_status_signal.emit(strat.get("Strategy Name", ""), state["status"])
                        return

            if sl:
                if sl_mode == "abs":
                    if entry_diff >= 0 and net <= sl:
                        state["status"] = "sl_hit"
                        log_event(strat["Strategy Name"], "SL Hit", f"(Abs, Buy) net={net:.2f} <= sl={sl:.2f}")
                        self.square_off(state)
                        self.update_status_signal.emit(strat.get("Strategy Name", ""), state["status"])
                        return
                    elif entry_diff < 0 and net >= sl:
                        state["status"] = "sl_hit"
                        log_event(strat["Strategy Name"], "SL Hit", f"(Abs, Sell) net={net:.2f} >= sl={sl:.2f}")
                        self.square_off(state)
                        self.update_status_signal.emit(strat.get("Strategy Name", ""), state["status"])
                        return
                else:  # Diff mode
                    if entry_diff >= 0 and net <= entry_diff - abs(sl):
                        state["status"] = "sl_hit"
                        log_event(strat["Strategy Name"], "SL Hit", f"(Diff, Buy) net={net:.2f} <= entry-sl={entry_diff-abs(sl):.2f}")
                        self.square_off(state)
                        self.update_status_signal.emit(strat.get("Strategy Name", ""), state["status"])
                        return
                    elif entry_diff < 0 and net >= entry_diff + abs(sl):
                        state["status"] = "sl_hit"
                        log_event(strat["Strategy Name"], "SL Hit", f"(Diff, Sell) net={net:.2f} >= entry+sl={entry_diff+abs(sl):.2f}")
                        self.square_off(state)
                        self.update_status_signal.emit(strat.get("Strategy Name", ""), state["status"])
                        return
        if status == "disabled" and not force_emit_diff:
            return


        for idx in range(1, num_legs + 1):
            strat[f"OrderQty{idx}"] = state.get(f"order_qty{idx}", 0)
            strat[f"TradedQty{idx}"] = state.get(f"traded_qty{idx}", 0)
        self.update_qty_signal.emit(strat.get("Strategy Name", ""), list(zip(order_qtys, traded_qtys)))


    def kill_switch(self):
        for strat_name, state in self.active_strategies.items():
            strat = state["strategy"]
            # --- Cancel all app-placed orders ---
            for order_id in state.get("order_request_ids", []):
                try:
                    order_bridge.IB_CancelOrExitOrder(order_id)
                    log_event(strat["Strategy Name"], "Kill Switch", f"Cancelled Order {order_id}")
                except Exception as e:
                    log_event(strat["Strategy Name"], "Kill Switch Error", f"Order {order_id}: {str(e)}")

            # --- Square off any open positions from this strategy ---
            try:
                self.square_off(state)
                log_event(strat["Strategy Name"], "Kill Switch", "Strategy squared off.")
            except Exception as e:
                log_event(strat["Strategy Name"], "Kill Switch Error", f"Square-off: {str(e)}")

            # --- Stop the strategy ---
            state["status"] = "disabled"

        self.update_status_signal.emit("SYSTEM", "All strategies stopped by kill switch.")
        print("[SYSTEM] Kill Switch All strategies stopped by kill switch.")