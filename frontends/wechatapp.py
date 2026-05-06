import os, sys, re, threading, queue, time, socket, json, struct, base64, uuid, webbrowser, hashlib, math, urllib.request
from pathlib import Path
from urllib.parse import quote

import requests, qrcode
import socket as _socket

_API_HOST = 'ilinkai.weixin.qq.com'

# Use system proxy (verge-mihomo at 127.0.0.1:7897) — do NOT clear proxy env vars.
# The proxy handles DNS resolution and SNI correctly, avoiding WFP hijacking.

from Crypto.Cipher import AES
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'temp')
from agentmain import GeneraticAgent

# ── WxBotClient (inline from wx_bot_client.py) ──
API     = f'https://{_API_HOST}'
TOKEN_FILE = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / 'temp' / 'wxbot_token.json'
TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
VER, MSG_USER, MSG_BOT, ITEM_TEXT, STATE_FINISH = '2.1.10', 1, 2, 1, 2
ILINK_APP_ID = 'bot'
ILINK_APP_CLIENT_VERSION = (2 << 16) | (1 << 8) | 10
UA = f'openclaw-weixin/{VER}'
ITEM_IMAGE, ITEM_FILE, ITEM_VIDEO = 2, 4, 5
CDN_BASE = 'https://novac2c.cdn.weixin.qq.com/c2c'

def _uin():
    return base64.b64encode(str(struct.unpack('>I', os.urandom(4))[0]).encode()).decode()

