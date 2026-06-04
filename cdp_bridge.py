"""
CDP Bridge - 通过 Chrome DevTools Protocol 直接操控 Chrome 浏览器
替代 TMWebDriver 的扩展方案，不需要 Chrome 扩展的 service worker。

使用方式：
1. 启动 Chrome with --remote-debugging-port=9222（离屏隐身）
2. 导入：from cdp_bridge import CDPDriver
3. driver = CDPDriver(port=9222)
4. 提供与 TMWebDriver 兼容的接口：execute_js, get_all_sessions, get_session_dict
"""

import json, time, urllib.request, urllib.parse
import websocket  # websocket-client

CDP_PORT = 9222

def cdp_http(path):
    """CDP HTTP 端点请求"""
    url = f"http://127.0.0.1:{CDP_PORT}{path}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())

def cdp_ws_call(ws_url, method, params=None, timeout=30):
    """通过 CDP WebSocket 发送命令并等待结果"""
    ws = websocket.create_connection(ws_url, timeout=timeout, suppress_origin=True)
    try:
        cmd = {"id": 1, "method": method}
        if params: cmd["params"] = params
        ws.send(json.dumps(cmd))
        while True:
            resp = json.loads(ws.recv())
            if resp.get("id") == 1:
                if "error" in resp:
                    raise RuntimeError(f"CDP error: {resp['error']}")
                return resp.get("result", {})
    finally:
        ws.close()

class CDPSession:
    """单个 Chrome 标签页的 CDP 会话"""
    def __init__(self, page_info):
        self.id = page_info["id"]
        self.url = page_info.get("url", "")
        self.title = page_info.get("title", "")
        self.ws_url = page_info["webSocketDebuggerUrl"]
        self._connected_at = time.time()
    
    def execute_js(self, expression, timeout=30):
        """执行 JS 表达式，返回 {"data": result}。
        兼容顶层 return 语句：自动提取最后一个 return 的表达式作为求值目标。
        """
        import re
        js = expression.strip()
        # 检测是否有顶层 return
        # 策略：如果 JS 以 function/var/let/const 开头且包含 return，
        # 则把最后一个 "return <expr>;" 替换为 "<expr>" 作为求值表达式
        has_return = bool(re.search(r'\breturn\b', js))
        if has_return:
            # 找最后一个 return 语句
            # 匹配 "return <expr>;" 或 "return <expr>" 在末尾
            m = re.search(r'\breturn\s+(.+?)\s*;?\s*$', js)
            if m:
                # 提取 return 后面的表达式
                return_expr = m.group(1).rstrip(';').strip()
                # 前面的定义部分作为脚本先执行（通过 ; 分隔）
                prefix = js[:m.start()].strip()
                if prefix:
                    # 先执行定义，再求值表达式
                    combined = f"{prefix};\n{return_expr}"
                    js = combined
                else:
                    js = return_expr
        try:
            result = cdp_ws_call(
                self.ws_url,
                "Runtime.evaluate",
                {"expression": js, "awaitPromise": True, "returnByValue": True},
                timeout=timeout
            )
            val = result.get("result", {})
            if val.get("subtype") == "error":
                return {"data": None, "error": val.get("description", "JS error")}
            return {"data": val.get("value")}
        except Exception as e:
            return {"data": None, "error": str(e)}
    
    def navigate(self, url, timeout=30):
        """导航到 URL"""
        return cdp_ws_call(self.ws_url, "Page.navigate", {"url": url}, timeout=timeout)
    
    def to_dict(self):
        """返回兼容 TMWebDriver session 的 dict"""
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "connected_at": self._connected_at,
        }


