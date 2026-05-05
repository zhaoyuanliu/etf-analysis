#!/usr/bin/env python3
"""
dev_beta/transform.py
將 dev_beta/index.html 轉換為 dev_beta 版本

使用方式：
    cp etfdev/index.html etf-analysis/dev_beta/index.html
    python3 etf-analysis/dev_beta/transform.py
"""

from pathlib import Path

ALLOWED_UIDS = ['YVRzEXWL9DbQ6qIJVoat8p0WFWW2']

target = Path(__file__).parent / 'index.html'

if not target.exists():
    print(f'[ERR] 找不到 {target}，請先 cp etfdev/index.html 到此目錄')
    exit(1)

with open(target, 'r', encoding='utf-8') as f:
    html = f.read()

errors = []

# 1. 修改 showPage() — 分頁跳轉保持 /dev_beta/ 前綴
OLD_PUSH_STATE = (
    "  if (opts.pushState !== false) {\n"
    "    const path = PAGE_ROUTES[name] || '/';\n"
    "    if (location.pathname !== path) history.pushState(null, '', path);\n"
    "  }"
)
NEW_PUSH_STATE = (
    "  if (opts.pushState !== false) {\n"
    "    const _basePath = location.pathname.startsWith('/dev_beta') ? '/dev_beta' : '';\n"
    "    const path = _basePath + (PAGE_ROUTES[name] || '/');\n"
    "    if (location.pathname !== path) history.pushState(null, '', path);\n"
    "  }"
)
if OLD_PUSH_STATE in html:
    html = html.replace(OLD_PUSH_STATE, NEW_PUSH_STATE)
    print('[OK] showPage() pushState → 保留 /dev_beta/ 前綴')
else:
    errors.append('showPage() pushState 替換失敗，格式可能已變更')

# 2. 修改 SPA redirect 路由查找 — 移除 /dev_beta/ 前綴再查 ROUTE_PAGES
OLD_SPA = (
    "const _spaRedirect = sessionStorage.getItem('spa_redirect');\n"
    "if (_spaRedirect) {\n"
    "  sessionStorage.removeItem('spa_redirect');\n"
    "  const _redirectPage = ROUTE_PAGES[_spaRedirect] || 'etfurl';\n"
    "  history.replaceState(null, '', _spaRedirect);\n"
    "  showPage(_redirectPage, { pushState: false });\n"
    "} else {\n"
    "  // 直接輸入路徑或刷新\n"
    "  const _initPage = ROUTE_PAGES[location.pathname];\n"
    "  if (_initPage) showPage(_initPage, { pushState: false });"
)
NEW_SPA = (
    "const _spaRedirect = sessionStorage.getItem('dev_beta_spa_redirect');\n"
    "if (_spaRedirect) {\n"
    "  sessionStorage.removeItem('dev_beta_spa_redirect');\n"
    "  const _routePath = _spaRedirect.replace(/^\\/dev_beta/, '') || '/';\n"
    "  const _redirectPage = ROUTE_PAGES[_routePath] || 'etfurl';\n"
    "  history.replaceState(null, '', _spaRedirect);\n"
    "  showPage(_redirectPage, { pushState: false });\n"
    "} else {\n"
    "  // 直接輸入路徑或刷新\n"
    "  const _initPath = location.pathname.replace(/^\\/dev_beta/, '') || '/';\n"
    "  const _initPage = ROUTE_PAGES[_initPath];\n"
    "  if (_initPage) showPage(_initPage, { pushState: false });"
)
if OLD_SPA in html:
    html = html.replace(OLD_SPA, NEW_SPA)
    print('[OK] SPA redirect 路由查找 → 支援 /dev_beta/ 刷新')
else:
    errors.append('SPA redirect 替換失敗，格式可能已變更')

# 3. 頁面初始隱藏，防止未授權用戶看到內容閃現
OLD_BODY = '<body>'
NEW_BODY = '<body style="visibility:hidden;">'
if OLD_BODY in html:
    html = html.replace(OLD_BODY, NEW_BODY, 1)
    print('[OK] body 初始隱藏 → 防止內容閃現')
else:
    errors.append('<body> 替換失敗')

