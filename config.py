# Configuration for Deriv AI Pro
DERIV_API_URL = "wss://ws.derivws.com/websockets/v3"
APP_ID = 1089

# Martingale defaults
DEFAULT_MULTIPLIER = 2.1
MAX_MARTINGALE_LEVEL = 6
BASE_STAKE = 0.35

# Security
ENABLE_ENCRYPTION = True
ENCRYPTION_KEY_ENV = "DERIV_BOT_ENC_KEY"

# Database
DATABASE_URL = "sqlite:///data/trades.db"

# Logging
LOG_DIR = "logs"
LOG_LEVEL = "DEBUG"

# Backup
BACKUP_INTERVAL_SECONDS = 3600
