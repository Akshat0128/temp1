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
            # 'strat_state' here is the 'state' object from the executor
            for name, strat_state in self.executor.active_strategies.items(): 
                if strat_state['status'] == 'triggered':
                    # Call square_off with just the state object
                    self.executor.square_off(strat_state) 
                    
                    strat_state['status'] = 'squared_off'
                    strat_state['position'] = 'closed'
                    print(f"🔁 Strategy '{name}' squared off")
            