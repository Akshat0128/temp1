import base64
from PyQt5.QtWidgets import QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QMessageBox
from config import ADMIN_USERNAME, ADMIN_PASSWORD_B64, TRADER_CREDENTIALS_B64

class LoginWindow(QWidget):
    def __init__(self, on_login_success):
        super().__init__()
        self.on_login_success = on_login_success
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Login")

        self.label_user = QLabel("Username:")
        self.input_user = QLineEdit()

        self.label_pass = QLabel("Password:")
        self.input_pass = QLineEdit()
        self.input_pass.setEchoMode(QLineEdit.Password)

        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.handle_login)

        layout = QVBoxLayout()
        layout.addWidget(self.label_user)
        layout.addWidget(self.input_user)
        layout.addWidget(self.label_pass)
        layout.addWidget(self.input_pass)
        layout.addWidget(self.login_button)

        self.setLayout(layout)

    def handle_login(self):
        username = self.input_user.text().strip()
        password = self.input_pass.text().strip()

        encoded_password = base64.b64encode(password.encode()).decode()

        if username == ADMIN_USERNAME and encoded_password == ADMIN_PASSWORD_B64:
            self.on_login_success("admin", username)
            self.close()
        elif username in TRADER_CREDENTIALS_B64 and encoded_password == TRADER_CREDENTIALS_B64[username]:
            self.on_login_success("trader", username)
            self.close()
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid username or password.")
