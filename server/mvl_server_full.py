#!/usr/bin/env python3
"""
Mong Vo Lam - Private Server (Full Version v2)
HTTP + ProudNet on port 2031

Chức năng:
- Serve trang login HTML (bypass Soha SDK dialog)
- Xử lý tất cả SDK endpoints
- ProudNet RMI handlers cho game logic
- SQLite database
"""

import socket
import struct
import json
import time
import os
import sqlite3

# === ONLINE PLAYER TRACKING & IDLE KICK ===
import threading
online_players = {}  # {user_id: {'username': str, 'last_active': float, 'socket': sock}}
db_lock = threading.Lock()
IDLE_TIMEOUT_SECONDS = 300  # 5 phút

def update_player_activity(user_id, username=None, socket=None):
    """Gọi khi player có hoạt động"""
    online_players[user_id] = {
        'username': username or str(user_id),
        'last_active': time.time(),
        'socket': socket
    }

def remove_player(user_id):
    """Gọi khi player disconnect"""
    online_players.pop(user_id, None)

def cleanup_idle_players():
    """Thread nền - mỗi30s kick player idle"""
    while True:
        time.sleep(30)
        try:
            now = time.time()
            for uid, info in list(online_players.items()):
                if now - info.get('last_active', 0) > IDLE_TIMEOUT_SECONDS:
                    print(f"[Server] Kick idle: {info.get('username', uid)} ({int(now-info['last_active'])}s idle)")
                    sock = info.get('socket')
                    if sock:
                        try: sock.close()
                        except: pass
                    remove_player(uid)
        except: pass

# Start cleanup thread
threading.Thread(target=cleanup_idle_players, daemon=True).start()
print("[Server] Idle kick enabled: 5min timeout, check every 30s")
import hashlib
import threading
import traceback
import random
import string
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode, quote
from io import BytesIO
from datetime import datetime, timedelta

# ============== CONFIG ==============
SERVER_IP = "0.0.0.0"
SERVER_PORT = 2031
APP_ID = "7f77e4348c5251668d2ac54eebe6f15c"
GAME_VERSION = "10.0.0"
DB_PATH = "mvl_game.db"
SERVER_NAME = "Mong Vo Lam - Private"
SERVER_PUBLIC_IP = "45.137.70.90"

GAME_SERVERS = [{
    "m_hostID": 4,
    "m_farmClientName": SERVER_NAME,
    "m_serverType": 0,
    "m_AddrPort": {"m_addr": SERVER_PUBLIC_IP, "m_port": SERVER_PORT},
    "m_CumServer": 1,
    "m_Status": 0,
    "m_GameServerID": 1
}]

GAME_CONFIG = {
    "version": GAME_VERSION,
    "androidUrl": "", "appstoreUrl": "", "jbUrl": "",
    "cfgAndroidUrl": "", "cfgAndroidCRC": 0,
    "cfgIOSUrl": "", "cfgIOSCRC": 0,
    "cfgWindowUrl": "", "cfgWindowCRC": 0,
    "cfgVer": 1, "WPUrl": "", "cfgWPUrl": "", "cfgWPCRC": 0
}

# ============== GAME DATA ==============
MON_PHAI = {
    0: {"name": "Thieu Lam", "hp": 150, "mp": 30, "attack": 12, "defense": 15, "speed": 8},
    1: {"name": "Thien Vuong", "hp": 120, "mp": 50, "attack": 15, "defense": 10, "speed": 12},
    2: {"name": "Duong Mon", "hp": 100, "mp": 80, "attack": 18, "defense": 8, "speed": 15},
    3: {"name": "Nga My", "hp": 90, "mp": 100, "attack": 10, "defense": 12, "speed": 10},
    4: {"name": "Thuy Yen", "hp": 95, "mp": 90, "attack": 14, "defense": 11, "speed": 11},
    5: {"name": "Cai Bang", "hp": 130, "mp": 40, "attack": 16, "defense": 13, "speed": 9},
    6: {"name": "Thien Nhan", "hp": 110, "mp": 60, "attack": 13, "defense": 14, "speed": 10},
    7: {"name": "Vo Dang", "hp": 105, "mp": 70, "attack": 11, "defense": 16, "speed": 9},
    8: {"name": "Con Lon", "hp": 115, "mp": 55, "attack": 17, "defense": 9, "speed": 13},
    9: {"name": "Ngu Doc", "hp": 85, "mp": 95, "attack": 20, "defense": 7, "speed": 14},
}

ITEMS_DB = {
    1: {"name": "Kiem Thuong", "type": "weapon", "class_id": -1, "level": 1, "attack": 5},
    2: {"name": "Dao Thuong", "type": "weapon", "class_id": -1, "level": 1, "attack": 4},
    3: {"name": "Ao Giap Vang", "type": "armor", "class_id": -1, "level": 1, "defense": 5},
    4: {"name": "Ao Giap Bac", "type": "armor", "class_id": -1, "level": 1, "defense": 4},
    5: {"name": "Nhan Luc", "type": "ring", "class_id": -1, "level": 1, "hp": 20},
    6: {"name": "Day Chuyen", "type": "necklace", "class_id": -1, "level": 1, "mp": 15},
    7: {"name": "Thuoc Mau", "type": "consumable", "effect": "heal", "value": 50},
    8: {"name": "Thuoc Mana", "type": "consumable", "effect": "mana", "value": 30},
    100: {"name": "Kiem Sat Thu", "type": "weapon", "class_id": 0, "level": 5, "attack": 15},
    101: {"name": "Thuong Thien Vuong", "type": "weapon", "class_id": 1, "level": 5, "attack": 18},
    200: {"name": "Ao Giap Thieu Lam", "type": "armor", "class_id": 0, "level": 5, "defense": 15},
    201: {"name": "Ao Thien Vuong", "type": "armor", "class_id": 1, "level": 5, "defense": 12},
}

SKILLS_DB = {
    1: {"name": "Kiem Quyet", "class_id": 0, "level": 1, "damage": 20, "mp_cost": 10},
    2: {"name": "La Han Chuong", "class_id": 0, "level": 3, "damage": 35, "mp_cost": 15},
    3: {"name": "Thuong Quyet", "class_id": 1, "level": 1, "damage": 25, "mp_cost": 12},
    4: {"name": "Phong Hoa Lien Hoan", "class_id": 1, "level": 5, "damage": 45, "mp_cost": 20},
    5: {"name": "An Khi Quyet", "class_id": 2, "level": 1, "damage": 30, "mp_cost": 15},
    6: {"name": "Giang Hoa", "class_id": 2, "level": 5, "damage": 50, "mp_cost": 25},
    7: {"name": "Phat Quang", "class_id": 3, "level": 1, "damage": 15, "mp_cost": 8, "heal": 30},
    8: {"name": "Tu Quang", "class_id": 3, "level": 5, "damage": 25, "mp_cost": 15, "heal": 60},
}

MAPS_DB = {
    1: {"name": "Thanh Do", "level": 1, "type": "city"},
    2: {"name": "Lang Tan Thu", "level": 1, "type": "field"},
    3: {"name": "Nui Thieu Lam", "level": 5, "type": "field"},
    4: {"name": "Rung Bach Ho", "level": 10, "type": "field"},
    5: {"name": "Thien Vuong Bang", "level": 15, "type": "field"},
}

MOBS_DB = {
    1: {"name": "Cho Soi", "level": 1, "hp": 30, "attack": 5, "defense": 2, "exp": 10, "gold": 5},
    2: {"name": "Heo Rung", "level": 2, "hp": 50, "attack": 8, "defense": 3, "exp": 15, "gold": 8},
    3: {"name": "Ca Sau", "level": 3, "hp": 80, "attack": 12, "defense": 5, "exp": 25, "gold": 12},
    4: {"name": "Ho", "level": 5, "hp": 150, "attack": 18, "defense": 8, "exp": 40, "gold": 20},
    5: {"name": "Gau", "level": 6, "hp": 200, "attack": 22, "defense": 10, "exp": 50, "gold": 25},
    6: {"name": "Bao", "level": 8, "hp": 300, "attack": 30, "defense": 15, "exp": 70, "gold": 35},
}

