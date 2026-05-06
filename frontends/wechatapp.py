import os, sys, re, threading, queue, time, socket, json, struct, base64, uuid, webbrowser, hashlib, math
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
TOKEN_FILE = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / 'wxbot_token.json'
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

    def login_qr_nonblocking(self):
        """获取二维码并保存到文件，返回 qr_id。不阻塞主循环。"""
        try:
            r = requests.get(f'{API}/ilink/bot/get_bot_qrcode',
                             params={'bot_type': 3}, headers={'User-Agent': UA}, timeout=10)
            r.raise_for_status()
            d = r.json()
            qr_id, url = d['qrcode'], d.get('qrcode_img_content', '')
            print(f'[QR] ID: {qr_id}', file=sys.__stdout__)
            if url:
                img_path = str(self._tf.parent / 'wx_qr_relogin.png')
                qrcode.make(url).save(img_path)
                print(f'[QR] 二维码已保存: {img_path}', file=sys.__stdout__)
            return qr_id, url
        except Exception as e:
            print(f'[QR] 获取失败: {e}', file=sys.__stdout__)
            return None, None

    def poll_qr_status(self, qr_id, max_wait=120):
        """非阻塞轮询二维码状态，超时返回 None"""
        deadline = time.time() + max_wait
        last = ''
        while time.time() < deadline:
            time.sleep(3)
            try:
                s = requests.get(f'{API}/ilink/bot/get_qrcode_status',
                                 params={'qrcode': qr_id},
                                 headers={'User-Agent': UA}, timeout=60).json()
            except requests.exceptions.ReadTimeout:
                continue
            st = s.get('status', '')
            if st != last:
                print(f'[QR] 状态: {st}', file=sys.__stdout__)
                last = st
            if st == 'confirmed':
                self.token = s.get('bot_token', '')
                self.bot_id = s.get('ilink_bot_id', '')
                self._save(login_time=time.strftime('%Y-%m-%d %H:%M:%S'))
                print(f'[QR] 登录成功! bot_id={self.bot_id}', file=sys.__stdout__)
                return True
            if st == 'expired':
                print(f'[QR] 二维码过期', file=sys.__stdout__)
                return False
        print(f'[QR] 超时', file=sys.__stdout__)
        return False

    def get_updates(self, timeout=30):
        try:
            resp = self._post('ilink/bot/getupdates',
                              {'get_updates_buf': self._buf or '',
                               'base_info': {}},
                              timeout=timeout + 5)
        except requests.exceptions.ReadTimeout:
            return []
        if resp.get('errcode'):
            print(f'[getUpdates] err: {resp.get("errcode")} {resp.get("errmsg","")}', file=sys.__stdout__)
            if resp['errcode'] == -14:
                # Token 过期，设置标记，由 run_loop 处理重新登录
                print('[getUpdates] Token 过期，需要重新登录', file=sys.__stdout__)
                self._buf = ''
                self._save()
                self._token_expired = True
            return []
        nb = resp.get('get_updates_buf', '')
        if nb: self._buf = nb; self._save()
        return resp.get('msgs') or []

    def send_text(self, to_user_id, text, context_token=''):
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
        print(f'[Bot] 监听中... (bot_id={self.bot_id})', file=sys.__stdout__)
        seen = set()
        self._token_expired = False
        while True:
            try:
                # Token 过期时自动重登录（非阻塞）
                if getattr(self, '_token_expired', False):
                    print('[Bot] 检测到 token 过期，获取二维码...', file=sys.__stdout__)
                    self._token_expired = False
                    qr_id, qr_url = self.login_qr_nonblocking()
                    if qr_id:
                        # 发二维码图片给最近联系的用户
                        qr_img = str(self._tf.parent / 'wx_qr_relogin.png')
                        for uid in list(seen)[-5:]:
                            try:
                                self.send_image(uid, qr_img)
                                self.send_text(uid, '🔑 Token 已过期，请扫码重新登录')
                            except: pass
                        # 等待扫码
                        ok = self.poll_qr_status(qr_id, max_wait=120)
                        if ok:
                            print('[Bot] 重登录成功，恢复监听', file=sys.__stdout__)
                        else:
                            print('[Bot] 扫码超时，60s后重试', file=sys.__stdout__)
                            time.sleep(60)
                            self._token_expired = True
                            continue
                    else:
                        time.sleep(30)
                        self._token_expired = True
                        continue
                for msg in self.get_updates(poll_timeout):
                    mid = msg.get('message_id', 0)
                    if not self.is_user_msg(msg) or mid in seen: continue
                    seen.add(mid)
                    if len(seen) > 5000: seen = set(list(seen)[-2000:])
                    try: on_message(self, msg)
                    except Exception as e: print(f'[Bot] 回调异常: {e}', file=sys.__stdout__)
            except KeyboardInterrupt: print('[Bot] 退出', file=sys.__stdout__); break
            except Exception as e: print(f'[Bot] 异常: {e}，5s重试', file=sys.__stdout__); time.sleep(5)

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

