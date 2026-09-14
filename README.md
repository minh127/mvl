# ⚔️ Mộng Võ Lâm - Private Server

> Phục hồi tuổi thơ - Game Mộng Võ Lâm của SohaGame chạy trên server riêng

## 🎮 Giới thiệu

**Mộng Võ Lâm** là game mobile thể loại MMORPG kiếm hiệp từng rất phổ biến tại Việt Nam, phát hành bởi SohaGame. Sau khi server gốc đóng cửa, project này được tạo ra để phục hồi lại game, cho phép chơi trên server riêng.

### Tính năng chính
- 🗡️ 10 môn phái (Thiếu Lâm, Thiên Vương, Đường Môn, Nga My, Thúy Yên, Cái Bang, Thiên Nhẫn, Võ Đang, Côn Lôn, Ngũ Độc)
- ⚔️ Hệ thống chiến đấu PvE & PvP
- 🎒 Hệ thống vật phẩm, trang bị, cường hóa
- 💬 Chat (World / Guild / Cross-server)
- 👥 Bạn bè, bang hội, liên minh
- 📬 Hệ thống thư
- 🏆 Xếp hạng
- 🎁 Phần thưởng hàng ngày, Gift Code
- 🐎 Pet, ngựa, thời trang
- 🎰 Vòng quay may mắn

## 🚀 Cài đặt nhanh

### Yêu cầu
- Server Pterodactyl (0.5 core, 1GB RAM, 2GB disk)
- Python 3.x
- Port 2031 mở

### Bước 1: Clone repo
```bash
git clone https://github.com/truong20405s/mong-vo-lam-private.git
cd mong-vo-lam-private
```

### Bước 2: Chạy server
```bash
cd server
python3 mvl_server_full.py
```

### Bước 3: Cài APK
- Copy `MongVoLam_Private.apk` vào điện thoại
- Copy OBB vào `/sdcard/Android/obb/vn.shg.mobi.mongvolam/`
- Mở game → Bấm "Bắt đầu" → Đăng nhập

### Bước 4: Kiểm tra
```bash
curl http://45.137.70.90:2031/health
```

## 📁 Cấu trúc repo

```
mong-vo-lam-private/
├── README.md                    # Giới thiệu tổng quan
├── PROJECT.md                   # Chi tiết kỹ thuật project
├── NOTES.md                     # Những thứ cần lưu ý
├── APK_ANALYSIS.md              # Phân tích cấu trúc APK
├── server/
│   ├── mvl_server_full.py       # Server chính (HTTP + ProudNet)
│   └── start.sh                 # Script khởi động
├── MongVoLam_Private.apk        # APK đã patch IP
└── Android/obb/...              # OBB game data
```

## 🎁 Gift Codes

| Code | Gold | KNB |
|------|------|-----|
| `MVL2024` | 5,000 | 50 |
| `PRIVATE` | 10,000 | 100 |
| `WELCOME` | 3,000 | 30 |

## ⚠️ Lưu ý

- Project này chỉ phục vụ mục đích học tập và nghiên cứu
- Không sử dụng cho mục đích thương mại
- Game data thuộc bản quyền của SohaGame

## 📄 License

Project này được tạo ra cho mục đích học tập và nghiên cứu.