class CDPDriver:
    """
    兼容 TMWebDriver 接口的 CDP 驱动。
    simphtml.py 通过 driver 调用的方法都在这里实现。
    """
    def __init__(self, port=CDP_PORT):
        self.port = port
        self._sessions = {}
        self.default_session_id = None
        self.latest_session_id = None
        self._refresh_sessions()
    
    def _refresh_sessions(self):
        """从 CDP /json/list 刷新标签页列表"""
        try:
            pages = cdp_http("/json/list")
            # 只取页面类型（排除 service worker 等）
            page_list = [p for p in pages if p.get("type") == "page" and p.get("webSocketDebuggerUrl")]
            self._sessions = {}
            for p in page_list:
                sid = p["id"]
                self._sessions[sid] = CDPSession(p)
            if self._sessions:
                if self.default_session_id not in self._sessions:
                    self.default_session_id = list(self._sessions.keys())[0]
                self.latest_session_id = list(self._sessions.keys())[-1]
        except Exception as e:
            print(f"[CDPDriver] 刷新 sessions 失败: {e}")
    
    def get_all_sessions(self):
        """返回所有 session 的 dict 列表（兼容 TMWebDriver）"""
        self._refresh_sessions()
        result = []
        for sid, sess in self._sessions.items():
            d = sess.to_dict()
            result.append(d)
        return result
    
    def execute_js(self, expression, timeout=30):
        """在当前默认 session 上执行 JS，自动处理 session 失效"""
        if not self._sessions:
            return {"data": None, "error": "没有可用的标签页"}
        sid = self.default_session_id
        if sid not in self._sessions:
            self._refresh_sessions()
        if sid not in self._sessions:
            return {"data": None, "error": f"session {sid} 不存在"}
        result = self._sessions[sid].execute_js(expression, timeout=timeout)
        # 自动处理 "No such target" — 刷新 sessions 后重试一次
        if result.get("error") and "No such target" in str(result["error"]):
            self._refresh_sessions()
            if self.default_session_id and self.default_session_id in self._sessions:
                result = self._sessions[self.default_session_id].execute_js(expression, timeout=timeout)
        return result
    
    def get_session_dict(self):
        """返回当前 session 的 dict（兼容 TMWebDriver）"""
        if not self.default_session_id or self.default_session_id not in self._sessions:
            self._refresh_sessions()
        if self.default_session_id and self.default_session_id in self._sessions:
            return self._sessions[self.default_session_id].to_dict()
        return {}
    
    def navigate(self, url, timeout=30):
        """在当前默认 session 上导航，自动等待页面加载并处理 session 变更"""
        if not self._sessions:
            return None
        sid = self.default_session_id
        if sid in self._sessions:
            result = self._sessions[sid].navigate(url, timeout=timeout)
            # 等待页面加载并监测 session 变更 (最多5秒)
            import time as _time
            for _ in range(10):
                _time.sleep(0.5)
                self._refresh_sessions()
                # 检查旧 session 是否还在（URL 可能已更新）
                if sid in self._sessions and self._sessions[sid].url != "chrome://newtab/":
                    break
                # 检查是否有新 session（旧 session 可能已被替换）
                if sid not in self._sessions and self.default_session_id and self.default_session_id in self._sessions:
                    break
            return result
        return None


def start_chrome(port=CDP_PORT, headless=True):
    """
    启动 Chrome with --remote-debugging-port（离屏隐身）
    headless=True: 用 --window-position=-32000,-32000 离屏（不弹窗口）
    """
    import subprocess, os
    
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    if not os.path.exists(chrome_path):
        raise FileNotFoundError(f"Chrome not found: {chrome_path}")
    
    # 用临时用户目录（隐身效果，不加载用户 profile）
    user_data_dir = os.path.join(os.environ.get("TEMP", "."), f"chrome_cdp_profile_{port}")
    
    cmd = [
        chrome_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-features=TranslateUI",
        "--remote-allow-origins=*",
    ]
    
    if headless:
        # 离屏隐身：窗口在屏幕外
        cmd.append("--window-position=-32000,-32000")
        cmd.append("--disable-gpu")
    
    # 启动 Chrome（不等待）
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # 等待 CDP 端口可用
    import socket
    for i in range(30):
        try:
            s = socket.socket()
            s.settimeout(1)
            s.connect(("127.0.0.1", port))
            s.close()
            print(f"[CDPDriver] Chrome CDP 端口 {port} 已就绪")
            time.sleep(2)  # 等 Chrome 完全初始化
            return True
        except:
            time.sleep(1)
    
    raise RuntimeError(f"Chrome CDP 端口 {port} 启动超时")


if __name__ == "__main__":
    # 测试：启动 Chrome 并获取页面列表
    print("启动 Chrome CDP...")
    start_chrome(port=CDP_PORT, headless=True)
    
    driver = CDPDriver(port=CDP_PORT)
    sessions = driver.get_all_sessions()
    print(f"找到 {len(sessions)} 个标签页:")
    for s in sessions:
        print(f"  [{s['id']}] {s['title'][:50]} - {s['url'][:80]}")
    
    # 导航到百度测试
    if sessions:
        print("\n导航到百度...")
        driver.navigate("https://www.baidu.com")
        time.sleep(2)
        
        # 获取页面标题
        result = driver.execute_js("document.title")
        print(f"页面标题: {result.get('data')}")
        
        # 获取简化 HTML
        result = driver.execute_js("document.body.innerText.substring(0, 500)")
        print(f"页面内容: {result.get('data', '')[:200]}")
    
    print("\nCDP Bridge 测试完成!")
