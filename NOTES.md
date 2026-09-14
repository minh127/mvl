# ⚠️ Những thứ cần lưu ý - Mộng Võ Lâm Private Server

## 1. Bảo mật

### 1.1 Mật khẩu
- Mật khẩu được hash bằng SHA-256 trước khi lưu vào database
- **Không sử dụng mật khẩu trùng với các dịch vụ khác**
- Nên sử dụng mật khẩu phức tạp

### 1.2 Token
- Access token được tạo ngẫu nhiên khi đăng nhập
- Token có thời hạn không xác định (không tự động hết hạn)
- Nếu nghi ngờ bị lộ, đăng nhập lại để tạo token mới

### 1.3 Server
- Server chạy trên port 2031, cần mở port trên firewall
- SQLite database lưu trực tiếp trên server
- **Không có mã hóa dữ liệu** (dữ liệu truyền plain text)

## 2. Hạn chế

### 2.1 ProudNet Protocol
- Server hiện tại **giả định JSON** cho RMI messages
- Game thật có thể dùng **binary serialization**
- Nếu game crash khi vào game → cần reverse-engineer thêm protocol

### 2.2 Chức năng chưa hoàn chỉnh
Các chức năng sau trả `success` nhưng chưa có logic đầy đủ:
- Bang Chiến (Guild War) - chỉ có stub
- Huyết Chiến (Blood War) - chỉ có stub
- Siêu Cup - chỉ có stub
- CT2 (Cross-server) - chỉ có stub
- Đệ Tử (Disciple) - chỉ có stub
- Lửa Trại (Campfire) - chỉ có stub
- Nien Thu (New Year) - chỉ có stub
- Payment - chỉ có stub

### 2.3 Game Balance
- EXP curve: `100 * (level ^ 1.5)`
- Drop rate: 10% cho tất cả quái
- Gold reward: `mob_gold + random(0, mob_gold/2)`
- Chưa có hệ thống chống hack/cheat

## 3. Xử lý lỗi thường gặp

### 3.1 Game không kết nối được
```
Kiểm tra:
1. Port 2031 có mở không? → curl http://IP:2031/health
2. Server có đang chạy không? → Kiểm tra Pterodactyl console
3. Firewall có chặn không? → Kiểm tra iptables/ufw
```

### 3.2 Form đăng nhập không hiện
```
Kiểm tra:
1. APK có đúng version không? → Cài lại APK
2. OBB có copy đúng không? → Kiểm tra /sdcard/Android/obb/
3. Server có trả HTML không? → curl http://IP:2031/dialog/SdkWebView/login_ver2/
```

### 3.3 Đăng nhập thất bại
```
Kiểm tra:
1. Server log có lỗi không? → Xem Pterodactyl console
2. Database có tồn tại không? → Kiểm tra mvl_game.db
3. Response format có đúng không? → Test bằng curl
```

### 3.4 Game crash sau khi đăng nhập
```
Nguyên nhân có thể:
1. ProudNet protocol mismatch → Cần reverse-engineer thêm
2. Game data missing → Kiểm tra OBB file
3. Memory limit → Tăng RAM cho Pterodactyl
```

## 4. Backup & Restore

### 4.1 Backup
```bash
# Backup database
cp mvl_game.db mvl_game_backup_$(date +%Y%m%d).db

# Backup toàn bộ server
tar -czf mvl_backup_$(date +%Y%m%d).tar.gz server/
```

### 4.2 Restore
```bash
# Restore database
cp mvl_game_backup_20240101.db mvl_game.db

# Restore server
tar -xzf mvl_backup_20240101.tar.gz
```

## 5. Monitoring

### 5.1 Kiểm tra trạng thái
```bash
# Health check
curl http://45.137.70.90:2031/health

# Số lượng account
sqlite3 mvl_game.db "SELECT COUNT(*) FROM accounts;"

# Log gần nhất
tail -f /var/log/mvl_server.log
```

### 5.2 Resource usage
```bash
# CPU/Memory
top -p $(pgrep -f mvl_server_full.py)

# Disk usage
du -sh mvl_game.db
```

## 6. Tùy chỉnh

### 6.1 Thêm Gift Code
Chỉnh sửa file `mvl_server_full.py`, tìm dòng `gift_codes`:
```python
gift_codes = {
    "MVL2024": {"gold": 5000, "knb": 50},
    "PRIVATE": {"gold": 10000, "knb": 100},
    "WELCOME": {"gold": 3000, "knb": 30},
    # Thêm code mới ở đây
    "NEWCODE": {"gold": 20000, "knb": 200},
}
```

### 6.2 Thay đổi server IP
Chỉnh sửa biến `SERVER_PUBLIC_IP`:
```python
SERVER_PUBLIC_IP = "IP_CUA_BAN"
```

### 6.3 Thay đổi port
Chỉnh sửa biến `SERVER_PORT`:
```python
SERVER_PORT = 2031
```

### 6.4 Thêm vật phẩm
Chỉnh sửa `ITEMS_DB`:
```python
ITEMS_DB = {
    # ... existing items ...
    300: {"name": "Kiếm mới", "type": "weapon", "class_id": -1, "level": 10, "attack": 25},
}
```

## 7. Pháp lý

- Project này chỉ phục vụ mục đích **học tập và nghiên cứu**
- **Không sử dụng cho mục đích thương mại**
- Game data thuộc bản quyền của **SohaGame**
- Không phân phối lại game data mà không có sự cho phép

## 8. Cập nhật

### 8.1 Cập nhật server
```bash
# Pull code mới
git pull origin main

# Restart server
# (trên Pterodactyl: Stop → Start)
```

### 8.2 Cập nhật APK
- Cần reverse-engineer lại APK nếu muốn thay đổi client
- APK hiện tại đã patch IP vào server

## 9. Liên hệ

- GitHub: https://github.com/truong20405s/mong-vo-lam-private
- Issues: Tạo issue trên GitHub nếu gặp lỗi
