import base64
from datetime import timedelta

# ========== Motilal Oswal XTS Credentials ==========
API_KEY_MD = ""
API_SECRET_MD = ""

API_KEY_ORDER = ""
API_SECRET_ORDER = ""

CLIENT_CODE = ""
API_BASE_URL = "https://moxtsapi.motilaloswal.com:3000"

# ========== User Credentials ==========
USERNAME = "your_username"
PASSWORD = "your_password"
PASSWORD_B64 = base64.b64encode(PASSWORD.encode()).decode()

# ========== General App Config ==========
LOG_FOLDER_PATH = r""
STRATEGY_EXPIRY_HOUR = 5  # Delete unsaved strategies after 5 AM daily
STRATEGY_EXPIRY_DELTA = timedelta(days=1)
LOG_ROTATION_TIME = "midnight"  # Daily log rotation
LATENCY_THRESHOLD_MS = 200  # Max latency in ms