# ============== HTML TEMPLATES ==============
LOGIN_PAGE_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mong Vo Lam - Dang Nhap</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: 'Segoe UI', Tahoma, sans-serif;
    background: linear-gradient(135deg, #1a0a2e 0%, #16213e 50%, #0f3460 100%);
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
}
.login-container {
    background: rgba(0,0,0,0.6);
    border: 2px solid #e94560;
    border-radius: 15px;
    padding: 30px;
    width: 90%;
    max-width: 360px;
    box-shadow: 0 0 30px rgba(233,69,96,0.3);
}
.logo {
    text-align: center;
    margin-bottom: 25px;
}
.logo h1 {
    font-size: 24px;
    color: #e94560;
    text-shadow: 0 0 10px rgba(233,69,96,0.5);
}
.logo p {
    font-size: 12px;
    color: #aaa;
    margin-top: 5px;
}
.form-group {
    margin-bottom: 15px;
}
.form-group label {
    display: block;
    font-size: 13px;
    color: #ccc;
    margin-bottom: 5px;
}
.form-group input {
    width: 100%;
    padding: 12px;
    border: 1px solid #333;
    border-radius: 8px;
    background: rgba(255,255,255,0.1);
    color: #fff;
    font-size: 14px;
    outline: none;
    transition: border-color 0.3s;
}
.form-group input:focus {
    border-color: #e94560;
}
.form-group input::placeholder {
    color: #666;
}
.btn-login {
    width: 100%;
    padding: 14px;
    background: linear-gradient(135deg, #e94560, #c23152);
    border: none;
    border-radius: 8px;
    color: #fff;
    font-size: 16px;
    font-weight: bold;
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.btn-login:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 20px rgba(233,69,96,0.4);
}
.btn-login:active {
    transform: translateY(0);
}
.btn-register {
    width: 100%;
    padding: 12px;
    background: transparent;
    border: 1px solid #e94560;
    border-radius: 8px;
    color: #e94560;
    font-size: 14px;
    cursor: pointer;
    margin-top: 10px;
    transition: background 0.3s;
}
.btn-register:hover {
    background: rgba(233,69,96,0.1);
}
.error {
    color: #e94560;
    font-size: 12px;
    text-align: center;
    margin-top: 10px;
    display: none;
}
.gift-codes {
    margin-top: 20px;
    padding: 15px;
    background: rgba(255,255,255,0.05);
    border-radius: 8px;
    font-size: 11px;
    color: #888;
}
.gift-codes h3 {
    color: #e94560;
    font-size: 12px;
    margin-bottom: 8px;
}
.gift-codes code {
    color: #4ecca3;
    background: rgba(78,204,163,0.1);
    padding: 2px 6px;
    border-radius: 3px;
}
</style>
</head>
<body>
<div class="login-container">
    <div class="logo">
        <h1>⚔️ Mộng Võ Lâm</h1>
        <p>Private Server</p>
    </div>
    <form id="loginForm" onsubmit="return doLogin(event)">
        <div class="form-group">
            <label>Tài khoản</label>
            <input type="text" id="email" name="email" placeholder="Nhập tài khoản..." autocomplete="username" required>
        </div>
        <div class="form-group">
            <label>Mật khẩu</label>
            <input type="password" id="password" name="password" placeholder="Nhập mật khẩu..." autocomplete="current-password" required>
        </div>
        <button type="submit" class="btn-login" id="btnLogin">Đăng Nhập</button>
        <button type="button" class="btn-register" onclick="doRegister()">Đăng Ký Tài Khoản Mới</button>
        <div class="error" id="errorMsg"></div>
    </form>
    <div class="gift-codes">
        <h3>🎁 Gift Codes:</h3>
        <div><code>MVL2024</code> - 5000 Gold + 50 KNB</div>
        <div><code>PRIVATE</code> - 10000 Gold + 100 KNB</div>
        <div><code>WELCOME</code> - 3000 Gold + 30 KNB</div>
    </div>
</div>
<script>
function showError(msg) {
    var el = document.getElementById('errorMsg');
    el.textContent = msg;
    el.style.display = 'block';
    setTimeout(function(){ el.style.display = 'none'; }, 5000);
}

function doLogin(e) {
    e.preventDefault();
    var email = document.getElementById('email').value.trim();
    var password = document.getElementById('password').value.trim();
    if (!email) { showError('Vui lòng nhập tài khoản'); return false; }
    if (!password) { showError('Vui lòng nhập mật khẩu'); return false; }

    var btn = document.getElementById('btnLogin');
    btn.textContent = 'Đang đăng nhập...';
    btn.disabled = true;

    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/a/GET/auth/loginmobile?email=' + encodeURIComponent(email) + '&password=' + encodeURIComponent(password), true);
    xhr.onload = function() {
        try {
            var data = JSON.parse(xhr.responseText);
            if (data.status === 'success') {
                // Redirect to urilogin with token
                window.location.href = 'urilogin://success?access_token=' + encodeURIComponent(data.access_token) + '&user_id=' + encodeURIComponent(data.user_info.user_id) + '&username=' + encodeURIComponent(data.user_info.username);
            } else {
                showError(data.message || 'Đăng nhập thất bại');
                btn.textContent = 'Đăng Nhập';
                btn.disabled = false;
            }
        } catch(ex) {
            showError('Lỗi kết nối server');
            btn.textContent = 'Đăng Nhập';
            btn.disabled = false;
        }
    };
    xhr.onerror = function() {
        showError('Không kết nối được server');
        btn.textContent = 'Đăng Nhập';
        btn.disabled = false;
    };
    xhr.send();
    return false;
}

function doRegister() {
    var email = document.getElementById('email').value.trim();
    var password = document.getElementById('password').value.trim();
    if (!email) { showError('Vui lòng nhập tài khoản'); return; }
    if (!password) { showError('Vui lòng nhập mật khẩu'); return; }

    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/a/POST/auth/register', true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onload = function() {
        try {
            var data = JSON.parse(xhr.responseText);
            if (data.status === 'success') {
                showError('');
                alert('Đăng ký thành công! Đang đăng nhập...');
                doLogin(new Event('submit'));
            } else {
                showError(data.message || 'Đăng ký thất bại');
            }
        } catch(ex) {
            showError('Lỗi kết nối');
        }
    };
    xhr.onerror = function() { showError('Không kết nối được server'); };
    xhr.send(JSON.stringify({username: email, password: password, email: email}));
}
</script>
</body>
</html>"""

SUCCESS_REDIRECT_HTML = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Login Success</title></head>
<body style="background:#1a0a2e;color:#fff;font-family:sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0">
<div style="text-align:center">
<h1 style="color:#4ecca3">✅ Đăng nhập thành công!</h1>
<p style="color:#aaa;margin-top:10px">Đang vào game...</p>
<p style="color:#666;font-size:12px;margin-top:20px">Nếu game không tự động, hãy quay lại và thử lại.</p>
</div>
</body>
</html>"""

# ============== DATABASE ==============
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        email TEXT,
        access_token TEXT,
        soap_token TEXT,
        session_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP,
        gold INTEGER DEFAULT 1000,
        knb INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        exp INTEGER DEFAULT 0,
        class_id INTEGER DEFAULT -1,
        map_id INTEGER DEFAULT 1,
        pos_x REAL DEFAULT 500,
        pos_y REAL DEFAULT 500,
        hp INTEGER DEFAULT 100,
        max_hp INTEGER DEFAULT 100,
        mp INTEGER DEFAULT 50,
        max_mp INTEGER DEFAULT 50,
        attack INTEGER DEFAULT 10,
        defense INTEGER DEFAULT 5,
        speed INTEGER DEFAULT 10,
        vip_level INTEGER DEFAULT 0,
        title TEXT DEFAULT '',
        guild_id INTEGER DEFAULT 0,
        friend_list TEXT DEFAULT '[]',
        inventory TEXT DEFAULT '[]',
        equipment TEXT DEFAULT '{}',
        skills TEXT DEFAULT '[]',
        quests TEXT DEFAULT '[]',
        mail TEXT DEFAULT '[]',
        settings TEXT DEFAULT '{}'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS guilds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        leader_id INTEGER,
        level INTEGER DEFAULT 1,
        exp INTEGER DEFAULT 0,
        members TEXT DEFAULT '[]',
        notice TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel TEXT,
        sender TEXT,
        message TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def gen_token():
    return hashlib.sha256(os.urandom(32)).hexdigest()

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def get_default_player_data(account):
    class_id = account['class_id'] if account['class_id'] is not None and account['class_id'] >= 0 else 0
    mon_phai = MON_PHAI.get(class_id, MON_PHAI[0])
    level = account['level'] or 1
    return {
        "ServerTimeTick": int(time.time()*1000),
        "HostID": account['id'],
        "PlayerID": account['id'],
        "PlayerName": account['username'],
        "DisplayName": account['username'],
        "Level": level,
        "Exp": account['exp'] or 0,
        "ClassID": class_id,
        "ClassName": mon_phai['name'],
        "Gold": account['gold'] or 1000,
        "KNB": account['knb'] or 0,
        "HP": account['hp'] or mon_phai['hp'],
        "MaxHP": account['max_hp'] or mon_phai['hp'],
        "MP": account['mp'] or mon_phai['mp'],
        "MaxMP": account['max_mp'] or mon_phai['mp'],
        "Attack": account['attack'] or mon_phai['attack'],
        "Defense": account['defense'] or mon_phai['defense'],
        "Speed": account['speed'] or mon_phai['speed'],
        "MapID": account['map_id'] or 1,
        "PosX": account['pos_x'] or 500,
        "PosY": account['pos_y'] or 500,
        "VIPLevel": account['vip_level'] or 0,
        "Title": account['title'] or "",
        "GuildID": account['guild_id'] or 0,
        "FriendList": json.loads(account['friend_list'] or '[]'),
        "Inventory": json.loads(account['inventory'] or '[]'),
        "Equipment": json.loads(account['equipment'] or '{}'),
        "Skills": json.loads(account['skills'] or '[]'),
        "Quests": json.loads(account['quests'] or '[]'),
        "Mail": json.loads(account['mail'] or '[]'),
        "CostumeList": [],
        "BanBeList": json.loads(account['friend_list'] or '[]'),
        "CuuThuList": [],
        "HonNhanVatList": [],
        "HeroList": [],
        "MailList": json.loads(account['mail'] or '[]'),
        "ServerInfo": {
            "FarmServerIP": SERVER_PUBLIC_IP,
            "ServerIP": SERVER_PUBLIC_IP,
            "PublicIP": SERVER_PUBLIC_IP,
            "ServerPort": SERVER_PORT,
            "GameConn": "",
            "LoginConn": "",
            "MongoConn": "",
            "MongoDB": "mvl_game",
            "BattleTime": 300
        }
    }