def _strip_md(t):
    """Enhance & filter markdown for WeChat rich-text rendering.
    WeChat natively renders: code fences, inline code, bold, italic,
    H1-H4 headings, horizontal rules, tables. We add emoji markers and visual separators."""
    def _trunc_code(m):
        full = m.group()
        fence = re.match(r'`{3,}', full).group()
        rest = full[len(fence):-len(fence)]
        if '\n' not in rest: return full  # single-line, keep as-is
        lang_line, _, body = rest.partition('\n')
        lines = body.split('\n')
        if len(lines) > 15:
            kept = lines[:12]
            return f'{fence}{lang_line}\n' + '\n'.join(kept) + f'\n⋯ ({len(lines)-12} 行省略)\n' + fence
        return full  # keep intact
    t = re.sub(r'(`{3,})[\s\S]*?\1', _trunc_code, t)
    # inline code: keep (WeChat renders it)
    # bold/italic (*/**/***): keep (WeChat renders it)
    # images: replace with emoji marker
    t = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'🖼️ [\1]', t)
    # links: text + 🔗
    t = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'\1 🔗', t)
    # H1-H4: add emoji prefix for visual hierarchy
    t = re.sub(r'^#{1}\s+(.+)', r'📌 \1', t, flags=re.M)
    t = re.sub(r'^#{2}\s+(.+)', r'🔹 \1', t, flags=re.M)
    t = re.sub(r'^#{3}\s+(.+)', r'▪️ \1', t, flags=re.M)
    t = re.sub(r'^#{4}\s+(.+)', r'• \1', t, flags=re.M)
    t = re.sub(r'^#{5,6}\s+', '', t, flags=re.M)                 # H5-H6: strip (too small on mobile)
    # unordered list: bullet with slight indent
    t = re.sub(r'^\s*[-*+]\s+', '  • ', t, flags=re.M)
    # ordered list: keep number but add spacing
    t = re.sub(r'^(\s*)(\d+)\.\s+', r'\1\2. ', t, flags=re.M)
    # blockquote: replace with indented style + vertical bar
    t = re.sub(r'^\s*>\s?(.+)', r'│ \1', t, flags=re.M)
    # horizontal rules: enhance with double line
    t = re.sub(r'^\s*[-*_]{3,}\s*$', '─' * 20, t, flags=re.M)
    # Add emoji to common keywords (case-insensitive, only if not already prefixed)
    t = re.sub(r'(?<!📌 )(?<!🔹 )(?<!▪️ )\b(注意|警告|错误|失败)\b', r'⚠️ \1', t)
    t = re.sub(r'(?<!\w)(成功|完成|通过|OK|done)\b', r'✅ \1', t, flags=re.I)
    t = re.sub(r'(?<!\w)(提示|说明|备注|Note)\b', r'💡 \1', t, flags=re.I)
    return re.sub(r'\n{3,}', '\n\n', t).strip()

