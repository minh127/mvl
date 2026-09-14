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

### Bài học & Phương hướng thất bại

#### 1. Poll process giết process
- **Sai:** Dùng `process poll` với timeout dài → process bị SIGTERM kill
- **Sai:** Poll lặp lại nhiều lần → process cũ bị orphan/killed
- **Đúng:** Dùng `nohup ... &` chạy nền, hoặc cron job kiểm tra sau
- **Lần sau:** Muốn giữ process sống → background hoàn toàn, không đụng vào cho đến khi user báo xong

#### 2. Gây phiền user vì thiếu tự chủ
- **Sai:** Bắt user báo khi đăng nhập xong → user đã nói "tự ngồi canh"
- **Sai:** Mỗi lần poll fail lại hỏi user → spam message
- **Đúng:** Tự dùng cron/schedule kiểm tra, không hỏi lại user
- **Lần sau:** Khi user nói "giữ process" → giữ im lặng, tự check bằng cron

#### 3. Cài tool không kiểm tra trước
- **Sai:** Cài apktool từ URL sai nhiều lần (404, file rỗng 0 bytes)
- **Sai:** Không kiểm tra Java có sẵn không → mất thời gian cài JDK
- **Đúng:** Check `which java` trước, download verify file size
- **Lần sau:** Luôn check prerequisites trước khi bắt đầu

#### 4. Patch .NET DLL qua smali
- **Sai:** Cố phân tích Assembly-CSharp.dll bằng tay (hex parsing) → quá phức tạp
- **Sai:** Không có tool .NET (monodis, ilspy) → manual metadata parse fail
- **Đúng:** Patch DEX (Java side) trước, bỏ qua Unity DLL nếu không có tool
- **Lần sau:** Muốn sửa Unity game → cần dnlib/monodis/ilspy, không có thì patch Java side

#### 5. Typo lặp lại
- `sleep2` thay vì `sleep 2` → 2 lần liên tiếp
- **Lần sau:** Viết command dài → copy-paste, không gõ tay

#### 6. Không test ngay
- Push server code nhưng chưa restart → code mới không chạy
- Push APK nhưng chưa cài test → không biết có hoạt động không
- **Lần sau:** Sau khi push → restart/deploy ngay nếu có thể, hoặc ghi rõ cần làm gì tiếp

#### 7. Thiếu sót khi phân tích
- Ban đầu chỉ sửa server, quên sửa APK → user hỏi "mày chưa sửa apk à"
- **Lần sau:** Khi user nói "sửa" → xác định rõ scope: server, client, hay cả hai

### Tóm tắt cho lần sau
1. **Giữ process = im lặng**, dùng nohup/cron, không poll, không hỏi
2. **Check toolchain trước** khi bắt đầu (java, gh, etc.)
3. **Patch Java/DEX trước**, bỏ qua .NET nếu không có tool
4. **Deploy ngay** sau khi push, hoặc ghi rõ next step
5. **Xác định scope** ngay từ đầu: server + client hay chỉ 1 trong 2
