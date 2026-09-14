# 🔍 Phân tích APK - Mộng Võ Lâm

## 1. Tổng quan

| Thông tin | Giá trị |
|-----------|---------|
| Package name | `vn.shg.mobi.mongvolam` |
| Version | 10.0.0 |
| App ID | `7f77e4348c5251668d2ac54eebe6f15c` |
| Facebook App ID | `1510703012479776` |
| Server IP | `45.137.70.90:2031` |
| Game Engine | Unity |
| Networking | ProudNet |

## 2. Cấu trúc file APK

```
MongVoLam_Private.apk
├── META-INF/
│   └── MANIFEST.MF
├── AndroidManifest.xml
├── classes.dex                    # Java/Kotlin code (Soha SDK)
├── assets/
│   ├── client.txt                 # App config (app_id, fb_id)
│   ├── bin/Data/
│   │   ├── mainData               # Unity main data
│   │   ├── settings.xml           # Unity settings
│   │   ├── Managed/
│   │   │   ├── Assembly-CSharp.dll        # Game logic (Unity)
│   │   │   ├── Assembly-CSharp-firstpass.dll
│   │   │   ├── Nettention.ProudNetClient.dll  # ProudNet client
│   │   │   ├── System.dll
│   │   │   ├── System.Core.dll
│   │   │   └── ...
│   │   └── sharedassets0.assets.* # Game assets
│   └── splash.png
├── lib/
│   ├── armeabi-v7a/
│   │   ├── libmain.so
│   │   ├── libmono.so
│   │   ├── libunity.so
│   │   └── libMesgLog.so
│   └── x86/
│       └── ...
└── res/
    └── ...
```

## 3. OBB File

```
main.100.vn.shg.mobi.mongvolam.obb (~157MB)
└── assets/bin/Data/
    ├── 0000000000000000f000000000000000
    ├── 000847ca94b540d41975d23c42c9f897
    ├── ... (4779 files total)
    └── ffef...
```

OBB chứa:
- Textures (hình ảnh, sprite)
- Audio (nhạc, sound effects)
- Animations
- UI assets
- Game data (items, skills, maps - binary format)

## 4. Phân tích DEX (classes.dex)

### 4.1 SohaGame SDK Classes
```
vn.soha.game.sdk.SohaSDK          # SDK chính
vn.soha.game.sdk.SohaActivity     # Activity login
vn.soha.game.sdk.SohaApplication  # Application class
vn.soha.game.sdk.utils.Utils      # Utilities
vn.soha.game.sdk.utils.LogStat    # Logging
```

### 4.2 Game Classes
```
vn.shg.mobi.mongvolam.MainActivity    # Main activity
vn.shg.mobi.mongvolam.UnityActivity   # Unity activity
```

### 4.3 Login Flow
```
SohaApplication.onCreate()
    → Init SDK
    → Check SharedPreferences for token

MainActivity.onCreate()
    → Start SohaActivity (if no token)

SohaActivity
    → Load WebView: /dialog/SdkWebView/login_ver2/
    → User enters credentials
    → Server returns token
    → Save to SharedPreferences
    → exchangeSOAPAccessToken()
    → /api/a/GET/me/exchangetoken

MainActivity
    → Start Unity game
    → Connect to ProudNet server
```

### 4.4 SharedPreferences Keys
```
SHARED_PREF_MYSOHA_ACCESS_TOKEN    # MySoha access token
SHARED_PREF_SOAP_ACCESS_TOKEN      # SOAP access token
SHARED_PREF_USER_EMAIL             # User email
SHARED_PREF_USER_ID                # User ID
SHARED_PREF_USER_NAME              # Username
SHARED_PREF_APP_ID                 # App ID
SHARED_PREF_APP_ID_FACEBOOK        # Facebook App ID
SHARED_PREF_PENDING_LOGIN_MYSOHA   # Pending login flag
```

## 5. Phân tích Assembly-CSharp.dll