def _clean(t):
    # Remove <summary>...</summary> blocks entirely (including content)
    t = re.sub(r'<summary>.*?</summary>', '', t, flags=re.DOTALL)
    # Remove internal agent artifacts
    t = re.sub(r'^\s*LLM Running \(Turn \d+\) \.{3}\s*$', '', t, flags=re.M)
    # Remove tool call lines: "调用工具xxx", "读取文件 xxx", "写入文件 xxx"
    t = re.sub(r'^\s*(调用工具\w+|读取文件\s+\S+|写入文件\s+\S+|执行脚本\s+\S+).*$', '', t, flags=re.M)
    # Remove 🔧 web tool call lines (web_scan, web_execute_js, etc.)
    t = re.sub(r'^\s*🔧\s*\w+\(.*$', '', t, flags=re.M)
    # Remove driver/CDP/executing/timeout/error log lines
    t = re.sub(r'^\s*(\[Driver\].*|\[CDP\].*|\[Timeout.*\].*|Executing:.*|Timeout Error.*|Error:.*|Traceback.*)$', '', t, flags=re.M)
    # Remove args: lines (tool call parameters)
    t = re.sub(r'^\s*args:\s*\{.*$', '', t, flags=re.M)
    # Remove 🛠️ tool call summary lines
    t = re.sub(r'^\s*🛠️\s*\w+\(.*$', '', t, flags=re.M)
    # Remove code_run/file_read/file_patch tool result JSON blocks
    t = re.sub(r'^\s*\{["\']status["\'].*$', '', t, flags=re.M)
    # Remove === Response === / === Prompt === token markers
    t = re.sub(r'^\s*={3,}\s*(Response|Prompt)\s*={3,}\s*$', '', t, flags=re.M)
    for p in _TAG_PATS:
        t = re.sub(p, '', t, flags=re.DOTALL)
    # Remove lines that are just tool metadata
    t = re.sub(r'^\s*["\'](exit_code|stdout|stderr)["\'].*$', '', t, flags=re.M)
    # ═══ 新增：过滤 agent 中间思考过程 ═══
    # 移除 ⏳ 进度条行（全部移除，不需要发给用户）
    t = re.sub(r'^\s*⏳.*$', '', t, flags=re.M)
    # 移除 "I'll search for..." / "Let me..." / "I need to..." 等英文思考行
    t = re.sub(r"^\s*(I'll|I'm|Let me|I need to|I will|I can|I should|I've|We need to)\s+.*$", '', t, flags=re.M)
    # 移除 "抱歉，我重新来" / "抱歉！我忘了" / "让我先查看" 等自我纠正行
    t = re.sub(r'^\s*(抱歉[，！!]?.*|让我先.*|重新来|重新执行|重新搜索).*$', '', t, flags=re.M)
    # 移除 "好的，这个任务比较简单" / "不需要走" 等内部判断行
    t = re.sub(r'^\s*(好的[，,]?.*|不需要走|直接搜索|直接执行|这个任务).*$', '', t, flags=re.M)
    # 移除 "首先" / "其次" / "最后" 等内部规划行（如果后面跟的是工具调用描述）
    t = re.sub(r'^\s*(首先|其次|最后|然后|接着)\s+(调用|读取|写入|搜索|查看|执行).*$', '', t, flags=re.M)
    # 移除空白的工具调用结果行
    t = re.sub(r'^\s*工具调用结果.*$', '', t, flags=re.M)
    # ═══ 段落级思考过滤 ═══
    # 删除包含思考关键词的整段（2-5行的段落）
    _think_kws = [
        r'用户问的是', r'但回复规则', r'规则模板错配', r'我应该',
        r'不过规则说', r'搜索失败', r'用已有知识', r'直接回答',
        r'思考过程', r'分析步骤', r'规则引用',
    ]
    _para_pats = '|'.join(_think_kws)
    # 删除包含思考关键词的段落（连续2-6行）
    t = re.sub(r'(?:^[^\n]*(?:' + _para_pats + r')[^\n]*\n?){1,6}', '', t, flags=re.M)
    # Remove excessive blank lines but keep paragraph separation
    return re.sub(r'\n{3,}', '\n\n', _strip_md(t)).strip()

def _extract_answer(t):
    """从 agent 回复中提取最终答案，丢弃所有思考过程。
    策略：取最后一个 Turn 内容，清理后返回。
    """
    _ph = []
    safe = re.sub(r'`{4,}.*?`{4,}', lambda m: (_ph.append(m.group(0)), f'\x00PH{len(_ph)-1}\x00')[1], t, flags=re.DOTALL)
    parts = re.split(r'(\**LLM Running \(Turn \d+\) \.\.\.\**)', safe)
    parts = [re.sub(r'\x00PH(\d+)\x00', lambda m: _ph[int(m.group(1))], p) for p in parts]
    # 取最后一个 Turn 的内容
    if len(parts) >= 4:
        last_idx = len(parts) - 2 if len(parts) % 2 == 0 else len(parts) - 1
        if last_idx >= 1:
            content = parts[last_idx]
            if last_idx + 1 < len(parts):
                content += parts[last_idx + 1]
        else:
            content = t
    else:
        content = t
    return content


def _turn_parts(t):
    """只取最终完整回复，丢弃所有中间 Turn 分片"""
    final = _extract_answer(t)
    cleaned = _clean(final)
    return ([], cleaned) if cleaned.strip() else ([], '')

def _progress_hint(turn_idx, total_turns):
    """进度提示不再发给用户，返回空"""
    return ''