def calculate_exp_for_level(level):
    return int(100 * (level ** 1.5))

def check_level_up(conn, account):
    level = account['level'] or 1
    exp = account['exp'] or 0
    leveled_up = False
    while exp >= calculate_exp_for_level(level):
        exp -= calculate_exp_for_level(level)
        level += 1
        leveled_up = True
        class_id = account['class_id'] if account['class_id'] is not None and account['class_id'] >= 0 else 0
        mon_phai = MON_PHAI.get(class_id, MON_PHAI[0])
        max_hp = (account['max_hp'] or mon_phai['hp']) + int(mon_phai['hp'] * 0.1)
        max_mp = (account['max_mp'] or mon_phai['mp']) + int(mon_phai['mp'] * 0.1)
        attack = (account['attack'] or mon_phai['attack']) + 2
        defense = (account['defense'] or mon_phai['defense']) + 1
        conn.execute("UPDATE accounts SET level=?, exp=?, max_hp=?, max_mp=?, attack=?, defense=?, hp=max_hp, mp=max_mp WHERE id=?",
                     (level, exp, max_hp, max_mp, attack, defense, account['id']))
    if not leveled_up:
        conn.execute("UPDATE accounts SET exp=? WHERE id=?", (exp, account['id']))
    return leveled_up, level

# ============== RMI HANDLERS ==============
rmi_handlers = {}

def rmi(name):
    def dec(f):
        rmi_handlers[name] = f
        return f
    return dec

@rmi("RequestFirstLogon")
def _(c, d):
    account_id = d.get("account_id", 1)
    class_id = d.get("class_id", 0)
    conn = get_db()
    acc = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
    if not acc:
        conn.close()
        return ("NotifyFirstLogonFailed", {"status": "fail"})
    mon_phai = MON_PHAI.get(class_id, MON_PHAI[0])
    starter_items = [{"id":1,"count":1,"slot":0},{"id":3,"count":1,"slot":1},{"id":7,"count":10,"slot":-1},{"id":8,"count":5,"slot":-1}]
    starter_skills = [s_id for s_id, s in SKILLS_DB.items() if s['class_id'] == class_id and s['level'] <= 1]
    conn.execute("UPDATE accounts SET class_id=?, hp=?, max_hp=?, mp=?, max_mp=?, attack=?, defense=?, speed=?, inventory=?, skills=? WHERE id=?",
                 (class_id, mon_phai['hp'], mon_phai['hp'], mon_phai['mp'], mon_phai['mp'], mon_phai['attack'], mon_phai['defense'], mon_phai['speed'], json.dumps(starter_items), json.dumps(starter_skills), account_id))
    conn.commit()
    acc = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
    conn.close()
    pd = get_default_player_data(acc)
    return ("NotifyFirstLogonSuccess", {"status": "success", "player": pd, "heroes": [pd], "serverTime": int(time.time()*1000)})

@rmi("RequestNextLogon")
def _(c, d):
    account_id = d.get("account_id", 1)
    conn = get_db()
    acc = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
    if not acc:
        conn.close()
        return ("NotifyNextLogonFailed", {"status": "fail"})
    conn.execute("UPDATE accounts SET last_login=? WHERE id=?", (time.strftime('%Y-%m-%d %H:%M:%S'), account_id))
    conn.commit()
    pd = get_default_player_data(acc)
    conn.close()
    return ("NotifyNextLogonSuccess", {"status": "success", "player": pd, "heroes": [pd], "serverTime": int(time.time()*1000)})

@rmi("RequestGetInfo")
def _(c, d):
    account_id = d.get("account_id", 1)
    conn = get_db()
    acc = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
    conn.close()
    if not acc:
        return ("NotifyGetInfoFailed", {"status": "fail"})
    return ("NotifyGetInfoSuccess", {"status": "success", "player": get_default_player_data(acc)})

@rmi("RequestSetInfo")
def _(c, d):
    return ("NotifySetInfoSuccess", {"status": "success"})

@rmi("RequestSetHeroData")
def _(c, d):
    return ("NotifySetHeroDataSuccess", {"status": "success"})

@rmi("RequestSetHeroCfg")
def _(c, d):
    return ("NotifySetHeroCfgSuccess", {"status": "success"})

@rmi("RequestChangeNextPos")
def _(c, d):
    account_id = d.get("account_id", 1)
    conn = get_db()
    conn.execute("UPDATE accounts SET pos_x=?, pos_y=?, map_id=? WHERE id=?", (d.get("x",500), d.get("y",500), d.get("map_id",1), account_id))
    conn.commit()
    conn.close()
    return ("NotifyChangeNextPosSuccess", {"status": "success"})

@rmi("RequestBanDo")
def _(c, d):
    return ("NotifyBanDoSuccess", {"status": "success", "map": MAPS_DB.get(d.get("map_id",1), MAPS_DB[1]), "players": [], "mobs": []})

