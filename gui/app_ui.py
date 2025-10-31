from PyQt5.QtWidgets import (
    QMainWindow, QDialog, QVBoxLayout, QRadioButton, QLineEdit, QPushButton, QHBoxLayout, QLabel, QButtonGroup,
    QComboBox, QSpinBox, QWidget, QTableWidget, QTableWidgetItem, QMessageBox, QAbstractItemView, QFileDialog, QCheckBox
)
from PyQt5.QtCore import Qt, QEvent, QTimer
from datetime import datetime
from strategies.executer import StrategyExecutor
from trading.xts_market import get_ltp
from utils.load_tokken import get_valid_expiries, get_valid_strikes, get_lot_size
import csv
from utils.load_tokken import load_scripmaster
from data.saved_strategies import save_strategies, load_strategies
from strategies.manager import StrategyManager
from utils.strategy_helpers import calculate_per_ratio_diff
from PyQt5.QtGui import QColor, QBrush
import json
import os
import config

def save_max_loss(value):
    with open("max_loss.json", "w") as f:
        json.dump({"max_loss": value}, f)

def load_max_loss():
    if os.path.exists("max_loss.json"):
        try:
            with open("max_loss.json", "r") as f:
                val = json.load(f).get("max_loss", "")
                return float(val) if val not in ("", None) else ""
        except Exception:
            pass
    return ""

