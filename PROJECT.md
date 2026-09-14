# 📋 Chi tiết kỹ thuật - Mộng Võ Lâm Private Server

## 1. Tổng quan kiến trúc

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│  APK Client │────▶│  Server (Python) │────▶│  SQLite DB  │
│  (Android)  │◀────│  Port 2031       │◀────│  mvl_game.db│
└─────────────┘     └──────────────────┘     └─────────────┘
       │                     │
       │            ┌────────┴────────┐
       │            │                 │
       ▼            ▼                 ▼
  ┌─────────┐  ┌─────────┐    ┌──────────┐
  │ HTTP API│  │ProudNet │    │ Game Data│
  │ (login) │  │  (RMI)  │    │  (OBB)   │
  └─────────┘  └─────────┘    └──────────┘
```

## 2. Server chi tiết

### 2.1 Protocol Detection
Server sử dụng single port (2031) cho cả HTTP và ProudNet:
- **Byte đầu là ASCII letter** (G/P/H/O/D/P/C) → HTTP protocol
- **Byte đầu là binary** → ProudNet protocol

### 2.2 HTTP Endpoints

#### Auth endpoints
| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/api/a/GET/auth/loginmobile` | GET | Đăng nhập (email + password) |
| `/api/a/POST/auth/register` | POST | Đăng ký tài khoản mới |
| `/api/a/GET/me/session` | GET | Kiểm tra session |
| `/api/a/GET/me/exchangetoken` | GET | Đổi token |