class WxBotClient:
    def __init__(self, token=None, token_file=None):
        self._tf = Path(token_file) if token_file else TOKEN_FILE
        self.token = token
        self.bot_id = None
        self._buf = ''
        if not self.token: self._load()

    def _load(self):
        if self._tf.exists():
            d = json.loads(self._tf.read_text('utf-8'))
            self.token, self.bot_id, self._buf = d.get('bot_token',''), d.get('ilink_bot_id',''), d.get('updates_buf','')

    def _save(self, **kw):
        d = {'bot_token': self.token or '', 'ilink_bot_id': self.bot_id or '',
             'updates_buf': self._buf or '', **kw}
        self._tf.write_text(json.dumps(d, ensure_ascii=False, indent=2), 'utf-8')

    def _post(self, ep, body, timeout=15):
        data = json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        h = {'Content-Type': 'application/json', 'AuthorizationType': 'ilink_bot_token',
             'Content-Length': str(len(data)), 'X-WECHAT-UIN': _uin(),
             'iLink-App-Id': ILINK_APP_ID,
             'iLink-App-ClientVersion': str(ILINK_APP_CLIENT_VERSION),
             'User-Agent': UA}
        tok = (self.token or '').strip()
        if tok: h['Authorization'] = f'Bearer {tok}'
        r = requests.post(f'{API}/{ep}', data=data, headers=h, timeout=timeout)
        r.raise_for_status()
        return r.json()

    def login_qr(self, poll_interval=2):
        r = requests.get(f'{API}/ilink/bot/get_bot_qrcode', params={'bot_type': 3}, headers={'User-Agent': UA}, timeout=10)
        r.raise_for_status()
        d = r.json()
        qr_id, url = d['qrcode'], d.get('qrcode_img_content', '')
        print(f'[QR登录] ID: {qr_id}')
        if url:
            img = self._tf.parent / 'wx_qr.png'
            qrcode.make(url).save(str(img)); webbrowser.open(str(img))
            qr = qrcode.QRCode(border=1); qr.add_data(url); qr.make(fit=True); qr.print_ascii(invert=True)
        last = ''
        while True:
            time.sleep(poll_interval)
            try: s = requests.get(f'{API}/ilink/bot/get_qrcode_status', params={'qrcode': qr_id}, headers={'User-Agent': UA}, timeout=60).json()
            except requests.exceptions.ReadTimeout: continue
            st = s.get('status', '')
            if st != last: print(f'  状态: {st}'); last = st
            if st == 'confirmed':
                self.token, self.bot_id = s.get('bot_token', ''), s.get('ilink_bot_id', '')
                self._save(login_time=time.strftime('%Y-%m-%d %H:%M:%S'))
                print(f'[QR登录] 成功! bot_id={self.bot_id}')
                return s
            if st == 'expired': raise RuntimeError('二维码过期')

    def get_updates(self, timeout=30):
        try:
            resp = self._post('ilink/bot/getupdates',
                              {'get_updates_buf': self._buf or '',
                               'base_info': {}},
                              timeout=timeout + 5)
        except requests.exceptions.ReadTimeout:
            return []
        except (requests.exceptions.ConnectionError,
                requests.exceptions.ChunkedEncodingError,
                ConnectionResetError,
                OSError) as e:
            # 网络层异常：DNS失败/连接断开/远端关闭 → 返回空，由上层退避重连
            print(f'[getUpdates] 网络异常: {type(e).__name__}: {e}', file=sys.__stdout__)
            return []
        except Exception as e:
            print(f'[getUpdates] 未知异常: {type(e).__name__}: {e}', file=sys.__stdout__)
            return []
        if resp.get('errcode'):
            print(f'[getUpdates] err: {resp.get("errcode")} {resp.get("errmsg","")}')
            if resp['errcode'] == -14: self._save()
            return []
        nb = resp.get('get_updates_buf', '')
        if nb: self._buf = nb; self._save()
        return resp.get('msgs') or []

    def send_text(self, to_user_id, text, context_token=''):
        # 统一微信格式化：去 Markdown 符号 + \n → \u2028 换行
        text = _fmt_wx(text) if text else text
        msg = {'from_user_id': '', 'to_user_id': to_user_id,
               'client_id': f'pyclient-{uuid.uuid4().hex[:16]}',
               'message_type': MSG_BOT, 'message_state': STATE_FINISH,
               'item_list': [{'type': ITEM_TEXT, 'text_item': {'text': text}}]}
        if context_token: msg['context_token'] = context_token
        return self._post('ilink/bot/sendmessage', {'msg': msg, 'base_info': {'channel_version': VER}})

    def send_typing(self, to_user_id, typing_ticket='', cancel=False):
        return self._post('ilink/bot/sendtyping', {
            'ilink_user_id': to_user_id, 'typing_ticket': typing_ticket,
            'status': 2 if cancel else 1,
            'base_info': {'channel_version': VER}})

    def _enc(self, raw, aes_key):
        pad = 16 - (len(raw) % 16)
        return AES.new(aes_key, AES.MODE_ECB).encrypt(raw + bytes([pad] * pad))

    def _upload(self, filekey, upload_param, raw, aes_key, timeout=120, upload_url=''):
        url = upload_url.strip() if upload_url else f'{CDN_BASE}/upload?encrypted_query_param={quote(upload_param)}&filekey={filekey}'
        data = self._enc(raw, aes_key)
        last_err = None
        for attempt in range(1, 4):
            try:
                r = requests.post(url, data=data, headers={'Content-Type': 'application/octet-stream', 'User-Agent': UA}, timeout=timeout)
                if 400 <= r.status_code < 500:
                    msg = r.headers.get('x-error-message') or r.text[:300]
                    raise RuntimeError(f'CDN upload client error {r.status_code}: {msg}')
                if r.status_code != 200:
                    msg = r.headers.get('x-error-message') or f'status {r.status_code}'
                    raise RuntimeError(f'CDN upload server error: {msg}')
                eq = r.headers.get('x-encrypted-param', '')
                if not eq: raise RuntimeError('CDN upload response missing x-encrypted-param header')
                return {'encrypt_query_param': eq,
                        'aes_key': base64.b64encode(aes_key.hex().encode()).decode(), 'encrypt_type': 1}
            except Exception as e:
                last_err = e
                if 'client error' in str(e) or attempt >= 3: break
                print(f'[WX] CDN upload retry {attempt}: {e}', file=sys.__stdout__)
        raise last_err

    def _send_media(self, to_user_id, file_path, media_type, item_type, item_key, context_token=''):
        fp = Path(file_path)
        raw = fp.read_bytes()
        filekey = uuid.uuid4().hex
        aes_key = os.urandom(16)
        ciphertext_size = ((len(raw) // 16) + 1) * 16
        thumb_raw = b''; thumb_w = thumb_h = 0; thumb_ciphertext_size = 0
        if item_key == 'image_item':
            from io import BytesIO
            from PIL import Image
            im = Image.open(fp); im.thumbnail((240, 240))
            thumb_w, thumb_h = im.size
            if im.mode not in ('RGB', 'L'):
                im = im.convert('RGB')
            bio = BytesIO(); im.save(bio, format='JPEG', quality=85)
            thumb_raw = bio.getvalue()
            thumb_ciphertext_size = ((len(thumb_raw) // 16) + 1) * 16
        body = {
            'filekey': filekey, 'media_type': media_type, 'to_user_id': to_user_id,
            'rawsize': len(raw), 'rawfilemd5': hashlib.md5(raw).hexdigest(),
            'filesize': ciphertext_size,
            'no_need_thumb': item_key not in ('image_item', 'video_item'),
            'aeskey': aes_key.hex(), 'base_info': {'channel_version': VER}}
        if thumb_raw:
            body.update({'thumb_rawsize': len(thumb_raw),
                         'thumb_rawfilemd5': hashlib.md5(thumb_raw).hexdigest(),
                         'thumb_filesize': thumb_ciphertext_size})
        resp = self._post('ilink/bot/getuploadurl', body)
        upload_param = resp.get('upload_param', '')
        upload_url = resp.get('upload_full_url', '')
        if not (upload_param or upload_url): raise RuntimeError(f'getuploadurl failed: {resp}')
        media = self._upload(filekey, upload_param, raw, aes_key=aes_key, upload_url=upload_url)
        item = {'media': media}
        if item_key == 'file_item':
            item.update({'file_name': fp.name, 'len': str(len(raw))})
        elif item_key == 'image_item':
            thumb_param = resp.get('thumb_upload_param', '')
            thumb_url = resp.get('thumb_upload_full_url', '')
            if thumb_param or thumb_url:
                thumb_media = self._upload(filekey, thumb_param, thumb_raw, aes_key=aes_key, upload_url=thumb_url)
                thumb_size = thumb_ciphertext_size
            else:
                # Some getuploadurl responses only return a single upload_full_url for IMAGE.
                # Keep ImageItem structurally complete by reusing the original CDN media as thumb_media.
                thumb_media = media
                thumb_size = ciphertext_size
            item.update({'mid_size': ciphertext_size, 'thumb_media': thumb_media,
                         'thumb_size': thumb_size,
                         'thumb_width': thumb_w, 'thumb_height': thumb_h})
        elif item_key == 'video_item':
            item.update({'video_size': ciphertext_size})
        msg = {'from_user_id': '', 'to_user_id': to_user_id,
               'client_id': f'pyclient-{uuid.uuid4().hex[:16]}',
               'message_type': MSG_BOT, 'message_state': STATE_FINISH,
               'item_list': [{'type': item_type, item_key: item}]}
        if context_token: msg['context_token'] = context_token
        return self._post('ilink/bot/sendmessage', {'msg': msg, 'base_info': {'channel_version': VER}})

    def send_file(self, to_user_id, file_path, context_token=''):
        return self._send_media(to_user_id, file_path, 3, ITEM_FILE, 'file_item', context_token)

    def send_image(self, to_user_id, file_path, context_token=''):
        return self._send_media(to_user_id, file_path, 1, ITEM_IMAGE, 'image_item', context_token)

    def send_video(self, to_user_id, file_path, context_token=''):
        return self._send_media(to_user_id, file_path, 2, ITEM_VIDEO, 'video_item', context_token)

    @staticmethod
    def extract_text(msg):
        return '\n'.join(it['text_item'].get('text', '')
                         for it in msg.get('item_list', [])
                         if it.get('type') == ITEM_TEXT and it.get('text_item'))

    @staticmethod
    def is_user_msg(msg): return msg.get('message_type') == MSG_USER

    def run_loop(self, on_message, poll_timeout=30):
        print(f'[Bot] 监听中... (bot_id={self.bot_id})')
        seen = set()
        retry_delay = 1          # 初始退避 1s
        max_retry_delay = 60     # 最大退避 60s
        while True:
            try:
                for msg in self.get_updates(poll_timeout):
                    mid = msg.get('message_id', 0)
                    if not self.is_user_msg(msg) or mid in seen: continue
                    seen.add(mid)
                    if len(seen) > 5000: seen = set(list(seen)[-2000:])
                    try: on_message(self, msg)
                    except Exception as e: print(f'[Bot] 回调异常: {e}')
                # 成功拉取一轮后退避重置
                retry_delay = 1
            except KeyboardInterrupt: print('[Bot] 退出'); break
            except Exception as e:
                print(f'[Bot] 异常: {type(e).__name__}: {e}，{retry_delay}s后重试', file=sys.__stdout__)
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_retry_delay)

# ── Unified media download (IMAGE/VIDEO/FILE/VOICE) ──
_MEDIA_KEYS = {'image_item': '.jpg', 'video_item': '.mp4', 'file_item': '', 'voice_item': '.silk'}

def _dl_media(items):
    """Download & decrypt all media items → list of local file paths."""
    paths = []
    for item in items:
        for key, ext in _MEDIA_KEYS.items():
            sub = item.get(key)
            if not sub: continue
            eq = (sub.get('media') or {}).get('encrypt_query_param')
            if not eq: continue
            ak = (sub.get('media') or {}).get('aes_key', '') or sub.get('aeskey', '')
            if not ak: continue
            try:
                aes_key = (bytes.fromhex(base64.b64decode(ak).decode())
                           if sub.get('media', {}).get('aes_key') else bytes.fromhex(ak))
                ct = requests.get(f'{CDN_BASE}/download?encrypted_query_param={quote(eq)}', headers={'User-Agent': UA}, timeout=60).content
                pt = AES.new(aes_key, AES.MODE_ECB).decrypt(ct); pt = pt[:-pt[-1]]
                fname = sub.get('file_name') or f'{uuid.uuid4().hex[:8]}{ext or ".bin"}'
                p = os.path.join(_TEMP_DIR, fname); open(p, 'wb').write(pt)
                paths.append(p); print(f'[WX] media saved: {fname}', file=sys.__stdout__)
            except Exception as e:
                print(f'[WX] media dl err ({key}): {e}', file=sys.__stdout__)
            break  # one media per item
    return paths

agent = GeneraticAgent()
agent.verbose = False

_TAG_PATS = [r'<' + t + r'>.*?</' + t + r'>' for t in ('thinking', 'tool_use')]
_TAG_PATS.append(r'<file_content>.*?</file_content>')

def _fmt_wx(t, already_has_unicode_nl=False):
    """统一微信消息格式化：把任意文本转成微信友好的纯文本格式。
    参数：
        already_has_unicode_nl: 如果文本已包含 \u2028 换行，就不再转换 \n
    处理：
    1. 去掉 Markdown 符号（**粗体**、`代码`、~~删除线~~）
    2. 表格 → 列表形式
    3. 标题加 emoji 前缀
    4. \n → \u2028（微信唯一有效的换行符）
    """
    if not t:
        return ''
    # 去掉代码块（微信不渲染）
    t = re.sub(r'```[\s\S]*?```', '[代码已省略]', t)
    # 去掉行内代码反引号，保留内容
    t = re.sub(r'`([^`\n]+)`', r'\1', t)
    # 去掉粗体/斜体符号
    t = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', t)
    t = re.sub(r'_{1,3}([^_]+)_{1,3}', r'\1', t)
    # 删除线
    t = re.sub(r'~~([^~]+)~~', r'\1', t)
    # 图片 → emoji
    t = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'🖼️ [\1]', t)
    # 链接 → 文字+🔗
    t = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'\1 🔗', t)
    # 标题加 emoji
    t = re.sub(r'^#{1}\s+(.+)', r'📌 \1', t, flags=re.M)
    t = re.sub(r'^#{2}\s+(.+)', r'🔹 \1', t, flags=re.M)
    t = re.sub(r'^#{3}\s+(.+)', r'▪️ \1', t, flags=re.M)
    t = re.sub(r'^#{4,6}\s+(.+)', r'• \1', t, flags=re.M)
    # 无序列表
    t = re.sub(r'^\s*[-*+]\s+', '  • ', t, flags=re.M)
    # 有序列表保持
    t = re.sub(r'^(\s*)(\d+)\.\s+', r'\1\2. ', t, flags=re.M)
    # 引用
    t = re.sub(r'^\s*>\s?(.+)', r'│ \1', t, flags=re.M)
    # 水平线
    t = re.sub(r'^\s*[-*_]{3,}\s*$', '━' * 15, t, flags=re.M)
    # 表格处理：把 | col1 | col2 | 行转成 "col1: col2" 格式
    lines = t.split('\n')
    result = []
    for line in lines:
        stripped = line.strip()
        # 跳过分隔行 |---|---|
        if re.match(r'^\|?[\s\-:|]+\|?$', stripped):
            result.append('─' * 10)
            continue
        # 表格行 | a | b | c |
        if stripped.startswith('|') and stripped.endswith('|'):
            cells = [c.strip() for c in stripped.strip('|').split('|')]
            cells = [c for c in cells if c]
            if cells:
                if len(cells) == 2:
                    result.append(f'{cells[0]}: {cells[1]}')
                else:
                    result.append(' │ '.join(cells))
            continue
        result.append(line)
    t = '\n'.join(result)
    # 清理多余空行
    t = re.sub(r'\n{3,}', '\n\n', t).strip()
    # ★ 关键：\n → \u2028（微信唯一有效换行）
    # 如果文本已经包含 \u2028（如快速通道天气），只转换剩余的 \n
    if already_has_unicode_nl:
        # 已经有 \u2028 的文本，把剩余的普通 \n 也转掉
        t = t.replace('\n', '\u2028')
    else:
        t = t.replace('\n', '\u2028')
    return t


def _strip_md(t):
    """兼容旧调用，转调 _fmt_wx。"""
    return _fmt_wx(t)

def _fmt_wx(t):
    """格式化 LLM 输出为微信友好的纯文本：去掉 Markdown、保留 emoji、结构清晰。"""
    # === Phase 1: 删除内部/代码大块结构 ===
    t = re.sub(r'<summary>.*?</summary>', '', t, flags=re.DOTALL)
    t = re.sub(r'```[\w]*\n.*?```', '', t, flags=re.DOTALL)
    t = re.sub(r'`[^`\n]{3,}`', '', t)
    t = re.sub(r'\{\s*["\']status["\'].*?\}', '', t, flags=re.DOTALL)
    t = re.sub(r'^\s*={3,}\s*(Response|Prompt)\s*={3,}\s*$', '', t, flags=re.M)
    t = re.sub(r'^\s*🛠️\s*\w+\(.*', '', t, flags=re.M | re.DOTALL)
    t = re.sub(r'^\s*🔧\s*\w+\(.*', '', t, flags=re.M | re.DOTALL)
    t = re.sub(r'^\s*(调用工具\w+|读取文件\s+\S+|写入文件\s+\S+|执行脚本\s+\S+).*$', '', t, flags=re.M)
    t = re.sub(r'^\s*args:\s*\{.*$', '', t, flags=re.M)
    t = re.sub(r'^\s*LLM Running \(Turn \d+\) \.{3}\s*$', '', t, flags=re.M)
    t = re.sub(r'^\s*(\[Driver\].*|\[CDP\].*|\[Timeout.*\].*|Executing:.*|Timeout Error.*|Error:.*|Traceback.*)$', '', t, flags=re.M)
    for p in _TAG_PATS:
        t = re.sub(p, '', t, flags=re.DOTALL)
    t = re.sub(r'^\s*["\'](exit_code|stdout|stderr)["\'].*$', '', t, flags=re.M)
    t = re.sub(r'^\s*⏳\s*思考中\s*[█░]+\s*\d+/\d+\s*$', '', t, flags=re.M)
    t = re.sub(r'⏳.*', '', t)
    t = re.sub(r'^✅\s*回复完成\s*$', '', t, flags=re.M)

    # === Phase 2: 去掉 Markdown 格式标记，保留文字内容 ===
    # 去掉标题标记 # ## ###
    t = re.sub(r'^#{1,6}\s+', '', t, flags=re.M)
    # 去掉表格行 | xxx | yyy | → 保留内容用空格分隔
    def _table_row(m):
        cells = [c.strip() for c in m.group(0).split('|') if c.strip()]
        if not cells: return ''
        # 如果全是分隔符 (---)，跳过
        if all(re.match(r'^[-:]+$', c) for c in cells): return ''
        return ' '.join(cells)
    t = re.sub(r'^\|.*\|$', _table_row, t, flags=re.M)
    # 去掉分隔线 ━━━━ ━━━━━ ---- ====
    t = re.sub(r'^[━─=\-]{4,}\s*$', '', t, flags=re.M)
    # 去掉列表标记 - * ▪ • ● → 保留内容
    t = re.sub(r'^(\s*)[-*▪•●]\s+', r'\1', t, flags=re.M)
    # 去掉有序列表 1. 2. → 保留内容
    t = re.sub(r'^(\s*)\d+\.\s+', r'\1', t, flags=re.M)
    # 去掉加粗 **xxx** __xxx__
    t = re.sub(r'\*\*(.+?)\*\*', r'\1', t)
    t = re.sub(r'__(.+?)__', r'\1', t)
    # 去掉斜体 *xxx* _xxx_
    t = re.sub(r'\*(.+?)\*', r'\1', t)
    t = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'\1', t)
    # 去掉行内代码 `xxx`
    t = re.sub(r'`([^`]+)`', r'\1', t)

    # === Phase 3: 删除 LLM 内部推理/元评论 ===
    _reasoning_prefixes = (
        '让我先', '让我看看', '先读', '继续读', '全部完成', '所有工作',
        '好的，', '我来', '我将', '我需要', '我直接', '我看看',
        '上次', '用户再次', '用户指出', '用户查询',
        '搜索工具', '浏览器', 'web工具', 'DDGS',
        '抱歉', '对不起',
        '还是需要', '还是需要优化', '还是需要调整', '还是需要修复',
        '还是优化', '还是需要', '应该优化', '应该调整', '应该修复', '应该改用',
        '那备份', '那我', '那就',
    )
    _reasoning_contains = (
        ('搜索', '返回'), ('搜索', '结果'), ('搜索', '为空'),
        ('浏览器', '没开'), ('浏览器', '不可用'),
        ('工具', '返回'), ('工具', '结果'), ('工具', '不可用'),
        ('DDGS', '更名'), ('DDGS', '包名'),
        ('返回', '为空'), ('返回', '结果'),
    )
    lines = t.split('\n')
    filtered = []
    for line in lines:
        s = line.strip()
        if any(s.startswith(p) for p in _reasoning_prefixes):
            continue
        if any(kw1 in s and kw2 in s for kw1, kw2 in _reasoning_contains):
            continue
        filtered.append(line)
    t = '\n'.join(filtered)

    # === Phase 4: 删除代码行 ===
    code_patterns = [
        r'import\s+[\w,. ]+', r'from\s+[\w.]+', r'def\s+\w+', r'class\s+\w+',
        r'if\s+\w+.*:', r'for\s+\w+.*:', r'while\s+.*:', r'try:', r'except\b',
        r'else:', r'elif\s+.*:', r'with\s+.*:', r'return\s+', r'^\s*#\s+',
        r'console\.\w+\(', r'window\.\w+',
        r'^\s*\w+\s*=\s*(urllib|requests|http|json|re|os|sys|subprocess)\b',
        r'^\s*\w+\s*=\s*\w+\.(get|post|put|delete|findall|search|sub|match)\(',
        r'^\s*\w+\s*=\s*[\w.]+\(.*\)\s*$', r'^\s*\w+\.\w+\(.*\)\s*$',
        r'^\s*print\(.*\)\s*$',
    ]
    combined = '|'.join(code_patterns)
    for _ in range(5):
        t = re.sub(r'^(' + combined + r').*$', '', t, flags=re.M)

    # === Phase 5: 清理空行 ===
    t = re.sub(r'\n{3,}', '\n\n', t).strip()
    return t

