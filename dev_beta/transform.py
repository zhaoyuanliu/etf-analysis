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

# 4. 注入 UID 白名單檢查
allowed_uids_js = str(ALLOWED_UIDS).replace("'", '"')
OLD_AUTH = "  onAuthStateChanged(auth, user => {\n    currentUser = user;"
NEW_AUTH = (
    f"  const _DEV_ALLOWED = {allowed_uids_js};\n"
    "  onAuthStateChanged(auth, user => {\n"
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
    "    document.body.style.visibility = 'visible';\n"
    "    currentUser = user;"
)
if OLD_AUTH in html:
    html = html.replace(OLD_AUTH, NEW_AUTH)
    print('[OK] UID 白名單保護 → 已注入')
else:
    errors.append('onAuthStateChanged 注入失敗，格式可能已變更')

if errors:
    for e in errors:
        print(f'[WARN] {e}')

with open(target, 'w', encoding='utf-8') as f:
    f.write(html)

print('[OK] dev_beta/index.html 轉換完成')
