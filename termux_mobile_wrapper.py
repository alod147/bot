#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Termux Mobile Wrapper for Deriv AI Pro Bot
Converts desktop bot into Android mobile application via Termux
Author: alod147
Version: 1.0.0
"""

import json
import os
import sys
import time
import threading
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from flask import Flask, render_template, request, jsonify, session
    from flask_cors import CORS
except ImportError:
    print("⚠️ Flask not installed. Install with: pip install flask flask-cors")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/termux_mobile.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Colors:
    """Color definitions for terminal output"""
    RESET = '\033[0m'
    CYAN = '\033[96m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'

class TermuxMobileWrapper:
    """
    Mobile wrapper for Deriv AI Pro Bot running on Termux/Android
    Provides web-based UI and Termux API integration
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
        """Initialize mobile wrapper"""
        self.host = host
        self.port = port
        self.debug = debug
        self.running = False
        self.app = Flask(__name__)
        self.app.secret_key = os.urandom(24)
        
        # Configuration
        self.config = {
            'api_token': '',
            'account_mode': 'demo',
            'base_stake': 0.35,
            'martingale_multiplier': 2.1,
            'max_level': 6,
            'target_profit': 10.0,
            'asset': 'R_100'
        }
        
        # Trading state
        self.state = {
            'running': False,
            'authorized': False,
            'balance': 0.0,
            'profit': 0.0,
            'wins': 0,
            'losses': 0,
            'current_trade': None
        }
        
        self._setup_routes()
        CORS(self.app)
        
        logger.info(f"{Colors.GREEN}✓ Termux Mobile Wrapper initialized{Colors.RESET}")
    
    def _setup_routes(self):
        """Setup Flask routes for mobile interface"""
        
        @self.app.route('/', methods=['GET'])
        def dashboard():
            """Main dashboard"""
            return jsonify({
                'status': 'running' if self.running else 'stopped',
                'state': self.state,
                'config': self.config
            })
        
        @self.app.route('/api/config', methods=['GET', 'POST'])
        def api_config():
            """Get/update configuration"""
            if request.method == 'POST':
                data = request.get_json()
                self.config.update(data)
                logger.info(f"Config updated: {data}")
                return jsonify({'status': 'success', 'config': self.config})
            return jsonify(self.config)
        
        @self.app.route('/api/state', methods=['GET'])
        def api_state():
            """Get current state"""
            return jsonify(self.state)
        
        @self.app.route('/api/start', methods=['POST'])
        def api_start():
            """Start bot"""
            try:
                if not self.config.get('api_token'):
                    return jsonify({'error': 'API token not configured'}), 400
                
                self.running = True
                self.state['running'] = True
                threading.Thread(target=self._run_bot, daemon=True).start()
                
                logger.info("Bot started")
                self._notify("Bot started successfully", "info")
                return jsonify({'status': 'success', 'message': 'Bot started'})
            except Exception as e:
                logger.error(f"Error starting bot: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/stop', methods=['POST'])
        def api_stop():
            """Stop bot"""
            try:
                self.running = False
                self.state['running'] = False
                logger.info("Bot stopped")
                self._notify("Bot stopped", "warning")
                return jsonify({'status': 'success', 'message': 'Bot stopped'})
            except Exception as e:
                logger.error(f"Error stopping bot: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/logs', methods=['GET'])
        def api_logs():
            """Get recent logs"""
            try:
                log_file = Path('logs/termux_mobile.log')
                if log_file.exists():
                    lines = log_file.read_text().split('\n')[-50:]
                    return jsonify({'logs': lines})
                return jsonify({'logs': []})
            except Exception as e:
                logger.error(f"Error reading logs: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/health', methods=['GET'])
        def api_health():
            """Health check"""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'uptime': time.time(),
                'bot_running': self.running
            })
    
    def _run_bot(self):
        """Run bot in background"""
        try:
            logger.info("Bot running...")
            while self.running:
                # Simulate bot operations
                self.state['balance'] = round(self.state['balance'] + 0.01, 2)
                time.sleep(5)
        except Exception as e:
            logger.error(f"Bot error: {e}")
            self._notify(f"Bot error: {e}", "error")
    
    def _notify(self, message: str, level: str = "info"):
        """Send notification via Termux"""
        try:
            # Check if running on Termux
            if os.path.exists('/data/data/com.termux/files/home'):
                cmd = f'termux-notification --title "Deriv AI" --content "{message}"'
                os.system(cmd)
            logger.info(f"[{level.upper()}] {message}")
        except Exception as e:
            logger.error(f"Notification error: {e}")
    
    def start(self):
        """Start web server"""
        try:
            logger.info(f"{Colors.CYAN}Starting Termux Mobile Wrapper on {self.host}:{self.port}{Colors.RESET}")
            self.running = True
            self.app.run(host=self.host, port=self.port, debug=self.debug, use_reloader=False)
        except Exception as e:
            logger.error(f"Error starting server: {e}")
            raise
    
    def stop(self):
        """Stop web server"""
        self.running = False
        logger.info(f"{Colors.RED}Stopping Termux Mobile Wrapper{Colors.RESET}")

def create_app():
    """Factory function to create Flask app"""
    wrapper = TermuxMobileWrapper()
    return wrapper.app, wrapper

def main():
    """Main entry point"""
    try:
        # Create logs directory
        Path('logs').mkdir(exist_ok=True)
        
        print(f"""
        {Colors.MAGENTA}╔════════════════════════════════════════╗
        ║  Deriv AI Pro - Termux Mobile Wrapper   ║
        ║  Version: 1.0.0                         ║
        ╚════════════════════════════════════════╝{Colors.RESET}
        """)
        
        wrapper = TermuxMobileWrapper(debug=False)
        
        print(f"{Colors.GREEN}✓ Server starting...{Colors.RESET}")
        print(f"{Colors.CYAN}📱 Access web interface at: http://localhost:5000{Colors.RESET}")
        print(f"{Colors.YELLOW}⚡ Termux API notifications enabled{Colors.RESET}\n")
        
        wrapper.start()
    
    except KeyboardInterrupt:
        print(f"\n{Colors.RED}✗ Shutdown requested{Colors.RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"{Colors.RED}✗ Fatal error: {e}{Colors.RESET}")
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()