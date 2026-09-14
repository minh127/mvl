# Nhật ký 2026-09-15

## GitHub Config (khôi phục nhanh)

**Cài gh CLI:**
```bash
cd /tmp
curl -sL "https://github.com/cli/cli/releases/download/v2.65.0/gh_2.65.0_linux_amd64.tar.gz" -o gh.tar.gz
tar xzf gh.tar.gz && mkdir -p ~/bin && cp gh_*/bin/gh ~/bin/gh && chmod +x ~/bin/gh
export PATH="$HOME/bin:$PATH"
```

**Khôi phục thẳng (không cần lấy mã):**
```bash
# Copy file config từ server cũ:
cp /đường_dẫn_server_cũ/.config/gh/hosts.yml ~/.config/gh/hosts.yml
gh auth setup-git
gh auth status
```

**Nếu mất token → đăng nhập lại (device flow):**
```bash
nohup gh auth login --hostname github.com --git-protocol https --web < /dev/null > /tmp/gh-login.log 2>&1 &
cat /tmp/gh-login.log  # lấy mã code
# Vào https://github.com/login/device → nhập mã
```

**Config:**
- Account: `truong20405s`
- Protocol: HTTPS
- Scopes: gist, read:org, repo
- Token location: `~/.config/gh/hosts.yml`
- gh binary: `~/bin/gh` (v2.65.0)