# 4. 注入 UID 白名單 + 密碼驗證
allowed_uids_js = str(ALLOWED_UIDS).replace("'", '"')
OLD_AUTH = "  onAuthStateChanged(auth, user => {\n    currentUser = user;"
NEW_AUTH = (
    f"  const _DEV_ALLOWED = {allowed_uids_js};\n"
    "  onAuthStateChanged(auth, user => {\n"
    "    // 第一層：UID 白名單\n"
    "    if (!user || !_DEV_ALLOWED.includes(user.uid)) {\n"
    "      document.body.innerHTML = `\n"
    "        <div style=\"display:flex;align-items:center;justify-content:center;height:100vh;\n"
    "          background:#0d1117;color:#8b949e;font-family:sans-serif;flex-direction:column;gap:12px;\">\n"
    "          <div style=\"font-size:48px;\">🔒</div>\n"
    "          <div style=\"font-size:18px;color:#e6edf3;\">此頁面僅限授權人員存取</div>\n"
    "          <div style=\"font-size:13px;\">dev_beta 測試環境</div>\n"
    "        </div>`;\n"
    "      document.body.style.visibility = 'visible';\n"
    "      return;\n"
    "    }\n"
    "    // 第二層：密碼驗證（Firestore）\n"
    "    if (sessionStorage.getItem('_devAccessGranted') !== 'true') {\n"
    "      document.body.style.visibility = 'visible';\n"
    "      document.getElementById('_devPasswordOverlay').style.display = 'flex';\n"
    "      const _inputEl  = document.getElementById('_devPasswordInput');\n"
    "      const _submitEl = document.getElementById('_devPasswordSubmit');\n"
    "      const _errEl    = document.getElementById('_devPasswordErr');\n"
    "      const _doVerify = async () => {\n"
    "        const _input = _inputEl.value.trim();\n"
    "        _errEl.textContent = '';\n"
    "        _submitEl.disabled = true;\n"
    "        _submitEl.textContent = '驗證中...';\n"
    "        try {\n"
    "          const _snap = await getDoc(doc(db, 'dev_config', 'access_code'));\n"
    "          if (_input === String(_snap.data()?.code)) {\n"
    "            sessionStorage.setItem('_devAccessGranted', 'true');\n"
    "            location.reload();\n"
    "          } else {\n"
    "            _errEl.textContent = '密碼錯誤，請再試一次';\n"
    "            _inputEl.value = '';\n"
    "            _inputEl.focus();\n"
    "            _submitEl.disabled = false;\n"
    "            _submitEl.textContent = '驗證';\n"
    "          }\n"
    "        } catch(e) {\n"
    "          _errEl.textContent = '驗證失敗，請重試';\n"
    "          _submitEl.disabled = false;\n"
    "          _submitEl.textContent = '驗證';\n"
    "        }\n"
    "      };\n"
    "      _submitEl.onclick = _doVerify;\n"
    "      _inputEl.addEventListener('keydown', e => { if (e.key === 'Enter') _doVerify(); });\n"
    "      _inputEl.focus();\n"
    "      return;\n"
    "    }\n"
    "    document.body.style.visibility = 'visible';\n"
    "    currentUser = user;"
)
if OLD_AUTH in html:
    html = html.replace(OLD_AUTH, NEW_AUTH)
    print('[OK] UID 白名單 + 密碼驗證 → 已注入')
else:
    errors.append('onAuthStateChanged 注入失敗，格式可能已變更')

# 5. 注入密碼輸入 Overlay HTML
OVERLAY_HTML = """
<div id="_devPasswordOverlay" style="display:none;position:fixed;inset:0;background:#0d1117;
  z-index:99999;align-items:center;justify-content:center;flex-direction:column;gap:16px;
  font-family:'Noto Sans TC',sans-serif;">
  <div style="font-size:40px;">🔑</div>
  <div style="color:#e6edf3;font-size:18px;font-weight:600;">dev_beta 存取驗證</div>
  <div style="color:#8b949e;font-size:13px;">請輸入存取碼</div>
  <input id="_devPasswordInput" type="password" placeholder="存取碼"
    style="background:#161b22;border:1px solid #30363d;border-radius:8px;color:#e6edf3;
      font-size:18px;padding:12px 20px;outline:none;width:220px;text-align:center;
      letter-spacing:6px;margin-top:4px;">
  <button id="_devPasswordSubmit"
    style="background:#58a6ff;border:none;border-radius:8px;color:#0d1117;font-size:14px;
      font-weight:600;padding:10px 32px;cursor:pointer;font-family:inherit;">
    驗證
  </button>
  <div id="_devPasswordErr" style="color:#f85149;font-size:13px;min-height:18px;"></div>
</div>
"""
if '</body>' in html:
    html = html.replace('</body>', OVERLAY_HTML + '</body>')
    print('[OK] 密碼輸入 Overlay → 已注入')
else:
    errors.append('</body> 找不到，Overlay 注入失敗')

if errors:
    for e in errors:
        print(f'[WARN] {e}')

with open(target, 'w', encoding='utf-8') as f:
    f.write(html)

print('[OK] dev_beta/index.html 轉換完成')
