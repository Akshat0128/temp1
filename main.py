import sys
from PyQt5.QtWidgets import QApplication
from gui.app_ui import MainWindow
from utils.load_tokken import load_scripmaster
from trading.xts_market import subscribe_one_token_per_exchange

scripmaster= load_scripmaster()
subscribe_one_token_per_exchange(scripmaster)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