#### Game endpoints
| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/api/a/GET/app/oinfo` | GET | Thông tin app |
| `/api/server/list` | GET | Danh sách server |
| `/api/a/GET/mobile/logplayuser` | GET | Log chơi game |
| `/health` | GET | Kiểm tra server |

#### SDK Dialog endpoints
| Endpoint | Response | Mô tả |
|----------|----------|-------|
| `/dialog/SdkWebView/login_ver2/` | HTML | Trang đăng nhập |
| `/dialog/oauthv2` | HTML | OAuth dialog |
| `/dialog/ConnectLogin/*` | HTML | Facebook login |
| `/dialog/*` | HTML | Catch-all dialog |

### 2.3 ProudNet RMI

Server xử lý 116 RMI handlers, bao gồm:

#### Auth & Character
- `RequestFirstLogon` - Tạo nhân vật lần đầu
- `RequestNextLogon` - Đăng nhập lần sau
- `RequestGetInfo` - Lấy thông tin nhân vật
- `RequestSetInfo` - Cập nhật thông tin

#### Combat
- `RequestGetBattleResult` - Xử lý kết quả chiến đấu
- `RequestDauLuanKiem` - PvP Luận Kiếm
- `RequestBangChienGetInfo` - Thông tin Bang Chiến

#### Inventory
- `RequestSetTrangBi` - Trang bị vật phẩm
- `RequestBuyVatPham` - Mua vật phẩm
- `RequestBanTrangBi` - Bán vật phẩm
- `RequestCuongHoaTrangBi` - Cường hóa

#### Social
- `RequestBangHuu` - Danh sách bạn bè
- `RequestAddBanBe` - Thêm bạn bè
- `RequestSendChatMsg` - Gửi tin nhắn
- `RequestLapLienMinh` - Tạo bang hội

#### Events
- `RequestDangNhapNhanThuong` - Phần thưởng đăng nhập
- `RequestQuayBacMayMan` - Vòng quay may mắn
- `RequestKichHoatGiftCode` - Nhập Gift Code

### 2.4 Database Schema

#### Bảng accounts
```sql
CREATE TABLE accounts (
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
);
```

#### Bảng guilds
```sql
CREATE TABLE guilds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    leader_id INTEGER,
    level INTEGER DEFAULT 1,
    exp INTEGER DEFAULT 0,
    members TEXT DEFAULT '[]',
    notice TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Bảng chat_log
```sql
CREATE TABLE chat_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT,
    sender TEXT,
    message TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 3. Game Data

### 3.1 Môn phái (10 phái)

| ID | Tên | HP | MP | ATK | DEF | SPD |
|----|------|-----|-----|-----|-----|-----|
| 0 | Thiếu Lâm | 150 | 30 | 12 | 15 | 8 |
| 1 | Thiên Vương | 120 | 50 | 15 | 10 | 12 |
| 2 | Đường Môn | 100 | 80 | 18 | 8 | 15 |
| 3 | Nga My | 90 | 100 | 10 | 12 | 10 |
| 4 | Thúy Yên | 95 | 90 | 14 | 11 | 11 |
| 5 | Cái Bang | 130 | 40 | 16 | 13 | 9 |
| 6 | Thiên Nhẫn | 110 | 60 | 13 | 14 | 10 |
| 7 | Võ Đang | 105 | 70 | 11 | 16 | 9 |
| 8 | Côn Lôn | 115 | 55 | 17 | 9 | 13 |
| 9 | Ngũ Độc | 85 | 95 | 20 | 7 | 14 |

### 3.2 Vật phẩm cơ bản

| ID | Tên | Loại | Chỉ số |
|----|------|------|--------|
| 1 | Kiếm Thường | Vũ khí | ATK +5 |
| 2 | Đao Thường | Vũ khí | ATK +4 |
| 3 | Áo Giáp Vàng | Giáp | DEF +5 |
| 4 | Áo Giáp Bạc | Giáp | DEF +4 |
| 5 | Nhẫn Lực | Nhẫn | HP +20 |
| 6 | Dây Chuyền | Dây chuyền | MP +15 |
| 7 | Thuốc Máu | Tiêu hao | Heal 50 |
| 8 | Thuốc Mana | Tiêu hao | Mana 30 |

### 3.3 Kỹ năng

| ID | Tên | Môn phái | Level | DMG | MP |
|----|------|----------|-------|-----|-----|
| 1 | Kiếm Quyết | Thiếu Lâm | 1 | 20 | 10 |
| 2 | La Hán Chưởng | Thiếu Lâm | 3 | 35 | 15 |
| 3 | Thương Quyết | Thiên Vương | 1 | 25 | 12 |
| 4 | Phong Hỏa Liên Hoàn | Thiên Vương | 5 | 45 | 20 |
| 5 | An Khí Quyết | Đường Môn | 1 | 30 | 15 |
| 6 | Giang Hòa | Đường Môn | 5 | 50 | 25 |
| 7 | Phát Quang | Nga My | 1 | 15 | 8 |
| 8 | Từ Quang | Nga My | 5 | 25 | 15 |

### 3.4 Quái vật

| ID | Tên | Level | HP | ATK | DEF | EXP | Gold |
|----|------|-------|-----|-----|-----|-----|------|
| 1 | Chó Sói | 1 | 30 | 5 | 2 | 10 | 5 |
| 2 | Heo Rừng | 2 | 50 | 8 | 3 | 15 | 8 |
| 3 | Cá Sấu | 3 | 80 | 12 | 5 | 25 | 12 |
| 4 | Hổ | 5 | 150 | 18 | 8 | 40 | 20 |
| 5 | Gấu | 6 | 200 | 22 | 10 | 50 | 25 |
| 6 | Báo | 8 | 300 | 30 | 15 | 70 | 35 |

### 3.5 Bản đồ

| ID | Tên | Level | Loại |
|----|------|-------|------|
| 1 | Thành Đô | 1 | Thành phố |
| 2 | Làng Tân Thủ | 1 | Chiến trường |
| 3 | Núi Thiếu Lâm | 5 | Chiến trường |
| 4 | Rừng Bạch Hổ | 10 | Chiến trường |
| 5 | Thiên Vương Bang | 15 | Chiến trường |

## 4. Luồng đăng nhập

```
┌─────────────┐
│  Mở game    │
└──────┬──────┘
       ▼
┌─────────────┐
│ Bấm bắt đầu│
└──────┬──────┘
       ▼
┌─────────────────────────────────────────────┐
│ Soha SDK check: /api/a/GET/me/session       │
│ (nếu có token → vào game)                   │
└──────┬──────────────────────────────────────┘
       ▼ (không có token)
┌─────────────────────────────────────────────┐
│ WebView load: /dialog/SdkWebView/login_ver2/│
│ → Hiện form đăng nhập HTML                  │
└──────┬──────────────────────────────────────┘
       ▼
┌─────────────────────────────────────────────┐
│ Nhập tài khoản + mật khẩu → Submit         │
│ GET /api/a/GET/auth/loginmobile             │
│ → Server tạo account + trả token            │
└──────┬──────────────────────────────────────┘
       ▼
┌─────────────────────────────────────────────┐
│ Redirect: urilogin://success?access_token=  │
│ → SDK lưu token                             │
└──────┬──────────────────────────────────────┘
       ▼
┌─────────────┐
│  Chọn server│
└──────┬──────┘
       ▼
┌─────────────────────────────────────────────┐
│ ProudNet connect: 45.137.70.90:2031         │
│ → RequestNextLogon / RequestFirstLogon      │
│ → Vào game                                  │
└─────────────────────────────────────────────┘
```

## 5. Yêu cầu hệ thống

| Thành phần | Yêu cầu |
|-----------|---------|
| CPU | 0.5 core |
| RAM | 1GB |
| Disk | 2GB |
| Python | 3.x |
| Port | 2031 (TCP) |
| OS | Linux (Pterodactyl) |

## 6. Hiệu suất

- **Concurrent connections:** ~50 (tùy RAM)
- **Database size:** Tối đa ~500MB (SQLite)
- **Response time:** < 100ms cho HTTP, < 50ms cho RMI
- **Memory usage:** ~50-100MB cho server Python