def on_message(bot, msg):
    text = bot.extract_text(msg).strip()
    uid = msg.get('from_user_id', '')
    ctx = msg.get('context_token', '')
    media_paths = _dl_media(msg.get('item_list', []))
    if not text and not media_paths: return
    if media_paths:
        text = (text + '\n' if text else '') + '\n'.join(f'[用户发送文件: {p}]' for p in media_paths)
    print(f'[WX] 收到: {text[:80]}', file=sys.__stdout__)

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
            # 极简 prompt：指令 agent 直接输出最终答案，不输出任何中间过程
            sys_hint = (
                "【系统指令-必须遵守】\n"
                "你是直接回复用户的助手。\n"
                "禁止输出：思考过程、分析步骤、规则引用、工具调用描述、搜索结果原文、英文推理。\n"
                "只输出：最终答案本身。\n"
                "格式：emoji分段，每段2-3行，手机友好，不超过500字。\n"
                "如果搜索失败，直接用知识回答，不要说明搜索失败。"
            )
            prompt = text if text.startswith('/') else f"{sys_hint}\n\n用户问题：{text}"
            dq = agent.put_task(prompt, source="wechat")
            try: bot.send_typing(uid)
            except: pass
            result = ''; sent = 0; mi = 0; last_send = 0
            def _wx_send(text):
                s = text.strip(); t0 = time.time()
                try:
                    print(f'[WX] _wx_send start len={len(s)} uid={uid[:20]} ctx={ctx[:20] if ctx else ""}', file=sys.__stdout__)
                    result = bot.send_text(uid, s, context_token=ctx)
                    print(f'[WX] send ok len={len(s)} dt={time.time()-t0:.1f}s result={result}', file=sys.__stdout__)
                    return True
                except Exception as e:
                    import traceback
                    tb = traceback.format_exc()
                    print(f'[WX] send err len={len(s)} dt={time.time()-t0:.1f}s {type(e).__name__}: {e}', file=sys.__stdout__)
                    print(f'[WX] send err tb:\n{tb}', file=sys.__stdout__)
                    return False
            def _send(show):
                nonlocal mi, last_send
                now = time.time()
                if mi >= 9 or not show.strip(): return False
                # 限速：第一条立即发，后续每条间隔 1 秒（从 2 秒优化）
                if mi and now - last_send < 1: return None
                if _wx_send(show[:2000]): mi += 1; last_send = time.time(); return True
                return False
            try:
                max_turns = 5  # 最多5轮，防止无限循环
                turn_count = 0
                while True:
                    item = dq.get(timeout=60)  # 60s超时（从300s缩短）
                    if 'done' in item: result = item['done']; break
                    raw = item.get('next', '')
                    done, partial = _turn_parts(raw)
                    turn_count += 1
                    if len(done) > sent:
                        merged = _clean('\n\n'.join(done[sent:]))
                        print(f'[WX] turns={len(done)}/{len(done)+1} sent={sent} sending={len(done)-sent}', file=sys.__stdout__)
                        if _send(merged):
                            sent = len(done)
                    if turn_count >= max_turns:
                        print(f'[WX] 达到最大轮次{max_turns}，强制结束', file=sys.__stdout__)
                        result = '\n\n'.join(done + [partial])
                        break
            except queue.Empty:
                result = '⏰ 响应超时，请稍后重试'
                print('[WX] agent 60s 超时', file=sys.__stdout__)
            done, partial = _turn_parts(result)
            # Build final response - 手机端友好格式
            rest = '\n\n'.join(done[sent:] + [partial])
            rest_clean = _clean(rest)
            # 截断到 2000 字符以内
            if len(rest_clean) > 1900:
                rest_clean = rest_clean[-1900:]
            if rest_clean.strip(): _wx_send(rest_clean)
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

def _ensure_cdp():
    """确保 Chrome CDP 9222 可用。不可用时自动启动 headless 隐身 Chrome。"""
    import socket as _sk
    sock = _sk.socket(_sk.AF_INET, _sk.SOCK_STREAM)
    if sock.connect_ex(('127.0.0.1', 9222)) == 0:
        sock.close(); print('[CDP] 已可用', file=sys.__stdout__); return
    sock.close()
    print('[CDP] 未检测到，启动 Chrome headless 隐身模式...', file=sys.__stdout__)
    chrome_exe = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    cdp_profile = os.path.join(os.environ.get('TEMP', ''), 'chrome_cdp_profile')
    subprocess.Popen([chrome_exe, '--remote-debugging-port=9222', f'--user-data-dir={cdp_profile}',
                      '--no-first-run', '--disable-gpu', '--headless=new', '--incognito'],
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                     creationflags=subprocess.CREATE_NO_WINDOW)
    time.sleep(8)
    sock2 = _sk.socket(_sk.AF_INET, _sk.SOCK_STREAM)
    ok = sock2.connect_ex(('127.0.0.1', 9222)) == 0
    sock2.close()
    print(f'[CDP] {"✅ 已启动" if ok else "❌ 启动失败"}', file=sys.__stdout__)

if __name__ == '__main__':
    _ensure_cdp()  # 启动前确保 CDP 可用
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