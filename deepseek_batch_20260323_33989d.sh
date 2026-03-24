# أنشئ ملف السكربت وادخل المحرر (أو استخدم curl/wget لتحميله)
cat > termux_setup_and_run.sh <<'SH'
#!/data/data/com.termux/files/usr/bin/env bash
set -e

echo "=== تحديث الحزم وتثبيت الأدوات الأساسية ==="
pkg update -y && pkg upgrade -y
pkg install -y python git clang make openssl-tool

echo "=== منح صلاحية الوصول للتخزين (مرة واحدة) ==="
termux-setup-storage || true

# مجلد العمل
WORKDIR=\$HOME/bot
if [ ! -d "\$WORKDIR" ]; then
  echo "استنساخ المستودع..."
  git clone https://github.com/alod147/bot.git "\$WORKDIR"
else
  echo "المستودع موجود، تحديث..."
  cd "\$WORKDIR"
  git pull || true
fi

cd "\$WORKDIR"

echo "=== إنشاء بيئة افتراضية ==="
python -m venv venv
source venv/bin/activate

echo "=== تحديث pip و تثبيت مكتبات خفيفة ==="
pip install --upgrade pip setuptools wheel
# نثبت فقط المكتبات المطلوبة للـ headless runner (خفيفة)
pip install websocket-client requests

echo "=== إنشاء مجلدات logs و data إن لم تكن موجودة ==="
mkdir -p logs data

echo "=== إنشاء ملف headless_runner.py ==="
cat > headless_runner.py <<'PY'
#!/usr/bin/env python3
"""
Headless runner for Deriv AI Pro - Termux edition
Reads DERIV_TOKEN and optional ASSET env variables.
"""
import os
import json
import time
import threading
from datetime import datetime

# استورد مكونات المشروع من المستودع
try:
    from deriv_ai_brain import AdvancedAIBrain
    from deriv_network import ProWebSocket
except Exception as e:
    print("خطأ استيراد وحدات المشروع:", e)
    raise

DERIV_TOKEN = os.environ.get("DERIV_TOKEN") or input("أدخل DERIV_TOKEN (سيظهر على الشاشة): ").strip()
ASSET = os.environ.get("ASSET", "R_100")
BASE_STAKE = float(os.environ.get("BASE_STAKE", "0.35"))
MIN_CONFIDENCE = float(os.environ.get("MIN_CONFIDENCE", "0.62"))

LOG_FILE = os.path.join("logs", "termux_bot.log")
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\\n")
    except:
        pass

class HeadlessBot:
    def __init__(self, token, asset):
        self.token = token
        self.asset = asset
        self.ai = AdvancedAIBrain()
        self.ws = None
        self.prices = []
        self.running = False
        self.is_waiting_for_result = False
        self.is_processing_trade = False
        self.current_stake = BASE_STAKE
        self.last_trade_time = 0

    def start(self):
        url = "wss://ws.derivws.com/websockets/v3?app_id=1089"
        self.ws = ProWebSocket(
            url,
            on_message=self.on_message,
            on_open=lambda ws: ws.send({"authorize": self.token}),
            on_error=lambda ws, e: log(f"WebSocket error: {e}")
        )
        log("Connecting to Deriv WebSocket...")
        self.running = True
        threading.Thread(target=self.ws.connect, daemon=True).start()

    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()
        log("Bot stopped.")

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
        except Exception as e:
            log(f"Invalid JSON message: {e}")
            return

        if "error" in data:
            err_msg = data.get("error", {}).get("message", "")
            log(f"API Error: {err_msg}")
            return

        msg_type = data.get("msg_type")
        if msg_type == "authorize":
            auth = data.get("authorize", {})
            balance = auth.get("balance", 0)
            log(f"Authorized. Balance: {balance}")
            # subscribe to ticks
            ws.send({"ticks": self.asset, "subscribe": 1})
        elif msg_type == "tick":
            try:
                price = float(data["tick"]["quote"])
                self.prices.append(price)
                if len(self.prices) > 100:
                    self.prices.pop(0)
            except Exception as e:
                log(f"Tick parse error: {e}")
                return
            # analyze periodically
            if len(self.prices) >= 15:
                threading.Thread(target=self.analyze_and_maybe_trade, daemon=True).start()
        elif msg_type == "proposal":
            # buy step (Deriv returns proposal id)
            if self.is_waiting_for_result:
                proposal_id = data.get("proposal", {}).get("id")
                if proposal_id:
                    ws.send({"buy": proposal_id, "price": self.current_stake})
        elif msg_type == "buy":
            log("Buy response received.")
        elif msg_type == "proposal_open_contract":
            contract = data.get("proposal_open_contract", {})
            if contract.get("is_sold"):
                profit = float(contract.get("profit", 0))
                if profit > 0:
                    log(f"WIN +${profit:.2f}")
                else:
                    log(f"LOSS ${profit:.2f}")
        # else: ignore other messages

    def analyze_and_maybe_trade(self):
        if self.is_waiting_for_result or self.is_processing_trade:
            return
        try:
            pattern = self.ai.get_pattern_key(self.prices)
            prediction, confidence = self.ai.predict(pattern, self.prices)
            if prediction == "NEUTRAL" or confidence < MIN_CONFIDENCE:
                return
            self.current_stake = round(BASE_STAKE, 2)
            self.is_waiting_for_result = True
            self.last_trade_time = time.time()
            log(f"SIGNAL: {prediction} ({confidence:.2f}) | Stake: ${self.current_stake}")
            # send proposal
            if self.ws and getattr(self.ws, "connected", False):
                self.ws.send({
                    "proposal": 1,
                    "amount": self.current_stake,
                    "basis": "stake",
                    "contract_type": "CALL" if prediction == "CALL" else "PUT",
                    "currency": "USD",
                    "duration": 5,
                    "duration_unit": "t",
                    "symbol": self.asset
                })
            else:
                log("WS not connected, cannot send proposal.")
                self.is_waiting_for_result = False
        except Exception as e:
            log(f"Error in analyze_and_maybe_trade: {e}")
            self.is_waiting_for_result = False

if __name__ == '__main__':
    log("Starting headless bot...")
    bot = HeadlessBot(DERIV_TOKEN, ASSET)
    try:
        bot.start()
        # keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        bot.stop()
    except Exception as e:
        log(f"Fatal error: {e}")
PY

echo "=== تشغيل البوت في الخلفية (nohup) ==="
# شغّل في الخلفية ووجه المخرجات إلى ملف سجل
nohup bash -c "source venv/bin/activate && python headless_runner.py" > logs/runner_nohup.log 2>&1 &

echo "=== تم الإعداد والتشغيل ==="
echo "تفقد السجلات: tail -f logs/termux_bot.log"
SH

# اجعل الملف قابل للتنفيذ وشغّله
chmod +x termux_setup_and_run.sh
./termux_setup_and_run.sh