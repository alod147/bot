import os
import pickle
import math

class AdvancedAIBrain:
    def __init__(self, filename="deriv_ai_core_v15_pro.pkl"):
        self.filename = filename
        self.memory = {
            "patterns": {},
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "experience_points": 0,
            "evolution_stage": 1
        }
        self.load_memory()

    def load_memory(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'rb') as f:
                    saved_data = pickle.load(f)
                    self.memory.update(saved_data)
            except: pass

    def save_memory(self):
        try:
            with open(self.filename, 'wb') as f:
                pickle.dump(self.memory, f)
        except: pass

    def get_pattern_key(self, prices, length=7):
        if len(prices) < length + 1: return None
        pattern = []
        for i in range(len(prices) - length, len(prices)):
            diff = prices[i] - prices[i-1]
            if diff > 0.0001: pattern.append("U")
            elif diff < -0.0001: pattern.append("D")
            else: pattern.append("S")
        return " ".join(pattern)

    def analyze_deeply(self, prices):
        if len(prices) < 10: return "NEUTRAL", 0.5
        mean = sum(prices[-10:]) / 10
        variance = sum((x - mean) ** 2 for x in prices[-10:]) / 10
        std_dev = math.sqrt(variance) if variance > 0 else 0.001
        trend_strength = (prices[-1] - prices[-10]) / std_dev
        
        if trend_strength > 1.2: return "CALL", min(0.9, 0.5 + abs(trend_strength)/10)
        elif trend_strength < -1.2: return "PUT", min(0.9, 0.5 + abs(trend_strength)/10)
        return "NEUTRAL", 0.5

    def predict(self, pattern, prices):
        pattern_pred = None
        pattern_conf = 0
        
        if pattern and pattern in self.memory["patterns"]:
            stats = self.memory["patterns"][pattern]
            total = stats["win"] + stats["loss"]
            if total >= 3:
                win_rate = stats["win"] / total
                if win_rate >= 0.6: pattern_pred, pattern_conf = "CALL", win_rate
                elif win_rate <= 0.4: pattern_pred, pattern_conf = "PUT", 1 - win_rate
        
        deep_pred, deep_conf = self.analyze_deeply(prices)
        
        if pattern_pred and deep_pred != "NEUTRAL":
            if pattern_pred == deep_pred: 
                return pattern_pred, (pattern_conf + deep_conf) / 2
            else: 
                return deep_pred, deep_conf * 0.8
        
        if deep_pred != "NEUTRAL": return deep_pred, deep_conf
        elif pattern_pred: return pattern_pred, pattern_conf
        return "NEUTRAL", 0.5

    def learn(self, pattern, result):
        if not pattern: return
        if pattern not in self.memory["patterns"]: 
            self.memory["patterns"][pattern] = {"win": 0, "loss": 0}
        
        if result == "win":
            self.memory["patterns"][pattern]["win"] += 1
            self.memory["wins"] += 1
            self.memory["experience_points"] += 50
        else:
            self.memory["patterns"][pattern]["loss"] += 1
            self.memory["losses"] += 1
            self.memory["experience_points"] += 20
            
        self.memory["total_trades"] += 1
        self.save_memory()