@rmi("RequestGetBattleResult")
def _(c, d):
    account_id = d.get("account_id", 1)
    mob_id = d.get("mob_id", 0)
    conn = get_db()
    acc = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
    if not acc:
        conn.close()
        return ("NotifyGetBattleResultFailed", {"status": "fail"})
    mob = MOBS_DB.get(mob_id)
    if not mob:
        conn.close()
        return ("NotifyGetBattleResultSuccess", {"status": "success", "winner": 1, "rewards": []})
    player_hp = acc['hp'] or 100
    player_attack = acc['attack'] or 10
    player_defense = acc['defense'] or 5
    damage_to_mob = max(1, player_attack - mob['defense'] + random.randint(-3, 5))
    damage_to_player = max(1, mob['attack'] - player_defense + random.randint(-2, 3))
    mob_hp = mob['hp']
    rounds = 0
    while mob_hp > 0 and player_hp > 0:
        mob_hp -= damage_to_mob
        if mob_hp > 0:
            player_hp -= damage_to_player
        rounds += 1
        if rounds > 100:
            break
    winner = 1 if mob_hp <= 0 else 0
    rewards = []
    if winner == 1:
        exp_gain = mob['exp']
        gold_gain = mob['gold'] + random.randint(0, mob['gold'] // 2)
        new_exp = (acc['exp'] or 0) + exp_gain
        new_gold = (acc['gold'] or 0) + gold_gain
        conn.execute("UPDATE accounts SET exp=?, gold=?, hp=? WHERE id=?", (new_exp, new_gold, max(1, player_hp), account_id))
        leveled_up, new_level = check_level_up(conn, acc)
        conn.commit()
        rewards = [{"type": "exp", "value": exp_gain}, {"type": "gold", "value": gold_gain}]
        if leveled_up:
            rewards.append({"type": "level_up", "value": new_level})
        if random.random() < 0.1:
            drop_id = random.choice(list(ITEMS_DB.keys()))
            inventory = json.loads(acc['inventory'] or '[]')
            inventory.append({"id": drop_id, "count": 1, "slot": -1})
            conn.execute("UPDATE accounts SET inventory=? WHERE id=?", (json.dumps(inventory), account_id))
            conn.commit()
            rewards.append({"type": "item", "id": drop_id, "name": ITEMS_DB[drop_id]['name']})
    else:
        conn.execute("UPDATE accounts SET hp=? WHERE id=?", (max(1, player_hp), account_id))
        conn.commit()
    conn.close()
    return ("NotifyGetBattleResultSuccess", {"status": "success", "winner": winner, "rewards": rewards})

@rmi("RequestSetTrangBi")
def _(c, d):
    return ("NotifySetTrangBiSuccess", {"status": "success"})

@rmi("RequestBuyVatPham")
def _(c, d):
    account_id = d.get("account_id", 1)
    item_id = d.get("item_id", 0)
    count = d.get("count", 1)
    item = ITEMS_DB.get(item_id)
    if not item:
        return ("NotifyBuyVatPhamFailed", {"status": "fail", "message": "Item not found"})
    price = item.get('level', 1) * 100 * count
    conn = get_db()
    acc = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
    if not acc or (acc['gold'] or 0) < price:
        conn.close()
        return ("NotifyBuyVatPhamFailed", {"status": "fail", "message": "Not enough gold"})
    inventory = json.loads(acc['inventory'] or '[]')
    inventory.append({"id": item_id, "count": count, "slot": -1})
    conn.execute("UPDATE accounts SET gold=?, inventory=? WHERE id=?", (acc['gold'] - price, json.dumps(inventory), account_id))
    conn.commit()
    conn.close()
    return ("NotifyBuyVatPhamSuccess", {"status": "success", "gold_remaining": acc['gold'] - price})

@rmi("RequestBanTrangBi")
def _(c, d):
    return ("NotifyBanTrangBiSuccess", {"status": "success"})

@rmi("RequestCuongHoaTrangBi")
def _(c, d):
    return ("NotifyCuongHoaTrangBiSuccess", {"status": "success", "level": 1})

@rmi("RequestKhamNgoc")
def _(c, d):
    return ("NotifyKhamNgocSuccess", {"status": "success"})

@rmi("RequestGoNgoc")
def _(c, d):
    return ("NotifyGoNgocSuccess", {"status": "success"})

@rmi("RequestGhepManhTrangBi")
def _(c, d):
    return ("NotifyGhepManhTrangBiSuccess", {"status": "success"})

@rmi("RequestPhanRaTrangBi")
def _(c, d):
    return ("NotifyPhanRaTrangBiSuccess", {"status": "success"})

@rmi("RequestSetVoCong")
def _(c, d):
    account_id = d.get("account_id", 1)
    conn = get_db()
    conn.execute("UPDATE accounts SET skills=? WHERE id=?", (json.dumps(d.get("skills",[])), account_id))
    conn.commit()
    conn.close()
    return ("NotifySetVoCongSuccess", {"status": "success"})

@rmi("RequestThamNgoVoCong")
def _(c, d):
    account_id = d.get("account_id", 1)
    skill_id = d.get("skill_id", 0)
    conn = get_db()
    acc = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
    if acc:
        skills = json.loads(acc['skills'] or '[]')
        if skill_id not in skills:
            skills.append(skill_id)
            conn.execute("UPDATE accounts SET skills=? WHERE id=?", (json.dumps(skills), account_id))
            conn.commit()
    conn.close()
    return ("NotifyThamNgoVoCongSuccess", {"status": "success"})

@rmi("RequestUnLockVoCong")
def _(c, d):
    return ("NotifyUnLockVoCongSuccess", {"status": "success"})

@rmi("RequestBangHuu")
def _(c, d):
    return ("NotifyBangHuuSuccess", {"status": "success", "friends": []})

@rmi("RequestAddBanBe")
def _(c, d):
    return ("NotifyAddBanBeSuccess", {"status": "success"})

@rmi("RequestAcceptBanBe")
def _(c, d):
    return ("NotifyAcceptBanBeSuccess", {"status": "success"})

@rmi("RequestDeleteBanBe")
def _(c, d):
    return ("NotifyDeleteBanBeSuccess", {"status": "success"})

@rmi("RequestSearchBanBe")
def _(c, d):
    keyword = d.get("keyword", "")
    conn = get_db()
    players = conn.execute("SELECT id, username, level, class_id FROM accounts WHERE username LIKE ? LIMIT 20", (f"%{keyword}%",)).fetchall()
    conn.close()
    results = [{"id": p['id'], "name": p['username'], "level": p['level'], "class": p['class_id']} for p in players]
    return ("NotifySearchBanBeSuccess", {"status": "success", "results": results})

@rmi("RequestSendChatMsg")
def _(c, d):
    msg = d.get("message", "")
    sender = d.get("sender", "Player")
    channel = d.get("channel", "world")
    conn = get_db()
    conn.execute("INSERT INTO chat_log (channel, sender, message) VALUES (?, ?, ?)", (channel, sender, msg))
    conn.commit()
    conn.close()
    return ("NotifyChatMsg", {"status": "success", "message": msg, "sender": sender, "channel": channel, "timestamp": int(time.time()*1000)})

@rmi("RequestSendChatAll")
def _(c, d):
    return rmi_handlers["RequestSendChatMsg"](c, d)

@rmi("RequestSendChatLienMinh")
def _(c, d):
    d["channel"] = "alliance"
    return rmi_handlers["RequestSendChatMsg"](c, d)

@rmi("RequestSendChatLienSrv")
def _(c, d):
    return ("NotifyChatLienSrv", {"status": "success", "message": d.get("message", "")})

@rmi("RequestGetChatLienSrv")
def _(c, d):
    return ("NotifyGetChatLienSrvSuccess", {"status": "success", "messages": []})

@rmi("RequestChatInfo")
def _(c, d):
    return ("NotifyChatInfoSuccess", {"status": "success"})

@rmi("RequestChatLienMinhInfo")
def _(c, d):
    return ("NotifyChatLienMinhInfoSuccess", {"status": "success"})

@rmi("RequestRefreshMail")
def _(c, d):
    return ("NotifyRefreshMailSuccess", {"status": "success", "mails": []})

@rmi("RequestReadAllMail")
def _(c, d):
    return ("NotifyReadAllMailSuccess", {"status": "success"})

@rmi("RequestSendMail")
def _(c, d):
    return ("NotifySendMailSuccess", {"status": "success"})

@rmi("RequestUseMailPhanThuong")
def _(c, d):
    return ("NotifyUseMailPhanThuongSuccess", {"status": "success"})

@rmi("RequestLapLienMinh")
def _(c, d):
    return ("NotifyLapLienMinhSuccess", {"status": "success"})

@rmi("RequestGiaNhapLienMinh")
def _(c, d):
    return ("NotifyGiaNhapLienMinhSuccess", {"status": "success"})

@rmi("RequestGetLienMinhInfo")
def _(c, d):
    return ("NotifyGetLienMinhInfoSuccess", {"status": "success", "guild": None})

@rmi("RequestThoatLienMinh")
def _(c, d):
    return ("NotifyThoatLienMinhSuccess", {"status": "success"})

@rmi("RequestSearchLienMinh")
def _(c, d):
    return ("NotifySearchLienMinhSuccess", {"status": "success", "results": []})

@rmi("RequestGetCacLoaiTop")
def _(c, d):
    conn = get_db()
    players = conn.execute("SELECT id, username, level FROM accounts ORDER BY level DESC, exp DESC LIMIT 50").fetchall()
    conn.close()
    rankings = [{"rank": i+1, "id": p['id'], "name": p['username'], "level": p['level']} for i, p in enumerate(players)]
    return ("NotifyGetCacLoaiTopSuccess", {"status": "success", "rankings": rankings})

@rmi("RequestGetLuanKiemInfo")
def _(c, d):
    return ("NotifyGetLuanKiemInfoSuccess", {"status": "success", "rank": 0, "points": 0, "wins": 0, "losses": 0})

@rmi("RequestDauLuanKiem")
def _(c, d):
    return ("NotifyDauLuanKiemSuccess", {"status": "success"})

@rmi("RequestCapNhatDiemLuanKiem")
def _(c, d):
    return ("NotifyCapNhatDiemLuanKiemSuccess", {"status": "success"})

@rmi("RequestDoiThuongLuanKiem")
def _(c, d):
    return ("NotifyDoiThuongLuanKiemSuccess", {"status": "success"})

@rmi("RequestDangNhapNhanThuong")
def _(c, d):
    account_id = d.get("account_id", 1)
    conn = get_db()
    acc = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
    gold_reward = 500
    if acc:
        gold_reward = 500 + (acc['level'] or 1) * 100
        conn.execute("UPDATE accounts SET gold=? WHERE id=?", ((acc['gold'] or 0) + gold_reward, account_id))
        conn.commit()
    conn.close()
    return ("NotifyDangNhapNhanThuongSuccess", {"status": "success", "rewards": [{"type": "gold", "value": gold_reward}]})

@rmi("RequestDangNhapNhanThuongTet")
def _(c, d):
    return ("NotifyDangNhapNhanThuongTetSuccess", {"status": "success", "rewards": []})

@rmi("RequestGetPhanThuong")
def _(c, d):
    return ("NotifyGetPhanThuongSuccess", {"status": "success", "rewards": []})

@rmi("RequestThuongDailyActivities")
def _(c, d):
    return ("NotifyThuongDailyActivitiesSuccess", {"status": "success"})

@rmi("RequestUpdateDailyActivities")
def _(c, d):
    return ("NotifyUpdateDailyActivitiesSuccess", {"status": "success"})

@rmi("RequestSelectStartNgua")
def _(c, d):
    return ("NotifySelectStartNguaSuccess", {"status": "success"})

@rmi("RequestDungNgua")
def _(c, d):
    return ("NotifyDungNguaSuccess", {"status": "success"})

@rmi("RequestThaoNgua")
def _(c, d):
    return ("NotifyThaoNguaSuccess", {"status": "success"})

@rmi("RequestActiveNgua")
def _(c, d):
    return ("NotifyActiveNguaSuccess", {"status": "success"})

@rmi("RequestSetThanThu")
def _(c, d):
    return ("NotifySetThanThuSuccess", {"status": "success"})

@rmi("RequestBatThanThu")
def _(c, d):
    return ("NotifyBatThanThuSuccess", {"status": "success"})

@rmi("RequestDoiThanThu")
def _(c, d):
    return ("NotifyDoiThanThuSuccess", {"status": "success"})

@rmi("RequestGetThanThuDao")
def _(c, d):
    return ("NotifyGetThanThuDaoSuccess", {"status": "success"})

@rmi("RequestCreateCostume")
def _(c, d):
    return ("NotifyCreateCostumeSuccess", {"status": "success"})

@rmi("RequestTakeOnCostume")
def _(c, d):
    return ("NotifyTakeOnCostumeSuccess", {"status": "success"})

@rmi("RequestTakeOffCostume")
def _(c, d):
    return ("NotifyTakeOffCostumeSuccess", {"status": "success"})

@rmi("RequestBanPhaoHoa")
def _(c, d):
    return ("NotifyBanPhaoHoaSuccess", {"status": "success"})

@rmi("RequestQuayBacMayMan")
def _(c, d):
    rewards = random.choice([{"type":"gold","value":random.randint(100,1000)},{"type":"knb","value":random.randint(1,10)},{"type":"item","id":random.choice(list(ITEMS_DB.keys()))}])
    return ("NotifyQuayBacMayManSuccess", {"status": "success", "reward": rewards})

@rmi("RequestVongQuay")
def _(c, d):
    return ("NotifyVongQuaySuccess", {"status": "success"})

@rmi("RequestThanTai")
def _(c, d):
    return ("NotifyThanTaiSuccess", {"status": "success"})

@rmi("RequestHoaVang")
def _(c, d):
    return ("NotifyHoaVangSuccess", {"status": "success"})

@rmi("RequestGetSonMonInfo")
def _(c, d):
    return ("NotifyGetSonMonInfoSuccess", {"status": "success"})

@rmi("RequestXayDungSonMon")
def _(c, d):
    return ("NotifyXayDungSonMonSuccess", {"status": "success"})

@rmi("RequestTanCongSonMon")
def _(c, d):
    return ("NotifyTanCongSonMonSuccess", {"status": "success"})

@rmi("RequestThuHoachSonMon")
def _(c, d):
    return ("NotifyThuHoachSonMonSuccess", {"status": "success"})

@rmi("RequestGetLanhDiaInfo")
def _(c, d):
    return ("NotifyGetLanhDiaInfoSuccess", {"status": "success"})

@rmi("RequestMoveLanhDia")
def _(c, d):
    return ("NotifyMoveLanhDiaSuccess", {"status": "success"})

@rmi("RequestBangChienGetInfo")
def _(c, d):
    return ("NotifyBangChienGetInfoSuccess", {"status": "success"})

@rmi("RequestBangChienMove")
def _(c, d):
    return ("NotifyBangChienMoveSuccess", {"status": "success"})

@rmi("RequestBangChienVaoThanh")
def _(c, d):
    return ("NotifyBangChienVaoThanhSuccess", {"status": "success"})

@rmi("RequestBangChienRoiThanh")
def _(c, d):
    return ("NotifyBangChienRoiThanhSuccess", {"status": "success"})

@rmi("RequestBangChienCongThanh")
def _(c, d):
    return ("NotifyBangChienCongThanhSuccess", {"status": "success"})

@rmi("RequestHuyetChienInfo")
def _(c, d):
    return ("NotifyHuyetChienInfoSuccess", {"status": "success"})

@rmi("RequestStartHuyetChien")
def _(c, d):
    return ("NotifyStartHuyetChienSuccess", {"status": "success"})

@rmi("RequestHoiSinhHuyetChien")
def _(c, d):
    return ("NotifyHoiSinhHuyetChienSuccess", {"status": "success"})

@rmi("RequestGetSieuCupData")
def _(c, d):
    return ("NotifyGetSieuCupDataSuccess", {"status": "success"})

@rmi("RequestGetSieuCupBattle")
def _(c, d):
    return ("NotifyGetSieuCupBattleSuccess", {"status": "success"})

@rmi("RequestThamGiaCT2")
def _(c, d):
    return ("NotifyThamGiaCT2Success", {"status": "success"})

@rmi("RequestGetListCT2")
def _(c, d):
    return ("NotifyGetListCT2Success", {"status": "success", "list": []})

@rmi("RequestLayDeTu")
def _(c, d):
    return ("NotifyLayDeTuSuccess", {"status": "success"})

@rmi("RequestSelectStartDeTu")
def _(c, d):
    return ("NotifySelectStartDeTuSuccess", {"status": "success"})

@rmi("RequestTuLuyenDeTu")
def _(c, d):
    return ("NotifyTuLuyenDeTuSuccess", {"status": "success"})

@rmi("RequestThamGiaLuaTrai")
def _(c, d):
    return ("NotifyThamGiaLuaTraiSuccess", {"status": "success"})

@rmi("RequestRoiDiLuaTrai")
def _(c, d):
    return ("NotifyRoiDiLuaTraiSuccess", {"status": "success"})

@rmi("RequestDanhGiangHo")
def _(c, d):
    return ("NotifyDanhGiangHoSuccess", {"status": "success"})

@rmi("RequestNhanThuongGiangHo")
def _(c, d):
    return ("NotifyNhanThuongGiangHoSuccess", {"status": "success"})

@rmi("RequestResetLuotGiangHo")
def _(c, d):
    return ("NotifyResetLuotGiangHoSuccess", {"status": "success"})

@rmi("RequestThamGiaNienThu")
def _(c, d):
    return ("NotifyThamGiaNienThuSuccess", {"status": "success"})

@rmi("RequestSummonNienThu")
def _(c, d):
    return ("NotifySummonNienThuSuccess", {"status": "success"})

@rmi("RequestPaymentConfirm")
def _(c, d):
    return ("NotifyPaymentConfirmSuccess", {"status": "success"})

@rmi("RequestCardPayment")
def _(c, d):
    return ("NotifyCardPaymentSuccess", {"status": "success"})

@rmi("RequestBuyLeBao")
def _(c, d):
    return ("NotifyBuyLeBaoSuccess", {"status": "success"})

@rmi("RequestTestProudNet")
def _(c, d):
    return ("NotifyTestProudNet", {"status": "success", "message": "Pong!"})

@rmi("RequestHighlight")
def _(c, d):
    return ("NotifyHighlightSuccess", {"status": "success"})

@rmi("RequestHideSoha")
def _(c, d):
    return ("NotifyHideSohaSuccess", {"status": "success"})

@rmi("RequestShowSoha")
def _(c, d):
    return ("NotifyShowSohaSuccess", {"status": "success"})

@rmi("RequestKichHoatGiftCode")
def _(c, d):
    code = d.get("code", "")
    account_id = d.get("account_id", 1)
    gift_codes = {"MVL2024": {"gold": 5000, "knb": 50}, "PRIVATE": {"gold": 10000, "knb": 100}, "WELCOME": {"gold": 3000, "knb": 30}}
    if code in gift_codes:
        reward = gift_codes[code]
        conn = get_db()
        acc = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
        if acc:
            conn.execute("UPDATE accounts SET gold=?, knb=? WHERE id=?", ((acc['gold'] or 0) + reward['gold'], (acc['knb'] or 0) + reward['knb'], account_id))
            conn.commit()
        conn.close()
        return ("NotifyKichHoatGiftCodeSuccess", {"status": "success", "rewards": reward})
    return ("NotifyKichHoatGiftCodeFailed", {"status": "fail", "message": "Invalid code"})

@rmi("RequestGetGamerInfo")
def _(c, d):
    target_id = d.get("target_id", 1)
    conn = get_db()
    acc = conn.execute("SELECT * FROM accounts WHERE id=?", (target_id,)).fetchone()
    conn.close()
    if not acc:
        return ("NotifyGetGamerInfoFailed", {"status": "fail"})
    return ("NotifyGetGamerInfoSuccess", {"status": "success", "player": get_default_player_data(acc)})

@rmi("RequestGetOtherPlayer")
def _(c, d):
    return rmi_handlers["RequestGetGamerInfo"](c, d)

@rmi("RequestGetListOtherPlayer")
def _(c, d):
    return ("NotifyGetListOtherPlayerSuccess", {"status": "success", "players": []})

@rmi("RequestGetListOtherUser")
def _(c, d):
    return ("NotifyGetListOtherUserSuccess", {"status": "success", "users": []})

@rmi("RequestFriend")
def _(c, d):
    return ("NotifyFriendSuccess", {"status": "success"})

@rmi("RequestFriendIcon")
def _(c, d):
    return ("NotifyFriendIconSuccess", {"status": "success"})

@rmi("RequestFriendLabel")
def _(c, d):
    return ("NotifyFriendLabelSuccess", {"status": "success"})

@rmi("RequestList")
def _(c, d):
    return ("NotifyListSuccess", {"status": "success", "list": []})

@rmi("RequestUpdate")
def _(c, d):
    return ("NotifyUpdateSuccess", {"status": "success"})

@rmi("RequestType")
def _(c, d):
    return ("NotifyTypeSuccess", {"status": "success"})

@rmi("RequestAgaint")
def _(c, d):
    return ("NotifyAgaintSuccess", {"status": "success"})

@rmi("RequestBattleData")
def _(c, d):
    return ("NotifyBattleDataSuccess", {"status": "success"})

# ============== HTTP REQUEST HANDLER ==============
class MVLHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html, status=200):
        body = html.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_redirect(self, url, status=302):
        self.send_response(status)
        self.send_header('Location', url)
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self):
        p = urlparse(self.path)
        q = parse_qs(p.query)
        path = p.path

        # === SDK LOGIN DIALOG ===
        if path.startswith('/dialog/SdkWebView/login_ver2'):
            self.send_html(LOGIN_PAGE_HTML)
            return

        # === OAUTH FLOW ===
        if path.startswith('/dialog/oauthv2/setsession'):
            session_id = q.get('session_id', [''])[0]
            redirect_uri = q.get('redirect_uri', ['urilogin'])[0]
            conn = get_db()
            acc = conn.execute("SELECT * FROM accounts WHERE session_id=?", (session_id,)).fetchone()
            if acc:
                self.send_redirect(f"urilogin://success?access_token={acc['access_token']}&user_id={acc['id']}&username={quote(acc['username'])}")
            else:
                self.send_redirect("urilogin://fail?message=Invalid+session")
            conn.close()
            return

        if path.startswith('/dialog/oauthv2'):
            # OAuth dialog - redirect to our login
            self.send_html(LOGIN_PAGE_HTML)
            return

        if path.startswith('/dialog/oauthv2/Welcome'):
            self.send_html(LOGIN_PAGE_HTML)
            return

        # === AUTH ENDPOINTS ===
        if path in ('/api/a/GET/auth/login', '/api/a/GET/auth/loginmobile'):
            email = q.get('email', [''])[0]
            pw = q.get('password', [''])[0]
            if not email:
                self.send_json({"status": "fail", "message": "Missing email"})
                return
            conn = get_db()
            acc = conn.execute("SELECT * FROM accounts WHERE username=?", (email,)).fetchone()
            if not acc:
                # Auto-register
                token = gen_token()
                session_id = gen_token()[:16]
                username = email.split('@')[0] if '@' in email else email
                conn.execute("INSERT INTO accounts (username, password_hash, email, access_token, session_id, last_login) VALUES (?,?,?,?,?,?)",
                             (username, hash_pw(pw or ''), email, token, session_id, time.strftime('%Y-%m-%d %H:%M:%S')))
                conn.commit()
                acc = conn.execute("SELECT * FROM accounts WHERE username=?", (email,)).fetchone()
            else:
                # Verify password
                if acc['password_hash'] != hash_pw(pw or ''):
                    conn.close()
                    self.send_json({"status": "fail", "message": "Sai mat khau"})
                    return
                token = gen_token()
                session_id = gen_token()[:16]
                conn.execute("UPDATE accounts SET access_token=?, session_id=?, last_login=? WHERE id=?",
                             (token, session_id, time.strftime('%Y-%m-%d %H:%M:%S'), acc['id']))
                conn.commit()
            conn.close()
            # Track online player
            update_player_activity(acc['id'], acc['username'])
            self.send_json({
                "status": "success",
                "type": "login",
                "user_info": {"user_id": str(acc['id']), "username": acc['username'], "display_name": acc['username']},
                "access_token": token,
                "session_id": session_id,
                "message": "Login successful"
            })
            return

        # === SESSION / USER INFO ===
        if path in ('/api/a/GET/me/session', '/api/a/GET/me/userinfo'):
            token = q.get('access_token', q.get('viet_token', ['']))[0]
            conn = get_db()
            acc = conn.execute("SELECT * FROM accounts WHERE access_token=?", (token,)).fetchone() if token else None
            conn.close()
            if acc:
                self.send_json({"status": "success", "user_id": str(acc['id']), "username": acc['username'], "access_token": token})
            else:
                self.send_json({"status": "success", "user_id": "0", "username": "guest",
                                "display_name": "guest", "email": "",
                                "access_token": "", "avatar": "", "vip_level": 0,
                                "gold": 0, "knb": 0, "level": 1})
            return

        # === TOKEN EXCHANGE ===
        if path.startswith('/api/a/GET/me/exchangetoken'):
            token = q.get('access_token', q.get('viet_token', ['']))[0]
            conn = get_db()
            acc = conn.execute("SELECT * FROM accounts WHERE access_token=?", (token,)).fetchone() if token else None
            conn.close()
            if acc:
                self.send_json({"status": "success", "access_token": token, "user_id": str(acc['id']), "username": acc['username']})
            else:
                self.send_json({"status": "fail", "message": "Invalid token"})
            return

        # === APP INFO ===
        if path.startswith('/api/a/GET/app/oinfo') or path.startswith('/api/a/iGET/app/oinfo'):
            self.send_json({
                "status": "success",
                "app_id": APP_ID,
                "version": GAME_VERSION,
                "notifi": {"status": "no", "force": "no"},
                "time_refresh_cache": str(int(time.time()))
            })
            return

        # === SERVER LIST ===
        if path == '/api/server/list':
            self.send_json({
                "status": "success",
                "GameServerList": GAME_SERVERS,
                "LoginCfg": GAME_CONFIG,
                "PlayedServerList": [1]
            })
            return

        # === LOGGING ===
        if path == '/api/a/GET/mobile/logplayuser':
            self.send_json({"status": "ok"})
            return

        if path.startswith('/api/a/POST/mobile/LogInstall'):
            self.send_json({"status": "ok"})
            return

        if path.startswith('/api/a/POST/mobile/logload'):
            self.send_json({"status": "ok"})
            return

        # === ADS ===
        if path.startswith('/api/a/GET/ads/'):
            self.send_json({"status": "ok", "data": [], "settings": {}})
            return

        # === NOTIFICATIONS ===
        if path.startswith('/public/getNotification'):
            self.send_json({"status": "ok", "notifications": [], "notification": {}})
            return

        if path.startswith('/public/getMysohaScheme'):
            self.send_json({"status": "ok", "scheme": ""})
            return

        # === GAME DATA ===
        if path.startswith('/apiv1/game/getMobileGameData'):
            self.send_json({"status": "ok", "data": {}})
            return

        # === DIALOG PAGES ===
        if path.startswith('/dialog/SdkWebView'):
            self.send_html(LOGIN_PAGE_HTML)
            return

        if path.startswith('/dialog/ConnectLogin/'):
            self.send_html(LOGIN_PAGE_HTML)
            return

        if path.startswith('/dialog/oauthv2'):
            self.send_html(LOGIN_PAGE_HTML)
            return

        if path.startswith('/dialog/'):
            self.send_html(LOGIN_PAGE_HTML)
            return

        # === PAYMENT ===
        if path.startswith('/api/a/GET/order/mobile'):
            self.send_json({"status": "ok"})
            return

        if path.startswith('/api/a/POST/pay/'):
            self.send_json({"status": "ok"})
            return

        # === PUSH ===
        if path.startswith('/api/a/POST/Push/'):
            self.send_json({"status": "ok"})
            return

        # === UTIL ===
        if path.startswith('/api/a/GET/util/'):
            self.send_json({"status": "ok"})
            return

        # === HEALTH ===
        if path == '/health':
            conn = get_db()
            count = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
            conn.close()
            self.send_json({"status": "ok", "game": SERVER_NAME, "port": SERVER_PORT, "players": count})
            return

        # === DEFAULT ===
        self.send_json({"status": "ok"})

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length) if length else b''
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}

        p = urlparse(self.path)
        path = p.path

        # === REGISTER ===
        if path.startswith('/api/a/POST/auth/register'):
            username = data.get('username', data.get('email', ''))
            password = data.get('password', '')
            email = data.get('email', username)
            if not username:
                self.send_json({"status": "fail", "message": "Missing username"})
                return
            conn = get_db()
            existing = conn.execute("SELECT id FROM accounts WHERE username=?", (username,)).fetchone()
            if existing:
                conn.close()
                self.send_json({"status": "fail", "message": "Username already exists"})
                return
            token = gen_token()
            session_id = gen_token()[:16]
            conn.execute("INSERT INTO accounts (username, password_hash, email, access_token, session_id) VALUES (?,?,?,?,?)",
                         (username, hash_pw(password or username), email, token, session_id))
            conn.commit()
            acc = conn.execute("SELECT * FROM accounts WHERE username=?", (username,)).fetchone()
            conn.close()
            self.send_json({"status": "success", "user_info": {"user_id": str(acc['id']), "username": username}, "access_token": token, "session_id": session_id})
            return

        self.send_json({"status": "ok"})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Length', '0')
        self.end_headers()