def _turn_parts(t):
    _ph = []
    safe = re.sub(r'`{4,}.*?`{4,}', lambda m: (_ph.append(m.group(0)), f'\x00PH{len(_ph)-1}\x00')[1], t, flags=re.DOTALL)
    parts = re.split(r'(\**LLM Running \(Turn \d+\) \.\.\.\**)', safe)
    parts = [re.sub(r'\x00PH(\d+)\x00', lambda m: _ph[int(m.group(1))], p) for p in parts]
    if len(parts) < 4: return [], t
    turns = [parts[i] + (parts[i+1] if i+1 < len(parts) else '') for i in range(1, len(parts), 2)]
    return (([parts[0]] if parts[0].strip() else []) + turns[:-1], turns[-1])

def _progress_hint(turn_idx, total_turns):
    """Generate a brief progress hint for multi-turn responses."""
    if total_turns <= 1:
        return ''
    bar_len = 10
    filled = min(bar_len, int((turn_idx / total_turns) * bar_len))
    bar = '█' * filled + '░' * (bar_len - filled)
    return f'⏳ 思考中 {bar} {turn_idx}/{total_turns}'

def on_message(bot, msg):
    text = bot.extract_text(msg).strip()
    uid = msg.get('from_user_id', '')
    ctx = msg.get('context_token', '')
    media_paths = _dl_media(msg.get('item_list', []))
    if not text and not media_paths: return
    if media_paths:
        text = (text + '\n' if text else '') + '\n'.join(f'[用户发送文件: {p}]' for p in media_paths)
    print(f'[WX] 收到: {text[:80]}', file=sys.__stdout__)

    # === 快速天气通道（免费 API，跳过 LLM） ===
    _weather_match = re.match(r'^(.+?)(?:的)?天气$', text.strip())
    if _weather_match:
        _city = _weather_match.group(1).strip()
        # 常见中文城市名映射（wttr.in 对中文支持不好，用英文名或拼音更准）
        _city_alias = {
            '北京': 'Beijing', '上海': 'Shanghai', '广州': 'Guangzhou', '深圳': 'Shenzhen',
            '杭州': 'Hangzhou', '南京': 'Nanjing', '武汉': 'Wuhan', '成都': 'Chengdu',
            '西安': 'Xian', '重庆': 'Chongqing', '天津': 'Tianjin', '苏州': 'Suzhou',
            '郑州': 'Zhengzhou', '长沙': 'Changsha', '青岛': 'Qingdao', '沈阳': 'Shenyang',
            '哈尔滨': 'Harbin', '昆明': 'Kunming', '厦门': 'Xiamen', '济南': 'Jinan',
            '合肥': 'Hefei', '福州': 'Fuzhou', '南昌': 'Nanchang', '贵阳': 'Guiyang',
            '太原': 'Taiyuan', '石家庄': 'Shijiazhuang', '长春': 'Changchun', '兰州': 'Lanzhou',
            '海口': 'Haikou', '南宁': 'Nanning', '呼和浩特': 'Hohhot', '乌鲁木齐': 'Urumqi',
            '西宁': 'Xining', '银川': 'Yinchuan', '拉萨': 'Lasa',
            # 省份映射到省会
            '甘肃': 'Lanzhou', '安徽': 'Hefei', '广东': 'Guangzhou', '福建': 'Fuzhou',
            '贵州': 'Guiyang', '海南': 'Haikou', '河北': 'Shijiazhuang', '河南': 'Zhengzhou',
            '黑龙江': 'Harbin', '湖北': 'Wuhan', '湖南': 'Changsha', '江苏': 'Nanjing',
            '江西': 'Nanchang', '吉林': 'Changchun', '辽宁': 'Shenyang', '内蒙古': 'Hohhot',
            '宁夏': 'Yinchuan', '青海': 'Xining', '山东': 'Jinan', '山西': 'Taiyuan',
            '陕西': 'Xian', '四川': 'Chengdu', '云南': 'Kunming', '浙江': 'Hangzhou',
            '西藏': 'Lasa', '新疆': 'Urumqi', '广西': 'Nanning',
        }
        _query_city = _city_alias.get(_city, _city)
        try:
            _url = f"https://wttr.in/{quote(_query_city)}?format=j1&lang=zh"
            _req = urllib.request.Request(_url, headers={'User-Agent': 'curl/7.68.0'})
            with urllib.request.urlopen(_req, timeout=8) as _resp:
                _j = json.loads(_resp.read().decode('utf-8'))
            _cur = _j['current_condition'][0]
            _area = _j['nearest_area'][0]
            _city_name = _city
            _desc = _cur['lang_zh'][0]['value'] if _cur.get('lang_zh') else _cur.get('weatherDesc', [{}])[0].get('value', '')
            _temp = _cur['temp_C']
            _feels = _cur['FeelsLikeC']
            _humidity = _cur['humidity']
            _wind = _cur['windspeedKmph']
            _wind_dir_en = _cur.get('winddir16Point', '')
            _wind_dir_cn = {'N':'北风','NNE':'北东北风','NE':'东北风','ENE':'东东北风',
                'E':'东风','ESE':'东南东风','SE':'东南风','SSE':'南东南风',
                'S':'南风','SSW':'南西南风','SW':'西南风','WSW':'西西南风',
                'W':'西风','WNW':'西西北风','NW':'西北风','NNW':'北西北风'}.get(_wind_dir_en, _wind_dir_en)
            _today = _j['weather'][0]
            _date = _today['date']
            _max_t = _today['maxtempC']
            _min_t = _today['mintempC']
            _hourly = _today.get('hourly', [])
            
            # 风向 emoji
            _dir_emoji = {'N':'⬆️','NNE':'⬆️','NE':'↗️','ENE':'↗️',
                'E':'➡️','ESE':'↘️','SE':'↘️','SSE':'↘️',
                'S':'⬇️','SSW':'⬇️','SW':'↙️','WSW':'↙️',
                'W':'⬅️','WNW':'⬅️','NW':'↖️','NNW':'↖️'}.get(_wind_dir_en, '🌀')
            
            # 只取白天关键时段 (6:00, 9:00, 12:00, 15:00, 18:00, 21:00)
            _slots = []
            for _h in _hourly:
                _hour = int(_h['time']) // 100
                if _hour not in (6, 9, 12, 15, 18, 21):
                    continue
                _h_desc = _h['lang_zh'][0]['value'] if _h.get('lang_zh') else _h.get('weatherDesc', [{}])[0].get('value', '')
                _rain = _h.get('chanceofrain', '0')
                _rain_str = f" 🌧{_rain}%" if int(_rain) > 20 else ""
                _slots.append(f"  {_hour:02d}:00  {_h_desc}  {_h['tempC']}°C{_rain_str}")
            
            # 用 \u2028 (Unicode 行分隔符) 替代 \n 实现换行
            # 微信 JSON 协议中 \n 被转义为字面量，\u2028 不被转义
            _NL = '\u2028'
            _slots_text = " ┃ ".join(_slots)
            _msg = (
                f"📍 {_city_name} │ {_desc} {_temp}°C 体感{_feels}°{_NL}"
                f"━━━━━━{_NL}"
                f"🔺{_max_t}° 🔻{_min_t}° │ 💧{_humidity}% │ {_dir_emoji}{_wind_dir_cn} {_wind}km/h{_NL}"
                f"━━━━━━{_NL}"
                f"{_slots_text}"
            )
            bot.send_text(uid, _msg, context_token=ctx)
            print(f'[WX] 天气快速通道: {_city_name} send ok', file=sys.__stdout__)
        except Exception as _we:
            print(f'[WX] 天气快速通道失败: {_we}', file=sys.__stdout__)
            # 失败时降级走 LLM
        else:
            return  # 成功则直接返回，不走 LLM

    # Commands
    if text in ('/stop', '/abort'):
        agent.abort()
        bot.send_text(uid, '已停止', context_token=ctx)
        return
    if text.startswith('/llm'):
        args = text.split()
        if len(args) > 1:
            try:
                n = int(args[1]); agent.next_llm(n)
                bot.send_text(uid, f'切换到 [{agent.llm_no}] {agent.get_llm_name()}', context_token=ctx)
            except (ValueError, IndexError):
                bot.send_text(uid, f'用法: /llm <0-{len(agent.list_llms())-1}>', context_token=ctx)
        else:
            lines = [f"{'→' if cur else '  '} [{i}] {name}" for i, name, cur in agent.list_llms()]
            bot.send_text(uid, 'LLMs:\n' + '\n'.join(lines), context_token=ctx)
        return

    def _handle():
        try:
            _wx_fmt_hint = (
                "【微信格式要求】\n"
                "- 输出纯文本+emoji，禁止 Markdown（无表格、无|分隔线、无**加粗**、无##标题）\n"
                "- 用 emoji 作为分区标记（如 📊🔥📰），用换行分隔段落\n"
                "- 列表用 emoji 序号（①②③）或简单换行，不用 - * ▪ •\n"
                "- 分隔线用短横线（────────────）或空行，不用 ━━━━ ====\n"
                "- 简洁明了，避免冗余的「今日焦点」「财经快讯」等小标题重复\n"
            )
            prompt = text if text.startswith('/') else f"{_wx_fmt_hint}\nIf you need to show files to user, use [FILE:filepath] in your response.\n\n{text}"
            dq = agent.put_task(prompt, source="wechat")
            try: bot.send_typing(uid)
            except: pass
            result = ''; sent = 0; mi = 0; last_send = 0
            def _wx_send(text):
                s = text.strip(); t0 = time.time()
                try:
                    bot.send_text(uid, s, context_token=ctx)
                    print(f'[WX] send ok len={len(s)} dt={time.time()-t0:.1f}s', file=sys.__stdout__)
                    return True
                except Exception as e:
                    print(f'[WX] send err len={len(s)} dt={time.time()-t0:.1f}s {type(e).__name__}: {e}', file=sys.__stdout__)
                    return False
            def _send(show):
                nonlocal mi, last_send
                now = time.time()
                if mi >= 9 or not show.strip(): return False
                if mi and now - last_send < 2: return None
                if _wx_send(show[:2000]): mi += 1; last_send = time.time(); return True
                return False
            try:
                while True:
                    item = dq.get(timeout=120)
                    if 'done' in item: result = item['done']; break
                    raw = item.get('next', '')
                    done, partial = _turn_parts(raw)
                    if len(done) > sent:
                        merged = _fmt_wx('\n\n'.join(done[sent:]))
                        print(f'[WX] turns={len(done)}/{len(done)+1} sent={sent} sending={len(done)-sent}', file=sys.__stdout__)
                        if _send(merged):
                            sent = len(done)
                    # Note: No streaming fallback here — wait for final result to avoid sending incomplete chunks
            except queue.Empty: result = '⏰ 响应超时，请稍后重试'
            done, partial = _turn_parts(result)
            # If fallback already sent during streaming, skip final send to avoid duplicate
            if sent > 0:
                print(f'[WX] final skip (already sent {sent})', file=sys.__stdout__)
            else:
                # Build final response (clean output, no internal artifacts)
                rest = '\n\n'.join(done[sent:] + [partial])
                rest_clean = _fmt_wx(rest)
                # If _turn_parts returned empty turns, send result directly
                if not done and not partial and result.strip():
                    rest_clean = _fmt_wx(result)
                # Ensure we don't exceed 2000 chars; if so, trim smartly
                final = rest_clean[-1900:] if len(rest_clean) > 1900 else rest_clean
                if final.strip(): _wx_send(final)
            files = re.findall(r'\[FILE:([^\]]+)\]', result)
            bad = {'filepath', '<filepath>', 'path', '<path>', 'file_path', '<file_path>', '...'}
            files = [f for f in files if f.strip().lower() not in bad and (f if os.path.isabs(f) else os.path.join(_TEMP_DIR, f)) not in media_paths]
            for fpath in set(files):
                if not os.path.isabs(fpath): fpath = os.path.join(_TEMP_DIR, fpath)
                try:
                    if not os.path.exists(fpath): raise FileNotFoundError(f"文件不存在: {fpath}")
                    ext = os.path.splitext(fpath)[1].lower()
                    sender = bot.send_video if ext in {'.mp4', '.mov', '.m4v', '.webm'} else \
                             bot.send_image if ext in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'} else bot.send_file
                    sender(uid, fpath, context_token=ctx)
                    print(f'[WX] sent media: {fpath}', file=sys.__stdout__)
                except Exception as e: print(f'[WX] send media err: {e}', file=sys.__stdout__)
        except Exception as e:
            import traceback
            print(f'[WX] _handle 未捕获异常: {type(e).__name__}: {e}', file=sys.__stdout__)
            traceback.print_exc(file=sys.__stdout__)

    threading.Thread(target=_handle, daemon=True).start()

