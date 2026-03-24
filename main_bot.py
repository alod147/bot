import json
import time
import threading
from datetime import datetime
from tkinter import *
from tkinter import ttk, messagebox, scrolledtext

# Import our custom modules
from deriv_ai_brain import AdvancedAIBrain
from deriv_network import ProWebSocket

class Colors:
    BG_DARK = "#05050a"
    BG_CARD = "#0d0d1a"
    BG_LIGHT = "#15152b"
    PRIMARY = "#00f2ff"
    SECONDARY = "#ff0055"
    ACCENT = "#9d00ff"
    WARNING = "#ffcc00"
    TEXT = "#ffffff"
    TEXT_DIM = "#a0a0a0"
    SUCCESS = "#00ff88"
    DANGER = "#ff3366"
    GOLD = "#ffcc33"
    INFO = "#3399ff"

class DerivProApp:
    def __init__(self):
        self.root = Tk()
        self.root.title("Deriv AI Pro v15.2 - Fixed Token Input")
        self.root.geometry("1280x900")
        self.root.configure(bg=Colors.BG_DARK)
        
        self.ai = AdvancedAIBrain()
        self.ws = None
        self.state_lock = threading.Lock()
        
        # Trading State
        self.running = False
        self.authorized = False
        self.balance = 0.0  # تم إصلاح المسافة هنا
        self.total_profit = 0.0
        self.wins = self.losses = 0
        self.consecutive_losses = 0
        self.prices = []
        
        # Logic Flags
        self.is_waiting_for_result = False
        self.is_processing_trade = False
        self.active_contract_id = None
        self.last_pattern = None
        self.last_side = None
        self.current_stake = 0.0
        self.last_trade_time = 0
        
        # Martingale Settings
        self.martingale_multiplier = 2.1
        self.max_martingale_level = 6
        
        self.setup_ui()
        self.update_loop()
        self.start_watchdog()

    def setup_ui(self):
        # Header
        header = Frame(self.root, bg=Colors.BG_LIGHT, height=70)
        header.pack(fill=X)
        title_frame = Frame(header, bg=Colors.BG_LIGHT)
        title_frame.pack(side=LEFT, padx=25)
        
        Label(title_frame, text="DERIV AI PRO", bg=Colors.BG_LIGHT, 
              fg=Colors.PRIMARY, font=("Impact", 24)).pack(side=LEFT)
        Label(title_frame, text="v15.2 FIXED", bg=Colors.BG_LIGHT, 
              fg=Colors.GOLD, font=("Arial", 10, "bold")).pack(side=LEFT, padx=5, pady=(10,0))
        
        self.status_indicator = Label(header, text="● DISCONNECTED", 
                                      bg=Colors.BG_LIGHT, fg=Colors.DANGER, 
                                      font=("Arial", 10, "bold"))
        self.status_indicator.pack(side=RIGHT, padx=25)
        
        main_container = Frame(self.root, bg=Colors.BG_DARK)
        main_container.pack(fill=BOTH, expand=True, padx=15, pady=15)
        
        left_panel = Frame(main_container, bg=Colors.BG_DARK, width=340)
        left_panel.pack(side=LEFT, fill=Y, padx=(0, 10))
        
        # Account Card
        acc_card = Frame(left_panel, bg=Colors.BG_CARD, padx=15, pady=15)
        acc_card.pack(fill=X, pady=(0, 10))
        
        Label(acc_card, text="🔑 إعدادات الحساب", bg=Colors.BG_CARD, 
              fg=Colors.PRIMARY, font=("Arial", 12, "bold")).pack(anchor=W)
        
        # --- إصلاح حقل التوكن ---
        Label(acc_card, text="API Token:", bg=Colors.BG_CARD, 
              fg=Colors.TEXT_DIM, font=("Arial", 10)).pack(anchor=W, pady=(10,0))
        
        self.token_entry = Entry(acc_card, bg=Colors.BG_DARK, fg=Colors.TEXT, 
                                 borderwidth=1, relief=FLAT, insertbackground="white",
                                 font=("Consolas", 11))
        self.token_entry.pack(fill=X, pady=5)
        # ----------------------
        
        self.acc_mode = StringVar(value="demo")
        mode_frame = Frame(acc_card, bg=Colors.BG_CARD)
        mode_frame.pack(fill=X, pady=10)
        
        Radiobutton(mode_frame, text="تجريبي (Demo)", variable=self.acc_mode, 
                    value="demo", bg=Colors.BG_CARD, fg=Colors.INFO, 
                    selectcolor=Colors.BG_DARK, activebackground=Colors.BG_CARD).pack(side=LEFT)
        Radiobutton(mode_frame, text="حقيقي (Real)", variable=self.acc_mode, 
                    value="real", bg=Colors.BG_CARD, fg=Colors.SECONDARY, 
                    selectcolor=Colors.BG_DARK, activebackground=Colors.BG_CARD).pack(side=LEFT, padx=10)

        # Strategy Card
        strat_card = Frame(left_panel, bg=Colors.BG_CARD, padx=15, pady=15)
        strat_card.pack(fill=X, pady=10)
        
        Label(strat_card, text="📊 استراتيجية التداول", bg=Colors.BG_CARD, 
              fg=Colors.PRIMARY, font=("Arial", 12, "bold")).pack(anchor=W)
        
        Label(strat_card, text="الأصل المالي:", bg=Colors.BG_CARD, 
              fg=Colors.TEXT_DIM).pack(anchor=W, pady=(10,0))
        self.asset_var = StringVar(value="R_100")
        ttk.Combobox(strat_card, textvariable=self.asset_var, 
                     values=["R_10", "R_25", "R_50", "R_75", "R_100", "1HZ10V", "1HZ100V"]).pack(fill=X, pady=5)
        
        Label(strat_card, text="الرهان الأساسي ($):", bg=Colors.BG_CARD, 
              fg=Colors.TEXT_DIM).pack(anchor=W, pady=(5,0))
        self.base_stake_entry = Entry(strat_card, bg=Colors.BG_DARK, fg=Colors.TEXT, borderwidth=1, relief=FLAT)
        self.base_stake_entry.insert(0, "0.35")
        self.base_stake_entry.pack(fill=X, pady=5)
        
        # Martingale Settings
        Label(strat_card, text="⚙️ إعدادات المارتينجل", bg=Colors.BG_CARD, 
              fg=Colors.GOLD, font=("Arial", 10, "bold")).pack(anchor=W, pady=(15,0))
        
        m_grid = Frame(strat_card, bg=Colors.BG_CARD)
        m_grid.pack(fill=X, pady=5)
        
        Label(m_grid, text="نسبة المضاعفة:", bg=Colors.BG_CARD, fg=Colors.TEXT_DIM, font=("Arial", 9)).grid(row=0, column=0, sticky=W)
        self.multiplier_entry = Entry(m_grid, bg=Colors.BG_DARK, fg=Colors.TEXT, width=10, borderwidth=1, relief=FLAT)
        self.multiplier_entry.insert(0, "2.1")
        self.multiplier_entry.grid(row=0, column=1, padx=5)
        
        Label(m_grid, text="أقصى مستوى:", bg=Colors.BG_CARD, fg=Colors.TEXT_DIM, font=("Arial", 9)).grid(row=1, column=0, sticky=W, pady=(5,0))
        self.max_level_entry = Entry(m_grid, bg=Colors.BG_DARK, fg=Colors.TEXT, width=10, borderwidth=1, relief=FLAT)
        self.max_level_entry.insert(0, "6")
        self.max_level_entry.grid(row=1, column=1, padx=5, pady=(5,0))

        Label(strat_card, text="هدف الربح ($):", bg=Colors.BG_CARD, 
              fg=Colors.TEXT_DIM).pack(anchor=W, pady=(10,0))
        self.target_profit_entry = Entry(strat_card, bg=Colors.BG_DARK, fg=Colors.TEXT, borderwidth=1, relief=FLAT)
        self.target_profit_entry.insert(0, "10.0")
        self.target_profit_entry.pack(fill=X, pady=5)

        self.start_btn = Button(left_panel, text="START BOT", bg=Colors.SUCCESS, 
                                fg=Colors.BG_DARK, font=("Arial", 14, "bold"), 
                                relief=FLAT, command=self.toggle_bot)
        self.start_btn.pack(fill=X, pady=15)
        
        self.lock_status_lbl = Label(left_panel, text="🔓 النظام جاهز", 
                                     bg=Colors.BG_CARD, fg=Colors.SUCCESS, 
                                     font=("Arial", 11, "bold"), pady=10)
        self.lock_status_lbl.pack(fill=X)
        
        self.martingale_status_lbl = Label(left_panel, text="المستوى: 0 | الرهان: $0.35", 
                                           bg=Colors.BG_CARD, fg=Colors.TEXT_DIM, 
                                           font=("Consolas", 10))
        self.martingale_status_lbl.pack(fill=X, pady=(5,0))

        # Right Panel
        right_panel = Frame(main_container, bg=Colors.BG_DARK)
        right_panel.pack(side=RIGHT, fill=BOTH, expand=True)
        
        stats_row = Frame(right_panel, bg=Colors.BG_DARK)
        stats_row.pack(fill=X, pady=(0, 10))
        
        self.lbl_balance = self.create_stat_box(stats_row, "رصيد الحساب", "$0.00", Colors.INFO)
        self.lbl_profit = self.create_stat_box(stats_row, "صافي الأرباح", "$0.00", Colors.SUCCESS)
        self.lbl_wins = self.create_stat_box(stats_row, "صفقات ناجحة", "0", Colors.SUCCESS)
        self.lbl_losses = self.create_stat_box(stats_row, "صفقات خاسرة", "0", Colors.DANGER)
        
        ai_row = Frame(right_panel, bg=Colors.BG_CARD, padx=15, pady=10)
        ai_row.pack(fill=X, pady=(0, 10))
        self.lbl_ai_status = Label(ai_row, text="🧠 AI Core: Scanning...", 
                                   bg=Colors.BG_CARD, fg=Colors.GOLD, font=("Arial", 10, "bold"))
        self.lbl_ai_status.pack(side=LEFT)
        self.lbl_xp = Label(ai_row, text="XP: 0", bg=Colors.BG_CARD, fg=Colors.TEXT_DIM)
        self.lbl_xp.pack(side=RIGHT)
        
        log_frame = Frame(right_panel, bg=Colors.BG_CARD)
        log_frame.pack(fill=BOTH, expand=True)
        self.log_area = scrolledtext.ScrolledText(log_frame, bg=Colors.BG_CARD, 
                                                  fg=Colors.TEXT, font=("Consolas", 10), borderwidth=0)
        self.log_area.pack(fill=BOTH, expand=True, padx=5, pady=5)

    def create_stat_box(self, parent, title, value, color):
        box = Frame(parent, bg=Colors.BG_CARD, padx=15, pady=15)
        box.pack(side=LEFT, fill=BOTH, expand=True, padx=5)
        Label(box, text=title, bg=Colors.BG_CARD, fg=Colors.TEXT_DIM, font=("Arial", 10)).pack()
        lbl = Label(box, text=value, bg=Colors.BG_CARD, fg=color, font=("Arial", 16, "bold"))
        lbl.pack()
        return lbl

    def add_log(self, msg, color=Colors.TEXT):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.insert(END, f"[{timestamp}] {msg}\n")
        self.log_area.see(END)

    def update_martingale_display(self):
        try:
            base = float(self.base_stake_entry.get())
            mult = float(self.multiplier_entry.get())
            level = self.consecutive_losses
            next_stake = round(base * (mult ** level), 2)
            
            txt = f"المستوى الحالي: {level} | الرهان التالي: ${next_stake:.2f}"
            color = Colors.SUCCESS if level == 0 else Colors.WARNING if level < 3 else Colors.DANGER
            self.martingale_status_lbl.config(text=txt, fg=color)
        except:
            pass

    def update_loop(self):
        with self.state_lock:
            self.lbl_balance.config(text=f"${self.balance:.2f}")
            self.lbl_profit.config(text=f"${self.total_profit:+.2f}")
            self.lbl_wins.config(text=str(self.wins))
            self.lbl_losses.config(text=str(self.losses))
            self.lbl_xp.config(text=f"XP: {self.ai.memory['experience_points']}")
            status_text = "● RUNNING" if self.running else "● STOPPED"
            status_color = Colors.SUCCESS if self.running else Colors.DANGER
            self.status_indicator.config(text=status_text, fg=status_color)
        
        if self.is_processing_trade:
            self.lock_status_lbl.config(text="🔒 معالجة النتيجة...", fg=Colors.WARNING)
        elif self.is_waiting_for_result:
            self.lock_status_lbl.config(text="🔒 انتظار النتيجة...", fg=Colors.DANGER)
        else:
            self.lock_status_lbl.config(text="🔓 النظام جاهز", fg=Colors.SUCCESS)
            
        self.update_martingale_display()
        self.root.after(500, self.update_loop)

    def start_watchdog(self):
        def check():
            while True:
                if self.running and self.authorized:
                    if (self.is_waiting_for_result or self.is_processing_trade):
                        if time.time() - self.last_trade_time > 45:
                            self.add_log("⚠️ مهلة زمنية انتهت، تحرير القفل", Colors.WARNING)
                            with self.state_lock:
                                self.is_waiting_for_result = False
                                self.is_processing_trade = False
                                self.active_contract_id = None
                time.sleep(5)
        threading.Thread(target=check, daemon=True).start()

    def toggle_bot(self):
        if not self.running:
            # تنظيف التوكن من أي مسافات زائدة
            token = self.token_entry.get().strip()
            
            if not token:
                messagebox.showerror("خطأ", "يرجى إدخال API Token صحيح")
                self.token_entry.focus_set()
                return
            
            # التحقق من طول التوكن (اختياري، للتأكد من أنه ليس فارغاً)
            if len(token) < 10:
                messagebox.showwarning("تحذير", "التوكن يبدو قصيراً جداً، تأكد من نسخه بشكل صحيح.")

            try:
                self.martingale_multiplier = float(self.multiplier_entry.get())
                self.max_martingale_level = int(self.max_level_entry.get())
            except:
                self.martingale_multiplier = 2.1
                self.max_martingale_level = 6

            self.running = True
            self.start_btn.config(text="STOP BOT", bg=Colors.SECONDARY)
            self.add_log(f"🚀 جاري البدء... | Token Length: {len(token)}", Colors.INFO)
            
            threading.Thread(target=self.connect_and_auth, args=(token,), daemon=True).start()
        else:
            self.running = False
            self.start_btn.config(text="START BOT", bg=Colors.SUCCESS)
            if self.ws: 
                self.ws.close()
            self.add_log("🛑 تم إيقاف البوت", Colors.SECONDARY)

    def connect_and_auth(self, token):
        url = "wss://ws.derivws.com/websockets/v3?app_id=1089"
        self.ws = ProWebSocket(url, on_message=self.on_message, 
                               on_open=lambda ws: ws.send({"authorize": token}),
                               on_error=lambda ws, e: self.add_log(f"خطأ اتصال: {e}", Colors.DANGER))
        self.ws.connect()

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            msg_type = data.get("msg_type")
            
            if "error" in data:
                err_msg = data['error']['message']
                # تجاهل أخطاء الرهان العشرية لتجنب الإزعاج
                if "Stake can not have more than 2 decimal places" not in err_msg:
                    self.add_log(f"❌ API Error: {err_msg}", Colors.DANGER)
                
                with self.state_lock:
                    if "Stake can not have more than 2 decimal places" in err_msg:
                        self.is_waiting_for_result = False 
                        self.add_log("⚠️ تم تصحيح قيمة الرهان للمحاولة القادمة.", Colors.WARNING)
                    else:
                        self.is_waiting_for_result = False
                        self.is_processing_trade = False
                return

            if msg_type == "authorize":
                auth_data = data.get("authorize", {})
                if not auth_data:
                    self.add_log("❌ فشل التفويض: بيانات غير صحيحة", Colors.DANGER)
                    self.toggle_bot()
                    return

                with self.state_lock:
                    self.authorized = True
                    self.balance = float(auth_data.get("balance", 0))
                    account_type = auth_data.get("loginid", "Unknown")
                
                self.add_log(f"✅ تم التفويض بنجاح! الحساب: {account_type} | الرصيد: ${self.balance}", Colors.SUCCESS)
                ws.send({"ticks": self.asset_var.get(), "subscribe": 1})

            elif msg_type == "tick":
                price = float(data["tick"]["quote"])
                with self.state_lock:
                    self.prices.append(price)
                    if len(self.prices) > 50: 
                        self.prices.pop(0)
                
                if self.running and not self.is_waiting_for_result and not self.is_processing_trade:
                    threading.Thread(target=self.analyze_and_execute, daemon=True).start()

            elif msg_type == "proposal":
                if self.is_waiting_for_result and not self.active_contract_id:
                    ws.send({"buy": data["proposal"]["id"], "price": self.current_stake})

            elif msg_type == "buy":
                with self.state_lock:
                    self.active_contract_id = data["buy"]["contract_id"]
                    self.last_trade_time = time.time()
                self.add_log(f"🎯 TRADE PLACED: {self.last_side} | Stake: ${self.current_stake:.2f} | Level: {self.consecutive_losses}", Colors.INFO)
                ws.send({"proposal_open_contract": 1, "contract_id": self.active_contract_id, "subscribe": 1})

            elif msg_type == "proposal_open_contract":
                contract = data["proposal_open_contract"]
                if contract.get("is_sold"):
                    with self.state_lock:
                        if not self.is_processing_trade:
                            self.is_processing_trade = True
                            threading.Thread(target=self.process_trade_result, args=(contract,), daemon=True).start()
        except Exception as e:
            print(f"Msg error: {e}")

    def analyze_and_execute(self):
        with self.state_lock:
            if len(self.prices) < 15: return
            if self.is_waiting_for_result or self.is_processing_trade: return
            
            pattern = self.ai.get_pattern_key(self.prices)
            prediction, confidence = self.ai.predict(pattern, self.prices)
            
            if prediction == "NEUTRAL" or confidence < 0.62: return
            
            base_stake = float(self.base_stake_entry.get())
            
            if self.consecutive_losses >= self.max_martingale_level:
                self.add_log(f"⚠️ تم الوصول للحد الأقصى ({self.max_martingale_level}). إعادة تعيين.", Colors.WARNING)
                self.consecutive_losses = 0
            
            raw_stake = base_stake * (self.martingale_multiplier ** self.consecutive_losses)
            self.current_stake = round(raw_stake, 2)
            
            if self.current_stake < 0.35:
                self.current_stake = 0.35
            
            if self.current_stake > self.balance * 0.30:
                self.add_log(f"⛔ خطر: الرهان مرتفع جداً. إعادة تعيين.", Colors.DANGER)
                self.consecutive_losses = 0
                self.current_stake = round(float(self.base_stake_entry.get()), 2)
            
            self.is_waiting_for_result = True
            self.is_processing_trade = False
            self.active_contract_id = None
            self.last_pattern = pattern
            self.last_side = prediction
            self.last_trade_time = time.time()
            
            self.add_log(f"🔍 SIGNAL: {prediction} ({confidence*100:.1f}%) | Stake: ${self.current_stake:.2f} (Lvl {self.consecutive_losses})")
        
        if self.ws and self.ws.connected:
            self.ws.send({
                "proposal": 1,
                "amount": self.current_stake,
                "basis": "stake",
                "contract_type": "CALL" if prediction == "CALL" else "PUT",
                "currency": "USD",
                "duration": 5,
                "duration_unit": "t",
                "symbol": self.asset_var.get()
            })
        else:
            with self.state_lock:
                self.is_waiting_for_result = False

    def process_trade_result(self, contract):
        try:
            profit = float(contract.get("profit", 0))
            
            with self.state_lock:
                if profit > 0:
                    self.wins += 1
                    self.consecutive_losses = 0
                    msg = f"💰 WIN! +${profit:.2f} | Martingale Reset"
                    color = Colors.SUCCESS
                    self.ai.learn(self.last_pattern, "win")
                else:
                    self.losses += 1
                    self.consecutive_losses += 1
                    msg = f"📉 LOSS! ${profit:.2f} | Next Level: {self.consecutive_losses}"
                    color = Colors.DANGER
                    self.ai.learn(self.last_pattern, "loss")
                
                self.total_profit += profit
                self.balance += profit
                self.add_log(msg, color)
            
            time.sleep(1.0)
            
            with self.state_lock:
                self.active_contract_id = None
                self.is_waiting_for_result = False
                self.is_processing_trade = False
                
                target = float(self.target_profit_entry.get())
                if self.total_profit >= target:
                    self.add_log(f"🏆 TARGET REACHED (${target})", Colors.GOLD)
                    self.toggle_bot()
                    
        except Exception as e:
            self.add_log(f"❌ Error processing result: {e}", Colors.DANGER)
            with self.state_lock:
                self.is_waiting_for_result = False
                self.is_processing_trade = False
                self.active_contract_id = None

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = DerivProApp()
    app.run()