# ============== PROUDNET ==============
MSG_CONNECT, MSG_CONNECT_ACK, MSG_RMI, MSG_HEARTBEAT = 0x04, 0x05, 0x01, 0x03

def handle_proudnet_client(conn, addr):
    host_id = hash(addr) & 0xFFFF
    player_id = None
    print(f"[ProudNet] Connected: {addr} (HostID: {host_id})")
    try:
        while True:
            hdr = b''
            while len(hdr) < 4:
                chunk = conn.recv(4 - len(hdr))
                if not chunk: return
                hdr += chunk
            msg_len = struct.unpack('<I', hdr)[0]
            if msg_len > 65536 or msg_len < 1: break
            type_data = conn.recv(1)
            if not type_data: break
            msg_type = struct.unpack('<B', type_data)[0]
            payload = b''
            need = msg_len - 1
            while len(payload) < need:
                chunk = conn.recv(need - len(payload))
                if not chunk: break
                payload += chunk
            try:
                data = json.loads(payload.decode('utf-8'))
            except:
                data = {}

            if msg_type == MSG_CONNECT:
                # Track player online
                account_id = data.get("account_id") or data.get("user_id")
                if account_id:
                    player_id = account_id
                    update_player_activity(account_id, data.get("username", str(account_id)), conn)
                resp = json.dumps({"status":"success","host_id":host_id,"server_time":int(time.time()*1000)}).encode()
                conn.sendall(struct.pack('<I', len(resp)+1) + struct.pack('<B', MSG_CONNECT_ACK) + resp)

            elif msg_type == MSG_RMI:
                rmi_name = data.get("rmi", "")
                rmi_data = data.get("data", {})
                rmi_data.setdefault("account_id", host_id)
                print(f"[C2S] {rmi_name}")
                if rmi_name in rmi_handlers:
                    try:
                        notify, resp_data = rmi_handlers[rmi_name](conn, rmi_data)
                    except Exception as e:
                        print(f"[RMI] Error: {rmi_name}: {e}")
                        traceback.print_exc()
                        notify = rmi_name.replace("Request","Notify") + "Success"
                        resp_data = {"status":"error","message":str(e)}
                else:
                    notify = rmi_name.replace("Request","Notify") + "Success"
                    resp_data = {"status":"success"}
                resp = json.dumps({"rmi":notify,"data":resp_data,"timestamp":int(time.time()*1000)}).encode()
                conn.sendall(struct.pack('<I', len(resp)+1) + struct.pack('<B', MSG_RMI) + resp)
                print(f"[S2C] {notify}")

            elif msg_type == MSG_HEARTBEAT:
                resp = json.dumps({"server_time":int(time.time()*1000)}).encode()
                conn.sendall(struct.pack('<I', len(resp)+1) + struct.pack('<B', MSG_HEARTBEAT) + resp)

    except (ConnectionResetError, BrokenPipeError): pass
    except Exception as e:
        print(f"[ProudNet] Error: {e}")
    finally:
        conn.close()
        print(f"[ProudNet] Disconnected: {addr}")
        if player_id:
            remove_player(player_id)
            print(f"[Server] Player {player_id} removed from online list")