if __name__ == '__main__':
    # Prevent multiple instances: check for other wechatapp.py processes via PowerShell
    _my_pid = os.getpid()
    _dup = False
    try:
        import subprocess as _sp
        _out = _sp.check_output(
            ['powershell', '-NoProfile', '-Command',
             'Get-Process python -ErrorAction SilentlyContinue | '
             'Select-Object Id, @{Name="Cmd";Expression={(Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine}} | '
             'Where-Object { $_.Cmd -like "*wechatapp*" } | ForEach-Object { "$($_.Id) $($_.Cmd)" }'],
            timeout=8
        ).decode('utf-8', errors='replace').strip()
        if _out:
            for _line in _out.split('\n'):
                _line = _line.strip()
                if _line:
                    try:
                        _other_pid = int(_line.split()[0])
                        if _other_pid != _my_pid:
                            _dup = True
                            print(f'[WeChat] Found another instance (PID {_other_pid}): {_line[:120]}')
                    except (ValueError, IndexError):
                        pass
    except Exception as _e:
        print(f'[WeChat] Process check skipped: {_e}')
    if _dup:
        print('[WeChat] Another instance running, exiting.')
        sys.exit(1)
    _logf = open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp', 'wechatapp.log'), 'a', encoding='utf-8', buffering=1)
    sys.stdout = sys.stderr = _logf
    print(f'[NEW] Process starting {time.strftime("%m-%d %H:%M")}')
    bot = WxBotClient()
    if not bot.token:
        _stdout_save = sys.__stdout__ if sys.__stdout__ else _logf
        sys.stdout = sys.stderr = _stdout_save  # restore for QR display
        bot.login_qr()
        sys.stdout = sys.stderr = _logf
    # Start agent in a supervised daemon thread that auto-restarts on crash
    def _agent_wrapper():
        while True:
            try:
                print('[Bot] agent.run() 启动', file=sys.__stdout__)
                agent.run()
            except Exception as e:
                print(f'[Bot] agent.run() 异常退出: {e}，5s后重启', file=sys.__stdout__)
                time.sleep(5)
    threading.Thread(target=_agent_wrapper, daemon=True).start()
    print(f'WeChat Bot 已启动 (bot_id={bot.bot_id})', file=sys.__stdout__)
    bot.run_loop(on_message)