### 5.1 Screen Classes
```
ScreenStart         # Màn hình bắt đầu
ScreenLogin         # Màn hình đăng nhập
ScreenReg           # Màn hình đăng ký
ScreenSelectServer  # Chọn server
ScreenMain          # Màn hình chính
ScreenBattle        # Màn hình chiến đấu
ScreenMonPhai       # Môn phái
ScreenWorldmap      # Bản đồ thế giới
```

### 5.2 Login Fields (ScreenLogin)
```
m_UserName          # Input tài khoản
m_UserPassword      # Input mật khẩu
VersionLabel        # Label version
grpLogin            # Login group (native form)
grpPublisher        # Publisher group (Soha buttons)
OnStartBtnClick     # Start button handler
DirectLogin         # Direct login method
DirectLoginSoha     # Soha SDK login method
OnConnect           # Connect handler
OnConnectVietID     # VietID connect
OnConnectFacebook   # Facebook connect
OnFindPassword      # Find password
OnRegister          # Register
```

### 5.3 Login Methods
```
DirectLogin         # Gọi thẳng /api/a/GET/auth/loginmobile
DirectLoginSoha     # Qua Soha SDK (WebView)
StartLogin          # Bắt đầu login flow
LoginSoha           # Soha login method
OnSohaLoginSuccess  # Callback khi login thành công
OnSohaLoginFail     # Callback khi login thất bại
```

### 5.4 RMI Methods (369 total)
Game sử dụng ProudNet RMI cho game logic:

#### Auth & Character (10 methods)
```
RequestFirstLogon, RequestNextLogon, RequestRegister,
RequestGetInfo, RequestSetInfo, RequestSetHeroData,
RequestSetHeroCfg, RequestUpdate, RequestType, RequestList
```

#### Combat (20+ methods)
```
RequestGetBattleResult, RequestDauLuanKiem, RequestThachDau,
RequestBangChienGetInfo, RequestBangChienMove, RequestBangChienVaoThanh,
RequestBangChienRoiThanh, RequestBangChienCongThanh, RequestStartHuyetChien,
RequestHoiSinhHuyetChien, RequestGetSieuCupData, RequestGetSieuCupBattle...
```

#### Inventory (15+ methods)
```
RequestSetTrangBi, RequestBuyVatPham, RequestBanTrangBi,
RequestCuongHoaTrangBi, RequestKhamNgoc, RequestGoNgoc,
RequestGhepManhTrangBi, RequestPhanRaTrangBi, RequestDungLuyenTrangBi...
```

#### Social (10+ methods)
```
RequestBangHuu, RequestAddBanBe, RequestAcceptBanBe,
RequestDeleteBanBe, RequestSearchBanBe, RequestSendChatMsg,
RequestSendChatAll, RequestSendChatLienMinh, RequestLapLienMinh...
```

## 6. Phân tích ProudNet Client

### 6.1 Protocol
```
ProudNet sử dụng TCP + UDP:
- TCP: Reliable messaging (RMI calls)
- UDP: Unreliable messaging (movement, combat)
- P2P: Direct peer-to-peer (optional)
```

### 6.2 Message Types
```
0x01 - RMI (Remote Method Invocation)
0x03 - Heartbeat
0x04 - Connect request
0x05 - Connect ACK
```

### 6.3 RMI Message Format (as implemented)
```
[4 bytes: payload length (little-endian)]
[1 byte: message type]
[N bytes: JSON payload]

JSON payload:
{
    "rmi": "RequestMethodName",
    "data": { ... }
}
```

### 6.4 Important Notes
- Server hiện tại **giả định JSON** cho RMI
- Game thật có thể dùng **binary serialization**
- Nếu game crash → cần reverse-engineer binary format

## 7. HTTP Endpoints (from DEX)

### 7.1 Auth
```
/api/a/GET/auth/loginmobile?app_id=%s&email=%s&password=***
/api/a/GET/auth/loginbig4?app_id=%s&big4_access_token=%s&big4_type=%s
/api/a/GET/me/session?
/api/a/GET/me/exchangetoken?
/api/a/GET/me/userinfo?
```