def is_http_first_byte(b):
    return b in b'GPHODPC'

def handle_raw_connection(conn, addr):
    try:
        conn.settimeout(10)
        first = conn.recv(1, socket.MSG_PEEK)
        if not first:
            conn.close()
            return
        if is_http_first_byte(first[0]):
            request = b''
            while True:
                chunk = conn.recv(4096)
                if not chunk: break
                request += chunk
                if b'\r\n\r\n' in request:
                    headers_end = request.index(b'\r\n\r\n') + 4
                    cl = 0
                    for line in request[:headers_end].decode('utf-8', errors='ignore').split('\r\n'):
                        if line.lower().startswith('content-length:'):
                            cl = int(line.split(':')[1].strip())
                    if len(request) >= headers_end + cl:
                        break
            if not request:
                conn.close()
                return
            try:
                lines = request.decode('utf-8', errors='ignore').split('\r\n')
                parts = lines[0].split(' ')
                if len(parts) < 2:
                    conn.close()
                    return
                method, path = parts[0], parts[1]
                headers = {}
                body = ''
                for i, line in enumerate(lines[1:], 1):
                    if line == '':
                        body = '\r\n'.join(lines[i+1:])
                        break
                    if ':' in line:
                        k, v = line.split(':', 1)
                        headers[k.strip().lower()] = v.strip()
                parsed = urlparse(path)
                params = parse_qs(parsed.query)

                # Create a fake handler to use the methods
                class FakeHandler:
                    def __init__(self):
                        self.wfile = BytesIO()
                        self.headers = headers
                        self.rfile = BytesIO(body.encode())
                        self._headers = []
                        self._status = 200
                    def send_response(self, status):
                        self._status = status
                    def send_header(self, key, value):
                        self._headers.append((key, value))
                    def end_headers(self):
                        pass

                handler = FakeHandler()

                if method == 'GET':
                    response_data = route_request(method, parsed.path, params, body, headers)
                    if isinstance(response_data, str):
                        # HTML response
                        response_bytes = response_data.encode('utf-8')
                        http_response = (
                            f"HTTP/1.1 200 OK\r\n"
                            f"Content-Type: text/html; charset=utf-8\r\n"
                            f"Content-Length: {len(response_bytes)}\r\n"
                            f"Connection: close\r\n\r\n"
                        ).encode() + response_bytes
                    else:
                        # JSON response
                        response_json = json.dumps(response_data, ensure_ascii=False).encode('utf-8')
                        http_response = (
                            f"HTTP/1.1 200 OK\r\n"
                            f"Content-Type: application/json; charset=utf-8\r\n"
                            f"Access-Control-Allow-Origin: *\r\n"
                            f"Content-Length: {len(response_json)}\r\n"
                            f"Connection: close\r\n\r\n"
                        ).encode() + response_json
                    conn.sendall(http_response)
                elif method == 'POST':
                    try:
                        post_data = json.loads(body) if body else {}
                    except:
                        post_data = {}
                    response_data = route_post(parsed.path, post_data, params)
                    response_json = json.dumps(response_data, ensure_ascii=False).encode('utf-8')
                    http_response = (
                        f"HTTP/1.1 200 OK\r\n"
                        f"Content-Type: application/json; charset=utf-8\r\n"
                        f"Access-Control-Allow-Origin: *\r\n"
                        f"Content-Length: {len(response_json)}\r\n"
                        f"Connection: close\r\n\r\n"
                    ).encode() + response_json
                    conn.sendall(http_response)
                elif method == 'OPTIONS':
                    http_response = (
                        f"HTTP/1.1 200 OK\r\n"
                        f"Access-Control-Allow-Origin: *\r\n"
                        f"Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
                        f"Access-Control-Allow-Headers: Content-Type\r\n"
                        f"Content-Length: 0\r\n\r\n"
                    ).encode()
                    conn.sendall(http_response)
            except Exception as e:
                print(f"[HTTP] Error: {e}")
                conn.sendall(b"HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n")
        else:
            handle_proudnet_client(conn, addr)
    except socket.timeout: pass
    except (ConnectionResetError, BrokenPipeError): pass
    except Exception as e:
        print(f"[Server] Error: {e}")
    finally:
        try: conn.close()
        except: pass

