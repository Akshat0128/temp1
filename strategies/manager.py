# Handles starting, stopping, editing strategies on demand

import threading
import time
from utils.pyIB_APIS import IB_APIS


class StrategyManager:
    def __init__(self, executor):
        self.executor = executor
        self.disabled_strategies = set()

    def disable_strategy(self, name):
        if name in self.executor.active_strategies:
            self.disabled_strategies.add(name)
            self.executor.active_strategies[name]['status'] = 'disabled'
            self.executor.update_status_signal.emit(name, "disabled")

            print(f"🚫 Strategy '{name}' has been disabled")

    def enable_strategy(self, name):
        if name in self.disabled_strategies or (name in self.executor.active_strategies and self.executor.active_strategies[name]['status'] == 'disabled'):
            self.disabled_strategies.discard(name)
            self.executor.resume_strategy(name)
            print(f"✅ Strategy '{name}' re-enabled")

    def edit_strategy(self, name, field, new_value):
        if name in self.executor.active_strategies:
            self.executor.active_strategies[name]['data'][field] = new_value
            print(f"✏️ Updated {field} of '{name}' to {new_value}")

    def square_off_all(self):
        for name, strat in self.executor.active_strategies.items():
            if strat['status'] == 'triggered':
                self.executor.square_off(strat, strat['data']["Token 1"], strat['data']["Token 2"])
                strat['status'] = 'squared_off'
                strat['position'] = 'closed'
                print(f"🔁 Strategy '{name}' squared off")
        
    def start_mtm_monitor(self, user_id, mtm_cap, executor):
        def monitor():
            ib = IB_APIS(source_url="YOUR_BRIDGE_URL")
            while True:
                try:
                    mtm = ib.IB_MTM(user_id)
                    if mtm is not None and float(mtm) < -abs(float(mtm_cap)):
                        print(f"[MTM_MONITOR] MTM {mtm} < -{mtm_cap}, disabling all strategies.")
                        executor.global_stop = True
                        # Disable all strategies, don't square off
                        for state in executor.active_strategies.values():
                            if state["status"] != "disabled":
                                state["status"] = "disabled"
                                executor.update_status_signal.emit(state["strategy"]["Strategy Name"], "disabled")
                        break
                except Exception as e:
                    print(f"[MTM_MONITOR] Error: {e}")
                time.sleep(1)  # 1 second polling
        threading.Thread(target=monitor, daemon=True).start()

