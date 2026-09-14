# Nhật ký 2026-09-15

## Buổi sáng (05:30 - 06:27)

### Cài GitHub CLI
- Cài `gh` v2.65.0 (binary standalone, không có root/apt)
- Đăng nhập GitHub device flow — lần đầu bị process kill do poll timeout
- Lần 2 dùng `nohup` chạy nền → đăng nhập thành công
- **Tài khoản:** `truong20405s`

### Phân tích repo MVL (Mộng Võ Lâm)
- Repo: `truong20405s/mvl` — Private Server game Mộng Võ Lâm (SohaGame)
- Server Python chạy trên `45.137.70.90:2031`, có 2 players online
- Cấu trúc: APK + OBB + server code (ProudNet + HTTP)

### Sửa server (6 patches)
1. **Idle kick** — 5 phút không hoạt động → auto disconnect
2. **Login response** — dùng username thay vì email
3. **Password verify** — bắt buộc đúng password
4. **Auto-register** — username sạch (không có @)
5. **ProudNet disconnect tracking** — tự xóa player khi mất kết nối
6. **Online player tracking** — cập nhật last_active

→ Push commit `c551a9c` lên GitHub

### Patch APK — DirectLogin
- Cài JDK 21 portable + apktool 2.10.0
- Decompile APK → phân tích smali (DEX) + Assembly-CSharp.dll (Unity)
- **Vấn đề:** APK dùng `DirectLoginSoha` → WebView → form HTML bẩn
- **Fix:** Sửa `DialogLogin.vLogin()` + `DialogLogin$2.run()` → gọi thẳng API `/api/a/GET/auth/loginmobile`
- Bỏ WebView hoàn toàn, token tự lưu SharedPreferences
- Rebuild + sign APK → push commit `e0974a2`

### Chưa làm
- [ ] Restart server trên `45.137.70.90` (cần SSH)
- [ ] Cài APK mới lên điện thoại test
- [ ] Test login flow end-to-end

### Bài học
- Đừng poll process dài — dùng `nohup` chạy nền hoặc cron
- Smali patching cho .NET DLL rất khó, nên patch DEX (Java side) trước
- `gh auth setup-git` cần chạy trước `git push` khi dùng HTTPS