def route_request(method, path, params, body, headers):
    """Route HTTP GET request. Returns dict (JSON) or str (HTML)"""
    if path in ('/api/a/GET/auth/login', '/api/a/GET/auth/loginmobile'):
        email = params.get('email', [''])[0]
        pw = params.get('password', [''])[0]
        if not email:
            return {"status": "fail", "message": "Missing email"}
        conn = get_db()
        acc = conn.execute("SELECT * FROM accounts WHERE username=?", (email,)).fetchone()
        if not acc:
            token = gen_token()
            conn.execute("INSERT INTO accounts (username,password_hash,email,access_token,last_login) VALUES (?,?,?,?,?)",
                         (email, hash_pw(pw or email), email, token, time.strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            acc = conn.execute("SELECT * FROM accounts WHERE username=?", (email,)).fetchone()
        else:
            if pw and acc['password_hash'] != hash_pw(pw):
                conn.close()
                return {"status": "fail", "message": "Wrong password"}
            token = gen_token()
            conn.execute("UPDATE accounts SET access_token=?, last_login=? WHERE id=?",
                         (token, time.strftime('%Y-%m-%d %H:%M:%S'), acc['id']))
            conn.commit()
        conn.close()
        session_id = gen_token()[:16]
        conn2 = get_db()
        conn2.execute("UPDATE accounts SET session_id=? WHERE id=?", (session_id, acc['id']))
        conn2.commit()
        conn2.close()
        return {"status": "success", "type": "login",
                "user_info": {"user_id": str(acc['id']), "username": email, "display_name": email.split('@')[0]},
                "access_token": token, "session_id": session_id, "message": "Login successful"}

    if path.startswith('/api/a/GET/app/oinfo') or path.startswith('/api/a/iGET/app/oinfo'):
        return {"status": "success", "app_id": APP_ID, "version": GAME_VERSION,
                "notifi": {"status": "no", "force": "no"}, "time_refresh_cache": str(int(time.time()))}

    if path in ('/api/a/GET/me/session', '/api/a/GET/me/userinfo'):
        token = params.get('access_token', params.get('viet_token', ['']))[0]
        if token:
            conn = get_db()
            acc = conn.execute("SELECT * FROM accounts WHERE access_token=?", (token,)).fetchone()
            conn.close()
            if acc:
                return {"status": "success", "user_id": str(acc['id']), "username": acc['username'],
                        "display_name": acc['username'], "email": acc['email'] or acc['username'],
                        "access_token": token, "avatar": "", "vip_level": 0,
                        "gold": acc['gold'] if 'gold' in acc.keys() else 0,
                        "knb": acc['knb'] if 'knb' in acc.keys() else 0,
                        "level": acc['level'] if 'level' in acc.keys() else 1}
        # Token không hợp lệ - trả về guest info thay vì fail
        return {"status": "success", "user_id": "0", "username": "guest",
                "display_name": "guest", "email": "",
                "access_token": "", "avatar": "", "vip_level": 0,
                "gold": 0, "knb": 0, "level": 1}

    if path.startswith('/api/a/GET/me/exchangetoken'):
        token = params.get('access_token', params.get('viet_token', ['']))[0]
        if token:
            conn = get_db()
            acc = conn.execute("SELECT * FROM accounts WHERE access_token=?", (token,)).fetchone()
            conn.close()
            if acc:
                return {"status": "success", "access_token": token, "user_id": str(acc['id']), "username": acc['username']}
        return {"status": "fail", "message": "Invalid token"}

    if path == '/api/a/GET/mobile/logplayuser':
        return {"status": "ok"}

    if path == '/api/server/list':
        return {"status": "success", "GameServerList": GAME_SERVERS, "LoginCfg": GAME_CONFIG, "PlayedServerList": [1]}

    if path == '/health':
        conn = get_db()
        count = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        conn.close()
        return {"status": "ok", "game": SERVER_NAME, "port": SERVER_PORT, "players": count}

    # Login dialog pages - return HTML
    if path.startswith('/dialog/SdkWebView'):
        return LOGIN_PAGE_HTML
    if path.startswith('/dialog/oauthv2/setsession'):
        session_id = params.get('session_id', [''])[0]
        conn = get_db()
        acc = conn.execute("SELECT * FROM accounts WHERE session_id=?", (session_id,)).fetchone()
        conn.close()
        if acc:
            return f'<html><head><meta http-equiv="refresh" content="0;url=urilogin://success?access_token={acc["access_token"]}&user_id={acc["id"]}&username={acc["username"]}"></head><body>Redirecting...</body></html>'
        return '<html><body>Invalid session</body></html>'
    if path.startswith('/dialog/oauthv2'):
        return LOGIN_PAGE_HTML
    if path.startswith('/dialog/SdkWebView'):
        return LOGIN_PAGE_HTML
    if path.startswith('/dialog/'):
        return LOGIN_PAGE_HTML

    return {"status": "ok"}

def route_post(path, data, params):
    if path.startswith('/api/a/POST/auth/register'):
        username = data.get('username', data.get('email', ''))
        password = data.get('password', '')
        if not username:
            return {"status": "fail", "message": "Missing username"}
        conn = get_db()
        existing = conn.execute("SELECT id FROM accounts WHERE username=?", (username,)).fetchone()
        if existing:
            conn.close()
            return {"status": "fail", "message": "Username already exists"}
        token = gen_token()
        conn.execute("INSERT INTO accounts (username,password_hash,email,access_token) VALUES (?,?,?,?)",
                     (username, hash_pw(password or username), data.get('email', username), token))
        conn.commit()
        acc = conn.execute("SELECT * FROM accounts WHERE username=?", (username,)).fetchone()
        conn.close()
        return {"status": "success", "user_info": {"user_id": str(acc['id']), "username": username}, "access_token": token}
    # Catch-all for dialog pages - return login page
    if path.startswith('/dialog/'):
        return LOGIN_PAGE_HTML

    return {"status": "ok"}

# ============== MAIN ==============
if __name__ == "__main__":
    print("=" * 55)
    print("  Mong Vo Lam - Private Server v2")
    print(f"  Port: {SERVER_IP}:{SERVER_PORT}")
    print("  HTTP + ProudNet on same port")
    print("=" * 55)

    init_db()
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    conn.close()
    print(f"  Accounts: {count}")
    print(f"  RMI handlers: {len(rmi_handlers)}")

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((SERVER_IP, SERVER_PORT))
    srv.listen(50)

    print(f"\n[Server] Listening on {SERVER_IP}:{SERVER_PORT}")
    print(f"[Server] Login page: http://{SERVER_PUBLIC_IP}:{SERVER_PORT}/dialog/SdkWebView/login_ver2/")
    print(f"[Server] Health: http://{SERVER_PUBLIC_IP}:{SERVER_PORT}/health")
    print(f"\n[Server] Ready!\n")

    try:
        while True:
            conn, addr = srv.accept()
            t = threading.Thread(target=handle_raw_connection, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\n[Server] Stopped.")
        srv.close()