### 7.2 App
```
/api/a/GET/app/oinfo?app_key=%s&viet_token=%s
/api/a/iGET/app/oinfo?app_key=
/api/server/list
```

### 7.3 Dialog
```
/dialog/SdkWebView/login_ver2/?redirect_uri=urilogin
/dialog/SdkWebView?redirect_uri=uri_payment
/dialog/oauthv2?client_id=xxx&response_type=token&redirect_uri=shxxx%3A%2F%2F
/dialog/oauthv2/setsession?redirect_uri=%s&session_id=%s
/dialog/oauthv2/Welcome?
/dialog/ConnectLogin/FacebookApp?fb_accesstoken=%s&sdkver=%s&gver=%s
/dialog/paym?redirect_uri=%s&order_info=%s
/dialog/PaymentApp/Jailbreaken?
/dialog/redirect/forum?app_id=
```

### 7.4 Logging
```
/api/a/GET/mobile/logplayuser?
/api/a/POST/mobile/LogInstall?type=0
/api/a/POST/mobile/logload
/api/a/POST/Push/RegisterDevice
```

### 7.5 Payment
```
/api/a/GET/order/mobile?check=%s&order_id=%s
/api/a/POST/pay/create
/api/a/POST/pay/appstore
```

### 7.6 Ads
```
/api/a/GET/ads/CPMobileData?type=2&app_key=%s
/api/a/GET/ads/CPMobileSettings?app_key=%s
```

### 7.7 Public
```
/public/getNotifications?
/public/getNotification?
/public/getMysohaScheme?device_type=android
/apiv1/game/getMobileGameData?channel_id=12&platform=android
```

## 8. String References (from DEX)

### 8.1 Server URLs
```
http://45.137.70.90:2031 (38 occurrences)
```

### 8.2 SDK Strings
```
SohaSDK
SohaActivity
SohaApplication
exchangeSOAPAccessToken
SHARED_PREF_*
```

### 8.3 Game Strings
```
DirectLogin
DirectLoginSoha
ScreenLogin
ScreenStart
LoginRequest
LoginResponse
SohaLoginResponse
```

## 9. Screenshots

### Login Screen
```
┌─────────────────────────────┐
│                             │
│     ⚔️ Mộng Võ Lâm         │
│      Private Server         │
│                             │
│  ┌───────────────────────┐  │
│  │ Tài khoản             │  │
│  │ [________________]    │  │
│  │                       │  │
│  │ Mật khẩu              │  │
│  │ [________________]    │  │
│  │                       │  │
│  │ [   Đăng Nhập   ]    │  │
│  │ [Đăng Ký Mới    ]    │  │
│  └───────────────────────┘  │
│                             │
│  🎁 Gift Codes:            │
│  MVL2024, PRIVATE, WELCOME │
│                             │
└─────────────────────────────┘
```

## 10. Reverse Engineering Notes

### 10.1 Tools cần thiết
- `jadx` - Decompiler DEX → Java
- `apktool` - Decode/rebuild APK
- `dex2jar` - Convert DEX → JAR
- `ILSpy` - Decompile .NET DLL (Assembly-CSharp.dll)
- `Wireshark` - Capture network traffic

### 10.2 Chưa giải quyết
1. **ProudNet binary format** - Cần reverse-engineer từ Nettention.ProudNetClient.dll
2. **Game data format** - OBB files có thể dùng Unity asset bundle format
3. **Encryption** - Game có thể mã hóa communication
4. **Anti-cheat** - CodeStage.AntiCheat detected in DEX

### 10.3 Thách thức
1. Không có source code gốc
2. ProudNet protocol phức tạp (TCP+UDP, P2P, encryption)
3. Game data trong OBB có thể bị mã hóa
4. Unity version cũ → có thể có compatibility issues