class StrikeComboBox(QComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.setMinimumWidth(130)
        self.lineEdit().installEventFilter(self)
        self._cleared_once = False

    def eventFilter(self, obj, event):
        if obj == self.lineEdit():
            if event.type() == QEvent.FocusIn or event.type() == QEvent.MouseButtonPress:
                if not self._cleared_once and self.currentText() in ("--SELECT--", "0"):
                    self.setEditText("")
                    self._cleared_once = True
        return super().eventFilter(obj, event)

class AddStrategyDialog(QDialog):
    def __init__(self, parent=None, strategy_data=None, edit_mode=False):
        super().__init__(parent)
        self.scrip_df = load_scripmaster()
        self.setWindowTitle("Add / Edit Strategy")
        self.underlyings = ["NIFTY", "BANKNIFTY", "SENSEX", "BANKEX"]
        self.leg_widgets = []
        self.strategy_data = strategy_data
        self.edit_mode = edit_mode


        main_layout = QVBoxLayout(self)

        # 1. Legs Layout (on top)
        self.legs_layout = QVBoxLayout()
        main_layout.addLayout(self.legs_layout)

        # 1a. Add Leg + Current Diff row
        add_leg_row = QHBoxLayout()
        self.add_leg_btn = QPushButton("Add Leg")
        self.add_leg_btn.clicked.connect(self.add_leg)
        self.live_diff_label = QLabel("Current Diff: --")
        add_leg_row.addWidget(self.add_leg_btn)
        add_leg_row.addWidget(self.live_diff_label)
        add_leg_row.addStretch()
        main_layout.addLayout(add_leg_row)
        # FIX: This call was missing, preventing signals from being connected on init
        # self.setup_leg_signals() # This is called in add_leg, so it's OK

        # 2. Diff Threshold row (before name)
        diff_row = QHBoxLayout()
        diff_row.addWidget(QLabel("Diff Threshold*:"))
        self.diff_edit = QLineEdit(
            (strategy_data.get("Diff Threshold") if strategy_data else "")
            or (strategy_data.get("Diff") if strategy_data else "")
            or ""
        )
        diff_row.addWidget(self.diff_edit)
        main_layout.addLayout(diff_row)

        # 3. Strategy Name row
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Strategy Name:"))
        rand_name = f"STRAT_{''.join(__import__('os').urandom(3).hex().upper())}"
        self.name_edit = QLineEdit(strategy_data.get("Strategy Name", rand_name) if strategy_data else rand_name)
        name_row.addWidget(self.name_edit)
        main_layout.addLayout(name_row)

        # 4. Enable SL/TP with checkboxes and radio buttons in button groups
        sl_tp_layout = QHBoxLayout()
        self.enable_sl_chk = QCheckBox("Enable SL")
        self.sl_edit = QLineEdit(strategy_data.get("SL", "") if strategy_data else "")

        self.sl_mode_diff = QRadioButton("Diff")
        self.sl_mode_abs = QRadioButton("Abs")
        self.sl_mode_group = QButtonGroup(self)
        self.sl_mode_group.addButton(self.sl_mode_diff)
        self.sl_mode_group.addButton(self.sl_mode_abs)
        self.sl_mode_diff.setChecked(True)
        sl_mode_box = QHBoxLayout()
        sl_mode_box.addWidget(self.sl_mode_diff)
        sl_mode_box.addWidget(self.sl_mode_abs)
        sl_tp_layout.addWidget(self.enable_sl_chk)
        sl_tp_layout.addLayout(sl_mode_box)
        sl_tp_layout.addWidget(self.sl_edit)

        self.sl_edit.setEnabled(bool(strategy_data and strategy_data.get("SL", "")))
        self.enable_sl_chk.setChecked(bool(strategy_data and strategy_data.get("SL", "")))
        self.enable_sl_chk.stateChanged.connect(lambda checked: self.sl_edit.setEnabled(bool(checked)))
        
        sl_tp_layout.addSpacing(20)

        self.enable_tp_chk = QCheckBox("Enable TP")
        self.tp_edit = QLineEdit(strategy_data.get("TP", "") if strategy_data else "")

        self.tp_mode_diff = QRadioButton("Diff")
        self.tp_mode_abs = QRadioButton("Abs")
        self.tp_mode_group = QButtonGroup(self)
        self.tp_mode_group.addButton(self.tp_mode_diff)
        self.tp_mode_group.addButton(self.tp_mode_abs)
        self.tp_mode_diff.setChecked(True)
        tp_mode_box = QHBoxLayout()
        tp_mode_box.addWidget(self.tp_mode_diff)
        tp_mode_box.addWidget(self.tp_mode_abs)
        sl_tp_layout.addWidget(self.enable_tp_chk)
        sl_tp_layout.addLayout(tp_mode_box)
        sl_tp_layout.addWidget(self.tp_edit)


        self.tp_edit.setEnabled(bool(strategy_data and strategy_data.get("TP", "")))
        self.enable_tp_chk.setChecked(bool(strategy_data and strategy_data.get("TP", "")))
        self.enable_tp_chk.stateChanged.connect(lambda checked: self.tp_edit.setEnabled(bool(checked)))

        main_layout.addLayout(sl_tp_layout)

        # 5. OK/Cancel Buttons
        btns = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.cancel_btn = QPushButton("Cancel")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        btns.addWidget(self.ok_btn)
        btns.addWidget(self.cancel_btn)
        main_layout.addLayout(btns)

        # --- Add legs from strategy_data or by default 2 legs
        if strategy_data:
            n = 0
            # FIX: Check for Token existence, not just any key
            while strategy_data.get(f"Token{n+1}"):
                n += 1
            if n == 0: # Handle case where strategy exists but has no legs
                 self.add_leg()
                 self.add_leg()
            else:
                for i in range(n):
                    token_str = strategy_data.get(f"Token{i+1}", "")
                    side      = strategy_data.get(f"Side{i+1}", "BUY")
                    lots_val  = int(strategy_data.get(f"Lots{i+1}", "1"))
                    if token_str:
                        parts = token_str.split()
                        if len(parts) == 4:
                            u, e, t, s = parts
                            self.add_leg((u, e, t, s, side_val, lots_val))
        else:
            self.add_leg()
            self.add_leg()

        # -- Tab order setup --
        leg_fields = []
        for leg in self.leg_widgets:
            _, ucb, ecb, strike_cb, tcb, scb, lots_spin, *_ = leg
            leg_fields.extend([ucb, ecb, strike_cb, tcb, scb, lots_spin])
        widgets_in_order = (
            leg_fields
            + [self.add_leg_btn, self.diff_edit, self.name_edit, self.sl_edit, self.tp_edit, self.ok_btn, self.cancel_btn]
        )
        # FIX: Filter out None in case some widgets aren't present
        widgets_in_order = [w for w in widgets_in_order if w is not None]
        for w1, w2 in zip(widgets_in_order, widgets_in_order[1:]):
            self.setTabOrder(w1, w2)

        self.diff_edit.textChanged.connect(self.validate_all)
        self.name_edit.textChanged.connect(self.validate_all)
        self.sl_edit.textChanged.connect(self.validate_all)
        self.tp_edit.textChanged.connect(self.validate_all)
        self.enable_sl_chk.stateChanged.connect(self.validate_all)
        self.enable_tp_chk.stateChanged.connect(self.validate_all)
        self.sl_mode_diff.toggled.connect(self.validate_all)
        self.sl_mode_abs.toggled.connect(self.validate_all)
        self.tp_mode_diff.toggled.connect(self.validate_all)
        self.tp_mode_abs.toggled.connect(self.validate_all)
        
        # Call setup_leg_signals *after* all legs are added
        self.setup_leg_signals() 
        self.update_leg_prices_and_diff()
        
        self.live_update_timer = QTimer(self)
        self.live_update_timer.timeout.connect(self.update_leg_prices_and_diff)
        # FIX: Changed timer from 10ms (100x/sec) to 1000ms (1x/sec) to prevent API spam
        self.live_update_timer.start(1000)  


        # Prevent Enter from doing anything in input fields
        for field in [self.name_edit, self.diff_edit, self.sl_edit, self.tp_edit]:
            field.setFocusPolicy(Qt.StrongFocus)
            try:
                field.returnPressed.connect(lambda: None)
            except Exception:
                pass

        QTimer.singleShot(0, self.validate_all)
        QTimer.singleShot(0, self.update_live_diff)
    
   


    def showEvent(self, event):
        super().showEvent(event)
        self.update_live_diff()

    def add_leg(self, leg_data=None):

        if len(self.leg_widgets) >= 8:
            return

        ucb = QComboBox()
        ucb.addItems(self.underlyings)
        ecb = QComboBox(); ecb.setEditable(True)
        tcb = QComboBox(); tcb.addItems(["CE", "PE"])
        scb = QComboBox(); scb.addItems(["BUY", "SELL"])
        lots_spin = QSpinBox(); lots_spin.setMinimum(1)
        lots_spin.setMaximum(1000000)
        strike_cb = StrikeComboBox()
        price_lbl = QLabel("Price: --")
        lot_lbl   = QLabel("Lot size: --")
        total_qty_lbl = QLabel("Total Qty: --")
        rm = QPushButton("Remove")
        hl = QHBoxLayout()
        hl.addWidget(QLabel("Underlying:")); hl.addWidget(ucb)
        hl.addWidget(QLabel("Expiry:"));     hl.addWidget(ecb)
        hl.addWidget(QLabel("Strike:"));     hl.addWidget(strike_cb)
        hl.addWidget(QLabel("Type:"));       hl.addWidget(tcb)
        hl.addWidget(QLabel("Side:"));       hl.addWidget(scb)
        hl.addWidget(QLabel("Lots:"));       hl.addWidget(lots_spin)
        hl.addWidget(rm)
        hl.addWidget(price_lbl)
        hl.addWidget(lot_lbl)
        hl.addWidget(total_qty_lbl)

        def expiry_key(ds):
            for fmt in ("%d-%b-%Y", "%d-%b-%y"):
                try:
                    return datetime.strptime(ds, fmt)
                except ValueError:
                    continue
            return datetime.max

        def refresh_expiries():
            code = ucb.currentText().strip().upper()
            expiry_list = get_valid_expiries(code)
            expiry_list = sorted(expiry_list, key=expiry_key)
            ecb.blockSignals(True)
            ecb.clear()
            ecb.addItem("--SELECT--")
            ecb.addItems(expiry_list)
            ecb.blockSignals(False)

        def refresh_strikes():
            code = ucb.currentText().strip().upper()
            expiry = ecb.currentText().strip().upper()
            opt_type = tcb.currentText().strip().upper()
            current_strike = strike_cb.currentText().strip()
            strike_list = get_valid_strikes(code, expiry, opt_type)
            strike_list = sorted(strike_list, key=lambda x: float(x) if x.replace('.', '', 1).isdigit() else float('inf'))
            strike_cb.blockSignals(True)
            strike_cb.clear()
            strike_cb.addItem("--SELECT--")
            strike_cb.addItems(strike_list)
            if current_strike and current_strike not in ("--SELECT--", "0"):
                if current_strike in strike_list:
                    strike_cb.setCurrentText(current_strike)
                else:
                    strike_cb.setEditText(current_strike)
            elif len(strike_list) > 0:
                # FIX: Don't just select first, try to find a reasonable default or keep '--SELECT--'
                strike_cb.setCurrentIndex(0) # Default to --SELECT--
            strike_cb.blockSignals(False)

        def update_price_lot():
            underlying = ucb.currentText().strip().upper()
            expiry = ecb.currentText().strip().upper()
            opt_type = tcb.currentText().strip().upper()
            strike = strike_cb.currentText().strip()
            if (
                underlying in ("", "--SELECT--") or
                expiry in ("", "--SELECT--") or
                opt_type in ("", "--SELECT--") or
                strike in ("--SELECT--", "0", "")
            ):
                price_lbl.setText("Price: --")
                lot_lbl.setText("Lot size: --")
                total_qty_lbl.setText("Total Qty: --")
                return
            tok = f"{underlying} {expiry} {opt_type} {strike}"
            ltp = get_ltp(tok)
            lot = get_lot_size(tok)
            lots_val = lots_spin.value()
            price_lbl.setText(f"Price: ₹{ltp:.2f}" if ltp else "Price: --")
            lot_lbl.setText(f"Lot size: {lot}" if lot else "Lot size: --")
            if lot and lots_val:
                total_qty_lbl.setText(f"Total Qty: {int(lot) * lots_val}")
            else:
                total_qty_lbl.setText("Total Qty: --")

        ucb.currentTextChanged.connect(lambda: (refresh_expiries(), refresh_strikes(), update_price_lot(), self.update_live_diff()))
        ecb.currentTextChanged.connect(lambda: (refresh_strikes(), update_price_lot(), self.update_live_diff()))
        tcb.currentTextChanged.connect(lambda: (refresh_strikes(), update_price_lot(), self.update_live_diff()))
        strike_cb.currentTextChanged.connect(lambda: (update_price_lot(), self.update_live_diff()))
        ucb.currentTextChanged.connect(self.validate_all)
        ecb.currentTextChanged.connect(self.validate_all)
        tcb.currentTextChanged.connect(self.validate_all)
        strike_cb.currentTextChanged.connect(self.validate_all)
        scb.currentTextChanged.connect(self.validate_all)
        scb.currentTextChanged.connect(self.update_live_diff)
        lots_spin.valueChanged.connect(self.validate_all)
        lots_spin.valueChanged.connect(update_price_lot)
        lots_spin.valueChanged.connect(self.update_live_diff)
        rm.clicked.connect(self.validate_all)
        rm.clicked.connect(lambda _, layout=hl: self.remove_leg(layout))
        rm.clicked.connect(self.update_live_diff)

        self.legs_layout.addLayout(hl)
        self.leg_widgets.append((hl, ucb, ecb, strike_cb, tcb, scb, lots_spin, price_lbl, lot_lbl, total_qty_lbl))

        if leg_data:
            u, e, t, s, side_val, lots_val = leg_data
            idx = ucb.findText(u)
            if idx >= 0:
                ucb.setCurrentIndex(idx)
            if e in [ecb.itemText(i) for i in range(ecb.count())]:
                ecb.setCurrentText(e)
            else:
                ecb.insertItem(0, e)
                ecb.setCurrentIndex(0)
            tcb.setCurrentText(t)
            scb.setCurrentText(side_val)
            lots_spin.setValue(int(lots_val))
            if s in [strike_cb.itemText(i) for i in range(strike_cb.count())]:
                strike_cb.setCurrentText(s)
            else:
                strike_cb.setEditText(s)
            update_price_lot()
        else:
            refresh_expiries()
            # refresh_strikes() # This is called by refresh_expiries
            update_price_lot()

        if self.edit_mode:
            ucb.setEnabled(False)
            ecb.setEnabled(False)
            strike_cb.setEnabled(False)
            tcb.setEnabled(False)
            scb.setEnabled(False)
            lots_spin.setEnabled(True)
            self.name_edit.setReadOnly(True)
            self.add_leg_btn.setEnabled(False)
            self.add_leg_btn.hide()  
            rm.setEnabled(False)
            rm.hide()

        self.validate_all()
        self.update_live_diff()


    def remove_leg(self, hlayout):
        if len(self.leg_widgets) <= 2:
            return
        for entry in self.leg_widgets:
            hl, *_ = entry
            if hl == hlayout:
                for i in reversed(range(hl.count())):
                    w = hl.itemAt(i).widget()
                    if w:
                        w.setParent(None)
                self.legs_layout.removeItem(hl)
                self.leg_widgets.remove(entry)
                break
        self.validate_all()
        self.update_live_diff()

    def validate_all(self):
        try:
            if not self.name_edit.text().strip():
                raise ValueError("Name is empty")
            try:
                float(self.diff_edit.text().strip())
            except ValueError:
                raise ValueError("Diff must be a number")
            for (hl, ucb, ecb, strike_cb, tcb, scb, lots_spin, price_lbl, lot_lbl, total_qty_lbl) in self.leg_widgets:
                txt = strike_cb.currentText().strip()
                if txt in ("--SELECT--", "", "0"):
                    raise ValueError("Strike must be selected")
                try:
                    float(txt)
                except ValueError:
                    raise ValueError("Strike must be a number")
                if lots_spin.value() < 1:
                    raise ValueError("Lots must be at least 1")
                if tcb.currentText() not in ("CE", "PE"):
                    raise ValueError("Invalid option type (must be CE/PE)")
                if scb.currentText() not in ("BUY", "SELL"):
                    raise ValueError("Invalid side (must be BUY/SELL)")
            # --- Only validate SL/TP if the box is checked ---
            if self.enable_sl_chk.isChecked():
                txt = self.sl_edit.text().strip()
                if not txt:
                    raise ValueError("SL required if enabled")
                if txt.endswith('%'):
                    float(txt[:-1])
                else:
                    float(txt)
            if self.enable_tp_chk.isChecked():
                txt = self.tp_edit.text().strip()
                if not txt:
                    raise ValueError("TP required if enabled")
                if txt.endswith('%'):
                    float(txt[:-1])
                else:
                    float(txt)
            self.ok_btn.setEnabled(True)
        except Exception:
            self.ok_btn.setEnabled(False)
        
    def save_strategies_to_file(self):
        save_strategies(self.strategy_list)

    def update_live_diff(self):
            try:
                legs = []
                prices = []
                lot_sizes = []
                
                for (_, ucb, ecb, strike_cb, tcb, scb, lots_spin, *_ ) in self.leg_widgets:
                    # 1. Get leg info
                    legs.append({'side': scb.currentText(), 'lots': lots_spin.value()})
                    
                    # 2. Get price
                    token_str = f"{ucb.currentText()} {ecb.currentText()} {tcb.currentText()} {strike_cb.currentText()}"
                    ltp = get_ltp(token_str)
                    prices.append(ltp if ltp else None)
                    
                    # 3. Get lot size
                    lot = get_lot_size(token_str)
                    lot_sizes.append(int(lot) if lot else None)

                # Calculate diff using the CORRECT executor logic
                diff = calculate_per_ratio_diff(legs, prices, lot_sizes)
                self.live_diff_label.setText(f"Current Diff: {diff:.2f}")

            except Exception:
                self.live_diff_label.setText("Current Diff: --")

    def make_token(underlying, expiry, opt_type, strike):
        return f"{underlying} {expiry} {opt_type} {strike}".strip().upper()

    def accept(self):
            self.validate_all()
            if not self.ok_btn.isEnabled():
                return

            # --- START: NEW WARNING LOGIC ---
            try:
                # 1. Get user's threshold
                entered_threshold = float(self.diff_edit.text().strip())

                # 2. Get current live diff (re-using logic from update_live_diff)
                legs = []
                prices = []
                lot_sizes = []
                
                for (_, ucb, ecb, strike_cb, tcb, scb, lots_spin, *_ ) in self.leg_widgets:
                    legs.append({'side': scb.currentText(), 'lots': lots_spin.value()})
                    token_str = f"{ucb.currentText()} {ecb.currentText()} {tcb.currentText()} {strike_cb.currentText()}"
                    ltp = get_ltp(token_str)
                    prices.append(ltp if ltp else None)
                    lot = get_lot_size(token_str)
                    lot_sizes.append(int(lot) if lot else None)

                # Calculate diff using the executor's logic
                diff_result = calculate_per_ratio_diff(legs, prices, lot_sizes)
                
                live_diff = None
                if isinstance(diff_result, (tuple, list)):
                    live_diff = diff_result[0] # Get the first element if it's a tuple/list
                elif isinstance(diff_result, (int, float)):
                    live_diff = diff_result # Use it directly if it's a number
                
                # 3. Compare and show warning
                # Check live_diff is not None (in case of error) and the user's condition
                if live_diff is not None and entered_threshold < live_diff:
                    reply = QMessageBox.question(self, "Confirmation",
                                                f"Warning: The threshold ({entered_threshold:.2f}) is less than the current difference ({live_diff:.2f}).\n"
                                                "This may trigger an immediate trade.\n\nDo you want to continue?",
                                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) # Default to 'No'

                    if reply == QMessageBox.No:
                        return # Abort accept(), user stays in dialog to edit

            except Exception as e:
                # If anything fails (e.g., getting live diff), just log it and proceed without the check
                print(f"Could not perform pre-trade warning check: {e}")
            # --- END: NEW WARNING LOGIC ---

            def make_token(underlying, expiry, opt_type, strike):
                return f"{underlying} {expiry} {opt_type} {strike}".strip().upper()
            for idx, (_, ucb, ecb, strike_cb, tcb, scb, lots_spin, price_lbl, lot_lbl, total_qty_lbl) in enumerate(self.leg_widgets, start=1):
                token = make_token(ucb.currentText(), ecb.currentText(), tcb.currentText(), strike_cb.currentText())
                row = self.scrip_df[self.scrip_df["scripname"].str.upper() == token]

                if row.empty:
                    QMessageBox.warning(self, "Order Size Error", f"Leg {idx}: {token} not found in scripmaster.")
                    return
                maxqty = int(row['maxqtyperorder'].values[0])
                lot_size = int(row['marketlot'].values[0])
                entered_lots = lots_spin.value()
                entered_qty = entered_lots * lot_size
                if entered_qty > maxqty:
                    QMessageBox.warning(
                        self,
                        "Order Size Error",
                        f"Leg {idx}: Entered quantity ({entered_qty}) exceeds max allowed per order ({maxqty}) for {token}."
                    )
                    return

            super().accept()
            
    def closeEvent(self, event):
        self.live_update_timer.stop()
        super().closeEvent(event)

    def get_strategy_data(self):
        data = {
            "Strategy Name": self.name_edit.text().strip(),
            "Diff Threshold": self.diff_edit.text().strip(),
            "SL": self.sl_edit.text().strip() if self.enable_sl_chk.isChecked() else "",
            "TP": self.tp_edit.text().strip() if self.enable_tp_chk.isChecked() else "",
            "SL_Mode": "abs" if self.sl_mode_abs.isChecked() else "diff",
            "TP_Mode": "abs" if self.tp_mode_abs.isChecked() else "diff"
        }
        for idx, (_, ucb, ecb, strike_cb, tcb, scb, lots_spin, price_lbl, lot_lbl, total_qty_lbl) in enumerate(self.leg_widgets, start=1):
            token_str = f"{ucb.currentText()} {ecb.currentText()} {tcb.currentText()} {strike_cb.currentText()}"
            data[f"Token{idx}"] = token_str
            data[f"Side{idx}"]  = scb.currentText()
            data[f"Lots{idx}"]  = str(lots_spin.value())
        return data

    def setup_leg_signals(self):
        for _, ucb, ecb, strike_cb, tcb, scb, lots_spin, price_lbl, lot_lbl, total_qty_lbl in self.leg_widgets:
            ucb.currentTextChanged.connect(self.update_leg_prices_and_diff)
            ecb.currentTextChanged.connect(self.update_leg_prices_and_diff)
            tcb.currentTextChanged.connect(self.update_leg_prices_and_diff)
            strike_cb.currentTextChanged.connect(self.update_leg_prices_and_diff)
            scb.currentTextChanged.connect(self.update_leg_prices_and_diff)
            lots_spin.valueChanged.connect(self.update_leg_prices_and_diff)

    def update_leg_prices_and_diff(self):
        prices = []
        legs_info = []
        lot_sizes_info = []

        for idx, (_, ucb, ecb, strike_cb, tcb, scb, lots_spin, price_lbl, lot_lbl, total_qty_lbl) in enumerate(self.leg_widgets):
            scripshortname = ucb.currentText().strip().upper()
            expirydate = ecb.currentText().strip().upper()
            optiontype = tcb.currentText().strip().upper()
            strikeprice = strike_cb.currentText().strip()
            
            if (
                not scripshortname or scripshortname == "--SELECT--" or
                not expirydate or expirydate == "--SELECT--" or
                not optiontype or optiontype == "--SELECT--" or
                not strikeprice or strikeprice in ("--SELECT--", "0", "")
            ):
                price_lbl.setText("Price: --")
                lot_lbl.setText("Lot size: --")
                total_qty_lbl.setText("Total Qty: --")
                prices.append(None)
                legs_info.append(None)
                lot_sizes_info.append(None)
                continue

            token = f"{scripshortname} {expirydate} {optiontype} {strikeprice}".strip().upper()
            
            # Lot size via get_lot_size
            marketlot = get_lot_size(token)
            entered_lots = lots_spin.value()

            if not marketlot or int(marketlot) <= 0:
                price_lbl.setText("Price: --")
                lot_lbl.setText("Lot size: --")
                total_qty_lbl.setText("Total Qty: --")
                prices.append(None)
                legs_info.append(None)
                lot_sizes_info.append(None)
                continue
            else:
                lot_lbl.setText(f"Lot size: {marketlot}")
                total_qty = entered_lots * int(marketlot)
                total_qty_lbl.setText(f"Total Qty: {total_qty}")

            # Price lookup
            ltp = get_ltp(token)
            if not ltp or float(ltp) <= 0:
                price_lbl.setText("Price: --")
                prices.append(None)
            else:
                price_lbl.setText(f"Price: ₹{float(ltp):.2f}")
                prices.append(float(ltp))
            
            legs_info.append({"side": scb.currentText(), "lots": entered_lots})
            lot_sizes_info.append(int(marketlot))

        # FIX: Crash fix
        # Filter out Nones before passing to helper
        valid_indices = [i for i, p in enumerate(prices) if p is not None]
        valid_legs = [legs_info[i] for i in valid_indices]
        valid_prices = [prices[i] for i in valid_indices]
        valid_lot_sizes = [lot_sizes_info[i] for i in valid_indices]

        if len(valid_legs) >= 2 and len(valid_legs) == len(valid_prices) == len(valid_lot_sizes):
            # FIX: Call helper with 3 args, expect float
            diff = calculate_per_ratio_diff(valid_legs, valid_prices, valid_lot_sizes)
            self.live_diff_label.setText(f"Current Diff: {diff:.2f}")
        else:
            self.live_diff_label.setText("Current Diff: --")


    def eventFilter(self, obj, event):
        if isinstance(obj, QLineEdit) and event.type() == QEvent.FocusIn:
            if obj.text() in ("0", "--SELECT--"):
                obj.setText("")
        return super().eventFilter(obj, event)

def is_strategy_valid(strat, valid_tokens):
    """Return True if all non-blank Token{i} are present in valid_tokens."""
    for i in range(1, 9):
        token = strat.get(f"Token{i}", "")
        if token:
            tkn = token.strip().upper()
            if tkn and tkn not in valid_tokens:
                print(f"[VALIDATE] Invalid token for Token{i}: '{tkn}'")
                return False
    return True

class MainWindow(QMainWindow):
    """
    Main application window. Contains:
     - Top row: Load CSV / Save CSV / Add / Delete / Manual Square-Off
     - Next row: Start / Stop / Start All / Stop All
     - Table with columns for strategy details including lots, order qty, traded qty
    """
    def __init__(self):
        super().__init__()
        self.user_id = config.CLIENT_CODE 
        self.setWindowTitle("Strategy Executor")
        self.setGeometry(200, 200, 1350, 700)
        self.btn_kill_switch = QPushButton("KILL SWITCH")
        self.btn_kill_switch.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        # Central widget + layout
        self.container = QWidget()
        self.setCentralWidget(self.container)
        main_layout = QVBoxLayout()
        self.container.setLayout(main_layout)

        # ... [top rows, buttons as before]
        self.btn_load = QPushButton("Load CSV")
        self.btn_save = QPushButton("Save CSV")
        self.btn_add  = QPushButton("Add Strategy")
        self.btn_delete = QPushButton("Delete Strategy")
        self.btn_manual_sqoff = QPushButton("Manual Square-Off")

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_manual_sqoff)
        btn_layout.addWidget(self.btn_kill_switch)
        main_layout.addLayout(btn_layout)

        ctrl_layout = QHBoxLayout()
        self.btn_start = QPushButton("Start")
        self.btn_stop  = QPushButton("Stop")
        self.btn_start_all = QPushButton("Start All")
        self.btn_stop_all  = QPushButton("Stop All")

        for b in (self.btn_stop, self.btn_stop_all, self.btn_delete):
            b.setStyleSheet("QPushButton:disabled {background-color:#ddd;color:#888}")

        ctrl_layout.addWidget(self.btn_start)
        ctrl_layout.addWidget(self.btn_stop)
        ctrl_layout.addWidget(self.btn_start_all)
        ctrl_layout.addWidget(self.btn_stop_all)
        
        # FIX: Add the Global Max Loss input field
        ml_layout = QHBoxLayout()
        ml_layout.addStretch()
        ml_layout.addWidget(QLabel("Global Max Loss:"))
        self.max_loss_edit = QLineEdit(str(load_max_loss()))
        self.max_loss_edit.setPlaceholderText("e.g., 5000")
        self.max_loss_edit.editingFinished.connect(lambda: save_max_loss(self.max_loss_edit.text()))
        ml_layout.addWidget(self.max_loss_edit)
        
        # Add both layouts to the main layout
        bottom_controls_layout = QHBoxLayout()
        bottom_controls_layout.addLayout(ctrl_layout)
        bottom_controls_layout.addLayout(ml_layout)
        main_layout.addLayout(bottom_controls_layout)


        # --- Updated column headers ---
        self.col_headers = [
            "S.No", "Name", "Diff", "SL", "TP", "P&L", "Current Diff"
        ]
        for i in range(1, 9):
            self.col_headers += [
                f"Token{i}", f"Side{i}", f"TotalQty{i}", f"OrderQty{i}", f"TradedQty{i}"
            ]

        # Create the table BEFORE setting headers/column counts!
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.col_headers))
        self.table.setHorizontalHeaderLabels(self.col_headers)

        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        main_layout.addWidget(self.table)

        # --- Backend connections (FIXED) ---
        # FIX 1: Create the executor *once*
        self.executor = StrategyExecutor(self.user_id, parent=self, max_loss_global=self.get_global_max_loss())
        
        # FIX 2: Connect signals to the *correct* executor instance
        self.executor.update_pnl_signal.connect(self._on_update_pnl)
        if hasattr(self.executor, "update_diff_signal"):
            print(f"[GUI] Connecting signals for executor: {self.executor}")
            self.executor.update_diff_signal.connect(self._on_update_diff)
        if hasattr(self.executor, "update_qty_signal"):
            self.executor.update_qty_signal.connect(self._on_update_qty)
        if hasattr(self.executor, "update_status_signal"):
            self.executor.update_status_signal.connect(self._on_update_status)
        
        self.manager = StrategyManager(self.executor)
        self.executor.start()

        # UI signals
        self.btn_add.clicked.connect(self.open_add_dialog)
        self.btn_delete.clicked.connect(self.delete_selected_strategy)
        self.table.cellDoubleClicked.connect(self.edit_strategy_dialog)
        self.btn_stop.clicked.connect(self.stop_selected_strategy)
        self.btn_start_all.clicked.connect(self.start_all_strategies)
        self.btn_stop_all.clicked.connect(self.stop_all_strategies)
        self.btn_manual_sqoff.clicked.connect(self.manual_square_off)
        self.table.itemSelectionChanged.connect(self._update_button_states)
        self.btn_kill_switch.clicked.connect(self.handle_kill_switch)
        self.btn_save.clicked.connect(self.save_strategies_to_file)
        self.btn_start.clicked.connect(self.start_selected_strategy)
        self.btn_stop.clicked.connect(lambda: self.manager.disable_strategy(self.get_selected_strategy_name()))
        self.btn_load.clicked.connect(self.load_csv)
        self.btn_save.clicked.connect(self.save_csv)

        self.strategy_list = load_strategies()

        for strat in self.strategy_list:
            self._add_strategy_to_table(strat)
            self.executor.add_strategy(strat)
        
        # self.executor.update_diff_signal.connect(self._on_update_diff) # Already connected
        # self.executor.update_status_signal.connect(self._on_update_status) # Already connected
        self._update_button_states()
    
    def get_all_valid_tokens(self):
        df = load_scripmaster()
        return set(df["scripname"].astype(str).str.upper().str.strip())
    
    def get_global_max_loss(self):
        val = self.max_loss_edit.text().strip()
        try:
            return float(val) if val else float('inf')
        except ValueError:
            return float('inf')

    def load_csv(self):
        print("[LOAD_CSV] ENTERED")
        path, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV Files (*.csv)")
        print(f"[LOAD_CSV] Path: {path}")

        if not path:
            return
        try:
            with open(path, newline='') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                print(f"[LOAD_CSV] Read {len(rows)} rows from CSV")

                if not rows:
                    QMessageBox.warning(self, "Load Error", "CSV file is empty!")
                    return
                self.strategy_list.clear()
                self.table.setRowCount(0)

                # Get all valid tokens from scripmaster for validation
                valid_tokens = self.get_all_valid_tokens()
                skipped = []
                print(f"[LOAD_CSV] Valid tokens: {len(valid_tokens)}")
                for strat in rows:
                    # PATCH: Robust Diff Threshold
                    if strat.get("Diff") and not strat.get("Diff Threshold"):
                        strat["Diff Threshold"] = strat["Diff"]
                    if strat.get("Diff Threshold") and not strat.get("Diff"):
                        strat["Diff"] = strat["Diff Threshold"]

                    # PATCH: Always fill Lots fields for each leg
                    for i in range(1, 9):
                        if not strat.get(f"Lots{i}"):
                            strat[f"Lots{i}"] = "1"

                    # Always fill Name for robust backend matching
                    if not strat.get("Name"):
                        strat["Name"] = strat.get("Strategy Name", "")
                    
                    if not strat.get("Strategy Name"):
                        strat["Strategy Name"] = strat.get("Name", "")
                    
                    # Validate all legs (if ANY leg invalid, reject the whole strategy)
                    # print(f"[LOAD_CSV] Checking strat: {strat}")
                    # for i in range(1, 9):
                    #     token = strat.get(f"Token{i}", "").strip().upper()
                    #     print(f"[CHECK TOKEN] Token{i}: '{token}' | Is in valid_tokens? {token in valid_tokens}")

                    if is_strategy_valid(strat, valid_tokens):
                        self.strategy_list.append(strat)
                        self._add_strategy_to_table(strat)
                        self.executor.add_strategy(strat)
                        self._update_button_states()
                        self.manager.disable_strategy(strat.get("Strategy Name", strat.get("Name", "")))
                        row = self.table.rowCount() - 1
                        self.update_serial_color(row)
                        # --- Force Current Diff/price update (safe, doesn't enable) ---
                        name = strat.get("Strategy Name", strat.get("Name", ""))
                        state = self.executor.active_strategies.get(name)
                        if state:
                            # FIX: Use executor's lock to temporarily change status for tick
                            with self.executor.state_lock:
                                old_status = state["status"]
                                state["status"] = "waiting"
                            
                            print(f"[LOAD_CSV] About to tick strategy: {strat.get('Strategy Name', strat.get('Name', ''))}")
                            self.executor._tick(state)
                            
                            with self.executor.state_lock:
                                state["status"] = old_status
                    else:
                        print(f"[LOAD_CSV] Skipped strategy: {strat}")
                        skipped.append(strat.get("Name") or strat.get("Strategy Name") or "Unknown")
                if self.table.rowCount() > 0:
                    self.table.selectRow(0)
                self._update_button_states()
                
                if skipped:
                    print(f"[POPUP] Skipped strategies: {skipped}")  # Must print
                    QMessageBox.warning(
                        self, "Invalid/Expired Strategies Skipped",
                        "The following strategies were skipped due to expired or invalid scripts:\n\n" + "\n".join(skipped)
                    )
                else:
                    print("[POPUP] Nothing skipped, no popup shown.")
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Failed to load CSV:\n{e}")


    def save_csv(self):
        if not self.strategy_list:
            QMessageBox.information(self, "Save CSV", "No strategies to save.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        try:
            with open(path, 'w', newline='') as f:
                # FIX: Use the actual headers from self.col_headers
                fieldnames = self.col_headers
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for strat in self.strategy_list:
                    # PATCH: Robust Diff Threshold
                    if strat.get("Diff Threshold"):
                        strat["Diff"] = strat["Diff Threshold"]
                    elif strat.get("Diff"):
                        strat["Diff Threshold"] = strat["Diff"]
                    else:
                        strat["Diff"] = ""
                        strat["Diff Threshold"] = ""

                    # PATCH: Always save the Lots fields for each leg
                    for i in range(1, 9):
                        if not strat.get(f"Lots{i}"):
                            try:
                                # This logic might be flawed, default to 1
                                lots_val = int(strat.get(f"TotalQty{i}", 0)) or 1
                                strat[f"Lots{i}"] = lots_val
                            except Exception:
                                strat[f"Lots{i}"] = 1

                    # Always fill the Name if missing
                    if not strat.get("Name"):
                        strat["Name"] = strat.get("Strategy Name", "")
                    # Overwrite traded qty for all legs
                    for i in range(1, 9):
                        strat[f"TradedQty{i}"] = 0
                    
                    # FIX: Map headers correctly, fill P&L, Current Diff
                    out_row = {}
                    for k in fieldnames:
                        val = strat.get(k, strat.get(self._map_csv_to_field(k), ""))
                        if k == 'P&L' or k == 'Current Diff':
                            val = "" # Don't save transient data
                        out_row[k] = val
                    
                    writer.writerow(out_row)
        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Failed to save CSV:\n{e}")

    def update_serial_color(self, row):
        try:
            name = self.table.item(row, 1).text()
            # FIX: Use lock to safely read state
            with self.executor.state_lock:
                state = self.executor.active_strategies.get(name, {})
                status = state.get("status", "disabled").lower()
                
                fully_traded = True
                at_least_one_leg = False
                
                for leg in range(1, 9):
                    total_qty = state.get(f"order_qty{leg}", 0)
                    traded_qty = state.get(f"traded_qty{leg}", 0)
                    
                    if total_qty > 0:
                        at_least_one_leg = True
                        if traded_qty < total_qty:
                            fully_traded = False
                            break # No need to check other legs
            
        except Exception as e:
            print(f"Error in update_serial_color: {e}")
            status = "disabled"
            fully_traded = False
            at_least_one_leg = False

        if status in ("sl_hit", "tp_hit", "squared_off", "disabled"):
            color = QColor("red")
        elif at_least_one_leg and fully_traded:
            color = QColor("red") # Fully traded is an "ended" state
        elif status in ("waiting", "triggered"):
            color = QColor("green")
        else:
            color = QColor("red") # Default to red for any other unknown state

        # 👉 Only color index 0 (S.No) column
        item = self.table.item(row, 0)
        if item:
            item.setBackground(QBrush(color))

        # Reset all other columns to default/white
        for col in range(1, self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                item.setBackground(QBrush(Qt.white))

    def save_strategies_to_file(self):
        save_strategies(self.strategy_list)

    def _add_strategy_to_table(self, strat: dict):
        row = self.table.rowCount()
        self.table.insertRow(row)

        # Set fixed columns (update this if you have more/less)
        self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))  # S.No
        name = strat.get("Name") or strat.get("Strategy Name") or ""
        self.table.setItem(row, 1, QTableWidgetItem(name))
        self.table.setItem(row, 2, QTableWidgetItem(str(strat.get("Diff", strat.get("Diff Threshold", "")))))
        self.table.setItem(row, 3, QTableWidgetItem(str(strat.get("SL", ""))))
        tp = strat.get("TP", "")
        tp_display = str(tp) if tp not in [None, "", "0", 0] else ""
        self.table.setItem(row, 4, QTableWidgetItem(tp_display))
        self.table.setItem(row, 5, QTableWidgetItem(str(strat.get("PnL", "0.00")))) # P&L
        self.table.setItem(row, 6, QTableWidgetItem(str(strat.get("Current Diff", "0.00")))) # Current Diff

        # Now fill up to 8 legs
        col = 7  # Start after fixed columns
        for i in range(1, 9):
            token = str(strat.get(f"Token{i}", "") or "")
            side = str(strat.get(f"Side{i}", "") or "")
            
            # Recalculate TotalQty from Lots and LotSize if possible
            lots_str = strat.get(f"Lots{i}", "0")
            total_qty_str = ""
            if token and lots_str.isdigit():
                lot_size = get_lot_size(token)
                if lot_size:
                    total_qty_str = str(int(lots_str) * lot_size)
            
            # Fallback to TotalQty if calculation fails
            if not total_qty_str:
                 total_qty_str = str(strat.get(f"TotalQty{i}", "") or "")
            
            traded_qty_str = str(strat.get(f"TradedQty{i}", "0") or "0")
            order_qty_str = ""
            try:
                tq = int(total_qty_str) if total_qty_str else 0
                tr = int(traded_qty_str) if traded_qty_str else 0
                order_qty = tq - tr
                order_qty_str = str(order_qty) if order_qty > 0 else ""
            except Exception:
                pass
            
            self.table.setItem(row, col,   QTableWidgetItem(token))
            self.table.setItem(row, col+1, QTableWidgetItem(side))
            self.table.setItem(row, col+2, QTableWidgetItem(total_qty_str)) # TotalQty
            self.table.setItem(row, col+3, QTableWidgetItem(order_qty_str)) # OrderQty (remaining)
            self.table.setItem(row, col+4, QTableWidgetItem(traded_qty_str)) # TradedQty
            col += 5
        
        self.table.selectRow(row)
        self._update_button_states()

    def open_add_dialog(self):
        dlg = AddStrategyDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            new_strat = dlg.get_strategy_data()
            self.strategy_list.append(new_strat)
            self._add_strategy_to_table(new_strat)
            self.executor.add_strategy(new_strat)
            # Ensure the newly added row is selected
            self.table.selectRow(self.table.rowCount() - 1)
            self._update_button_states()

    
    def _map_csv_to_field(self, key):
        # Map CSV headers to internal strategy dictionary keys
        mapping = {
            "S.No": "S.No",
            "Strategy Name": "Strategy Name",
            "Name": "Strategy Name",
            "Diff": "Diff",           # threshold value
            "Diff Threshold": "Diff",
            "SL": "SL",
            "TP": "TP",
            "Current Status": "Current Status",
            "Current Diff": "Current Diff",
            "P&L": "P&L",
        }

        # Leg-wise mapping
        for i in range(1, 9):
            mapping[f"Token{i}"] = f"Token{i}"
            mapping[f"Side{i}"] = f"Side{i}"
            mapping[f"TotalQty{i}"] = f"TotalQty{i}"
            mapping[f"OrderQty{i}"] = f"OrderQty{i}"
            mapping[f"TradedQty{i}"] = f"TradedQty{i}"
            # Add Lots mapping
            mapping[f"Lots{i}"] = f"Lots{i}"

        return mapping.get(key, key)
        
    def get_selected_strategy_name(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        return self.table.item(row, 1).text()


    def edit_strategy_dialog(self, row, column):
        if row < 0 or row >= len(self.strategy_list):
            return

        old_strat = self.strategy_list[row]
        old_lots = [old_strat.get(f"Lots{i}", None) for i in range(1, 10)]
        dlg = AddStrategyDialog(self, old_strat, edit_mode=True)
        if dlg.exec_() == QDialog.Accepted:
            new_strat = dlg.get_strategy_data()
            new_lots = [new_strat.get(f"Lots{i}", None) for i in range(1, 10)]

            lots_changed = (old_lots != new_lots)
            self.strategy_list[row] = new_strat

            self._update_strategy_row(row, new_strat)

            # PATCH: Use fallback if key missing
            strat_name = old_strat.get("Strategy Name") or old_strat.get("Name")
            self.executor.remove_strategy(strat_name)
            self.executor.add_strategy(new_strat)  # This sets status to "waiting" and clears entry_diff

            pnl_col = self.col_headers.index("P&L")
            self.table.setItem(row, pnl_col, QTableWidgetItem("0.00"))

            self._update_button_states()

    
    def get_row_by_strategy_name(self, name):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)  # Column 1 should be the "Name" column
            if item and item.text() == name:
                return row
        return None


    def delete_selected_strategy(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Delete", "Select a row to delete.")
            return
        strat_name = self.table.item(row, 1).text()
        del self.strategy_list[row]
        self.table.removeRow(row)
        self.executor.remove_strategy(strat_name)
        self._update_button_states()

    def start_selected_strategy(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Start", "Select a row to start.")
            return
        name = self.get_selected_strategy_name()
        self.manager.enable_strategy(name)
        self._update_button_states()

    def stop_selected_strategy(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Stop", "Select a row to stop.")
            return
        name = self.table.item(row, 1).text()
        self.manager.disable_strategy(name)
        self._update_button_states()


    def start_all_strategies(self):
        for strat in self.strategy_list:
            strat_name = strat.get("Strategy Name") or strat.get("Name")
            self.manager.enable_strategy(strat_name)
        self._update_button_states()

    def stop_all_strategies(self):
        for strat in self.strategy_list:
            strat_name = strat.get("Strategy Name") or strat.get("Name")
            self.manager.disable_strategy(strat_name)
        self._update_button_states()

    def manual_square_off(self):
        # FIX: Use lock to get snapshot
        with self.executor.state_lock:
            states_to_sqoff = [state for state in self.executor.active_strategies.values() if state["status"] == "triggered"]
        
        for state in states_to_sqoff:
            self.executor.square_off(state) # This will update status internally
            row = self.get_row_by_strategy_name(state["strategy"]["Strategy Name"])
            if row is not None:
                self.update_serial_color(row)

        self._update_button_states()

    def _on_update_pnl(self, strat_name: str, pnl: float):
        row = self.get_row_by_strategy_name(strat_name)
        if row is not None:
            self.table.setItem(row, 5, QTableWidgetItem(f"{pnl:.2f}"))


    def _on_update_status(self, name, status):
        row = self.get_row_by_strategy_name(name)
        if row is not None:
            self.update_serial_color(row)
            
            # FIX: Use lock to safely read strategy list
            # This might be slow, but safer.
            # A better fix is to have a self.strategy_map[name] -> strat_dict
            strat = next((s for s in self.strategy_list if s.get("Strategy Name") == name), None)
            
            if strat:
                tp = strat.get("TP")
                sl = strat.get("SL")
                tp_col_index = 4  # Your actual TP column index
                sl_col_index = 3  # Your actual SL column index
                self.table.setItem(row, tp_col_index, QTableWidgetItem(str(tp) if tp not in ["", None, 0, "0"] else ""))
                self.table.setItem(row, sl_col_index, QTableWidgetItem(str(sl) if sl else ""))


    def _on_update_diff(self, strat_name, diff):
        row = self.get_row_by_strategy_name(strat_name)
        if row is not None:
            # print(f"[DIFF] strat={strat_name}, diff={diff}")
            try:
                self.table.setItem(row, 6, QTableWidgetItem(f"{float(diff):.2f}"))
            except Exception:
                pass


    def _on_update_qty(self, strat_name, qty_list):
        """
        qty_list is expected as a list of tuples:
        [(total_qty1, traded_qty1), (total_qty2, traded_qty2), ...]
        """
        row = self.get_row_by_strategy_name(strat_name)
        if row is not None:
            for idx in range(8):  # Always 8 legs
                if idx < len(qty_list):
                    total_qty, traded_qty = qty_list[idx]
                    order_qty = total_qty - traded_qty
                    total_qty_str = str(total_qty)
                    order_qty_str = str(order_qty) if order_qty > 0 else ""
                    traded_qty_str = str(traded_qty)
                else:
                    total_qty_str = order_qty_str = traded_qty_str = ""
                base_col = 7 + idx*5
                self.table.setItem(r, base_col+2, QTableWidgetItem(total_qty_str)) # TotalQty
                self.table.setItem(r, base_col+3, QTableWidgetItem(order_qty_str)) # OrderQty
                self.table.setItem(r, base_col+4, QTableWidgetItem(traded_qty_str)) # TradedQty
            self.update_serial_color(row)


    def _update_button_states(self):
        any_strat = bool(self.strategy_list)
        sel_row = self.table.currentRow()
        sel_valid = (0 <= sel_row < self.table.rowCount())
        self.btn_save.setEnabled(any_strat)
        self.btn_load.setEnabled(True)
        self.btn_delete.setEnabled(sel_valid)
        self.btn_manual_sqoff.setEnabled(any_strat) # Can sqoff all

        # FIX: Use lock to safely check states
        with self.executor.state_lock:
            # Start button: enabled if selected row is not enabled
            if sel_valid:
                name = self.table.item(sel_row, 1).text()
                state = self.executor.active_strategies.get(name)
                if state:
                    st = state.get("status", "disabled")
                    self.btn_start.setEnabled(st in ("disabled", "sl_hit", "tp_hit", "squared_off"))
                    self.btn_stop.setEnabled(st in ("enabled", "waiting", "triggered"))
                else:
                    self.btn_start.setEnabled(True)
                    self.btn_stop.setEnabled(False)
            else:
                self.btn_start.setEnabled(False)
                self.btn_stop.setEnabled(False)

            # Start All: enabled if any is not enabled
            any_not_enabled = any(
                s.get("status", "disabled") in ("disabled", "sl_hit", "tp_hit", "squared_off")
                for s in self.executor.active_strategies.values()
            )
            self.btn_start_all.setEnabled(any_not_enabled)

            # Stop All: enabled if any is enabled or waiting
            any_enabled = any(
                s.get("status", "disabled") in ("enabled", "waiting", "triggered")
                for s in self.executor.active_strategies.values()
            )
            self.btn_stop_all.setEnabled(any_enabled)

    def _update_strategy_row(self, row, strat):
        # Update fixed columns
        self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))  # S.No
        name = strat.get("Name") or strat.get("Strategy Name") or ""
        self.table.setItem(row, 1, QTableWidgetItem(name))
        self.table.setItem(row, 2, QTableWidgetItem(str(strat.get("Diff", strat.get("Diff Threshold", "")))))
        self.table.setItem(row, 3, QTableWidgetItem(str(strat.get("SL", ""))))
        self.table.setItem(row, 4, QTableWidgetItem(str(strat.get("TP", ""))))
        self.table.setItem(row, 5, QTableWidgetItem(str(strat.get("PnL", "0.00"))))
        self.table.setItem(row, 6, QTableWidgetItem(str(strat.get("Current Diff", "0.00"))))
        
        # Now fill up to 8 legs 
        col = 7
        for i in range(1, 9):
            token = str(strat.get(f"Token{i}", "") or "")
            side = str(strat.get(f"Side{i}", "") or "")
            
            # Recalculate TotalQty
            lots_str = strat.get(f"Lots{i}", "0")
            total_qty_str = ""
            if token and lots_str.isdigit():
                lot_size = get_lot_size(token)
                if lot_size:
                    total_qty_str = str(int(lots_str) * lot_size)
            
            if not total_qty_str:
                 total_qty_str = str(strat.get(f"TotalQty{i}", "") or "")

            traded_qty_str = str(strat.get(f"TradedQty{i}", "0") or "0")
            order_qty_str = ""
            try:
                tq = int(total_qty_str) if total_qty_str else 0
                tr = int(traded_qty_str) if traded_qty_str else 0
                order_qty = tq - tr
                order_qty_str = str(order_qty) if order_qty > 0 else ""
            except Exception:
                pass

            self.table.setItem(row, col,   QTableWidgetItem(token))
            self.table.setItem(row, col+1, QTableWidgetItem(side))
            self.table.setItem(row, col+2, QTableWidgetItem(total_qty_str)) # TotalQty
            self.table.setItem(row, col+3, QTableWidgetItem(order_qty_str)) # OrderQty
            self.table.setItem(row, col+4, QTableWidgetItem(traded_qty_str)) # TradedQty
            col += 5

    def handle_kill_switch(self):
        confirm = QMessageBox.question(
            self, "Confirm Kill Switch",
            "Are you sure you want to immediately cancel all orders and square off all positions for ALL strategies?\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.executor.kill_switch()
            # self.btn_start.setEnabled(True) # These are set by _update_button_states
            # self.btn_start_all.setEnabled(True)
            self._update_button_states()
            QMessageBox.information(self, "Kill Switch", "All orders cancelled and all positions squared off.\nAll strategies stopped.")