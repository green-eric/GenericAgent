import os, sys, re, threading, queue, time, socket, json, struct, base64, uuid, webbrowser, hashlib, math, urllib.request
from pathlib import Path
from urllib.parse import quote

# ── 自启动日志重定向（pythonw.exe 无 stdout/stderr，手动重定向到文件）──
_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'temp')
os.makedirs(_LOG_DIR, exist_ok=True)
_logf = open(os.path.join(_LOG_DIR, 'wechatbot_stdout.log'), 'a', encoding='utf-8')
_logf_err = open(os.path.join(_LOG_DIR, 'wechatbot_stderr.log'), 'a', encoding='utf-8')
sys.stdout = _logf
sys.stderr = _logf_err
sys.__stdout__ = _logf
sys.__stderr__ = _logf_err
# Override print to always use UTF-8 log file, never fallback to GBK console
_builtin_print = print
def print(*args, file=None, **kwargs):
    if file is None or file is sys.__stdout__ or file is sys.__stderr__:
        file = _logf
    _builtin_print(*args, file=file, **kwargs)
print(f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] wechatapp.py 启动，日志重定向已生效', file=sys.stdout)

# ── 启动时自动清理 .pyc 缓存，确保加载最新代码 ──
for _d in [os.path.dirname(os.path.abspath(__file__)),
           os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]:
    _pyc = os.path.join(_d, '__pycache__')
    if os.path.exists(_pyc):
        try:
            shutil.rmtree(_pyc)
            print(f'[WX] 已清理缓存: {_pyc}', file=sys.__stdout__)
        except Exception:
            pass
_trace = open(os.path.join(_LOG_DIR, 'wechatbot_trace.log'), 'a', encoding='utf-8', buffering=1)
_trace.write(f'[{time.strftime("%H:%M:%S")}] TRACE: after cache cleanup\n')
_trace.flush()

import requests, qrcode
from requests.adapters import HTTPAdapter
import socket as _socket
_trace.write(f'[{time.strftime("%H:%M:%S")}] TRACE: after import socket\n')
_trace.flush()

_API_HOST = 'ilinkai.weixin.qq.com'

# 显式代理配置：不依赖环境变量（nssm服务为SYSTEM用户，无用户环境变量）
_PROXY = 'http://127.0.0.1:7897'
_PROXIES = {'http': _PROXY, 'https': _PROXY}
# 代理可用性缓存（避免每次请求都尝试超时）
_PROXY_OK = None

def _check_proxy():
    """检测代理是否可用，返回 True/False。结果缓存避免重复检测。"""
    global _PROXY_OK
    if _PROXY_OK is not None:
        return _PROXY_OK
    try:
        # ★ 检测实际使用的API域名（ilinkai.weixin.qq.com），而非api.weixin.qq.com
        # 避免代理对api.weixin.qq.com通但对ilinkai.weixin.qq.com SSL握手失败
        r = requests.head(f'https://{_API_HOST}/', timeout=5, proxies=_PROXIES)
        _PROXY_OK = True  # 代理能连通即视为可用
    except Exception:
        _PROXY_OK = False
    print(f'[WX] 代理检测: {"可用" if _PROXY_OK else "不可用，将直连"}', file=sys.__stdout__)
    return _PROXY_OK

def _get_proxies():
    """返回可用代理 dict，或 None（直连）。"""
    if _check_proxy():
        return _PROXIES
    return None

from Crypto.Cipher import AES
_trace.write(f'[{time.strftime("%H:%M:%S")}] TRACE: after Crypto.Cipher.AES\n')
_trace.flush()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'temp')
from agentmain import GeneraticAgent
# ── K线图集成 ──
try:
    _TEMP_DIR_KL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'temp')
    sys.path.insert(0, _TEMP_DIR_KL)
    from kline_chart import generate_kline as _gen_kline
except ImportError:
    _gen_kline = None
    print('[WX] kline_chart.py 未找到，K线功能不可用', file=sys.__stdout__)
_trace.write(f'[{time.strftime("%H:%M:%S")}] TRACE: after agentmain import\n')
_trace.flush()

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

# ── 设备模式：uid → 'pc' | 'mobile' | None(auto) ──
_USER_MODE = {}

def _guess_device(text, uid):
    """根据消息特征推测用户设备类型。"""
    if uid in _USER_MODE:
        return _USER_MODE[uid]
    # 启发式：长消息/代码块/表格 → PC
    if len(text) > 150 or '```' in text or '\n|' in text:
        return 'pc'
    return 'mobile'

class WxBotClient:
    def __init__(self, token=None, token_file=None):
        self._tf = Path(token_file) if token_file else TOKEN_FILE
        self.token = token
        self.bot_id = None
        self._buf = ''
# 复用 Session：连接池 + 自动重试，避免每次新建 TCP 连接被代理关闭
        self._session = requests.Session()
        adapter = HTTPAdapter(pool_connections=5, pool_maxsize=10,
                              max_retries=3, pool_block=False)
        self._session.mount('https://', adapter)
        self._session.mount('http://', adapter)
        self._token_expired = False
        if not self.token: self._load()

    def _load(self):
        if self._tf.exists():
            d = json.loads(self._tf.read_text('utf-8'))
            self.token, self.bot_id, self._buf = d.get('bot_token',''), d.get('ilink_bot_id',''), d.get('updates_buf','')
            self._login_time = d.get('login_time', '')
            self._admin_notify_uid = d.get('admin_notify_uid', '')
            self._admin_uid_saved = bool(self._admin_notify_uid)
            self._token_expired = d.get('_token_expired', False)  # ★ 恢复token过期状态

    def _save(self, **kw):
        # ★ 保留已持久化的关键字段，防止被无参 _save() 覆盖丢失
        existing = {}
        if self._tf.exists():
            try:
                existing = json.loads(self._tf.read_text('utf-8'))
            except Exception:
                pass
        d = {'bot_token': self.token or '', 'ilink_bot_id': self.bot_id or '',
             'updates_buf': self._buf or '', 'saved_at': time.strftime('%Y-%m-%d %H:%M:%S')}
        # 持久化 login_time
        lt = kw.pop('login_time', None) or getattr(self, '_login_time', '') or existing.get('login_time', '')
        if lt:
            d['login_time'] = lt
        # 持久化 admin_notify_uid（优先内存中的，否则保留已有的）
        anu = kw.pop('admin_notify_uid', None) or getattr(self, '_admin_notify_uid', '') or existing.get('admin_notify_uid', '')
        if anu:
            d['admin_notify_uid'] = anu
        d.update(kw)
        self._tf.write_text(json.dumps(d, ensure_ascii=False, indent=2), 'utf-8')

    def _token_age_hours(self):
        """返回token已登录的小时数，无记录返回-1"""
        if not getattr(self, '_login_time', ''):
            return -1
        try:
            lt = time.mktime(time.strptime(self._login_time, '%Y-%m-%d %H:%M:%S'))
            return (time.time() - lt) / 3600
        except Exception:
            return -1

    def _token_near_expiry(self, threshold_hours=23.5):
        """token是否接近过期（默认23.5小时，微信token 24h过期，留30min缓冲）"""
        age = self._token_age_hours()
        return age >= 0 and age >= threshold_hours

    def _post(self, ep, body, timeout=30):
        tok = (self.token or '').strip()
        if not tok:
            print(f'[POST] 无 token，拒绝请求 {ep}', file=sys.__stderr__)
            return {'errcode': -1, 'errmsg': 'no_token', 'endpoint': ep}
        data = json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        h = {'Content-Type': 'application/json', 'AuthorizationType': 'ilink_bot_token',
             'Content-Length': str(len(data)), 'X-WECHAT-UIN': _uin(),
             'iLink-App-Id': ILINK_APP_ID,
             'iLink-App-ClientVersion': str(ILINK_APP_CLIENT_VERSION),
             'User-Agent': UA,
'Connection': 'keep-alive'}
        tok = (self.token or '').strip()
        if tok: h['Authorization'] = f'Bearer {tok}'
        # 分离 connect timeout 和 read timeout，避免代理长连接被远端关闭
        t = (min(timeout, 10), timeout) if isinstance(timeout, (int, float)) else timeout
        r = self._session.post(f'{API}/{ep}', data=data, headers=h, timeout=t)
        r.raise_for_status()
        return r.json()

    def login_qr(self, poll_interval=2):
        # 获取二维码（用 Session 保持连接复用）
        r = self._session.get(f'{API}/ilink/bot/get_bot_qrcode',
                               params={'bot_type': 3}, headers={'User-Agent': UA}, timeout=10)
        r.raise_for_status()
        d = r.json()
        qr_id, url = d['qrcode'], d.get('qrcode_img_content', '')
        print(f'[QR登录] ID: {qr_id}')
        if url:
            # 保存二维码图片到 temp 目录
            img = self._tf.parent / 'wx_qr.png'
            qrcode.make(url).save(str(img))
# 打印 ASCII 二维码到终端（不依赖 GUI）
            qr = qrcode.QRCode(border=1); qr.add_data(url); qr.make(fit=True)
            try:
                qr.print_ascii(invert=True)
            except Exception:
                pass
            print(f'[QR登录] 二维码已保存: {img}')
            print(f'[QR登录] 扫码链接: {url}')
        last = ''
        while True:
            time.sleep(poll_interval)
            try:
                s = self._session.get(f'{API}/ilink/bot/get_qrcode_status',
                                       params={'qrcode': qr_id},
                                       headers={'User-Agent': UA}, timeout=60).json()
            except requests.exceptions.ReadTimeout:
                continue
            except Exception as e:
                print(f'[QR登录] 轮询异常: {e}', file=sys.__stdout__)
                continue
            st = s.get('status', '')
            if st != last: print(f'[QR登录] 状态: {st}'); last = st
            if st == 'confirmed':
                self.token, self.bot_id = s.get('bot_token', ''), s.get('ilink_bot_id', '')
                self._save(login_time=time.strftime('%Y-%m-%d %H:%M:%S'))
                print(f'[QR登录] 成功! bot_id={self.bot_id}')
                return s
            if st == 'expired':
                raise RuntimeError('二维码过期')

    def login_qr_nonblocking(self):
        """获取二维码并保存到文件，返回 qr_id。不阻塞主循环。10分钟冷却期避免重复生成。"""
        # ★ 冷却期60s，与退避周期对齐（60→120→240→480→960s）
        QR_COOLDOWN = 60
        now = time.time()
        last = getattr(self, '_last_qr_gen_time', 0)
        # ★ 如果上次二维码已过期，允许提前解除冷却（二维码过期后旧id已无用）
        last_qr_expired = getattr(self, '_last_qr_expired', False)
        if now - last < QR_COOLDOWN and not last_qr_expired:
            _out = sys.__stdout__ if sys.__stdout__ else sys.stdout
            print(f'[QR] 冷却中（{QR_COOLDOWN - int(now - last)}s后可用），跳过重复生成', file=_out)
            old_qr_id = getattr(self, '_last_qr_id', None)
            old_url = getattr(self, '_last_qr_url', None)
            if old_qr_id:
                return old_qr_id, old_url
            return None, None
        try:
            r = requests.get(f'{API}/ilink/bot/get_bot_qrcode',
                             params={'bot_type': 3}, headers={'User-Agent': UA}, timeout=10, proxies=_get_proxies())
            r.raise_for_status()
            d = r.json()
            qr_id, url = d['qrcode'], d.get('qrcode_img_content', '')
            _out = sys.__stdout__ if sys.__stdout__ else sys.stdout
            print(f'[QR] ID: {qr_id}', file=_out)
            print(f'[QR] API完整返回: {d}', file=_out)
            # ★ qrcode_img_content可能是base64编码的图片
            if url:
                # 如果是base64编码的图片数据，直接解码保存
                if len(url) > 100:
                    try:
                        import base64 as _b64
                        img_data = _b64.b64decode(url)
                        img_path = str(self._tf.parent / 'wx_qr_relogin.png')
                        with open(img_path, 'wb') as _f:
                            _f.write(img_data)
                        print(f'[QR] 二维码已保存(base64解码): {img_path} ({len(img_data)} bytes)', file=_out)
                    except Exception:
                        # 不是base64，当作URL生成二维码
                        url = url if url else qr_id
                        img_path = str(self._tf.parent / 'wx_qr_relogin.png')
                        _qr = qrcode.make(url).convert('RGB')
                        _qr.save(img_path, optimize=False)
                        print(f'[QR] 二维码已保存(URL生成): {img_path}', file=_out)
                else:
                    # 短字符串当作URL
                    img_path = str(self._tf.parent / 'wx_qr_relogin.png')
                    _qr = qrcode.make(url).convert('RGB')
                    _qr.save(img_path, optimize=False)
                    print(f'[QR] 二维码已保存(短URL): {img_path}', file=_out)
            else:
                # qrcode_img_content为空，用qr_id生成
                url = qr_id
                print(f'[QR] qrcode_img_content为空，使用qr_id作为二维码内容', file=_out)
                img_path = str(self._tf.parent / 'wx_qr_relogin.png')
                _qr = qrcode.make(url).convert('RGB')
                _qr.save(img_path, optimize=False)
                print(f'[QR] 二维码已保存(qr_id): {img_path}', file=_out)
            # ★ 记录本次生成时间和qr_id，供冷却期复用
            self._last_qr_gen_time = now
            self._last_qr_id = qr_id
            self._last_qr_url = url
            return qr_id, url
        except Exception as e:
            _out = sys.__stdout__ if sys.__stdout__ else sys.stdout
            print(f'[QR] 获取失败: {e}', file=_out)
            return None, None

    def _on_login_success(self):
        """登录成功后统一记录时间戳"""
        self._login_time = time.strftime('%Y-%m-%d %H:%M:%S')
        self._token_expired = False  # ★ 必须在_save前设置，_save会触发__setattr__写文件
        self._relogin_time = time.time()
        self._save(login_time=self._login_time, _token_expired=False)
        print(f'[Bot] token刷新成功，登录时间: {self._login_time}', file=sys.__stdout__)

    def poll_qr_status(self, qr_id, max_wait=180):
        """非阻塞轮询二维码状态，超时返回 False"""
        deadline = time.time() + max_wait
        last = ''
        while time.time() < deadline:
            time.sleep(3)
            try:
                s = requests.get(f'{API}/ilink/bot/get_qrcode_status',
                                 params={'qrcode': qr_id},
                                 headers={'User-Agent': UA}, timeout=60, proxies=_get_proxies()).json()
            except requests.exceptions.ReadTimeout:
                continue
            st = s.get('status', '')
            if st != last:
                print(f'[QR] 状态: {st}', file=sys.__stdout__)
                last = st
            if st == 'confirmed':
                self.token = s.get('bot_token', '')
                self.bot_id = s.get('ilink_bot_id', '')
                self._on_login_success()
                print(f'[QR] 登录成功! bot_id={self.bot_id}', file=sys.__stdout__)
                return True
            if st == 'expired':
                print(f'[QR] 二维码过期', file=sys.__stdout__)
                # ★ 标记二维码已过期，让login_qr_nonblocking的冷却期检查知道可以提前解除
                self._last_qr_expired = True
                return False
        print(f'[QR] 超时（{max_wait}s）', file=sys.__stdout__)
        return False

    def get_updates(self, timeout=60):
        try:
            # 固定 read timeout=35，避免代理长连接被远端关闭（之前 timeout+5=35 但 connect timeout 也=35）
            resp = self._post('ilink/bot/getupdates',
                              {'get_updates_buf': self._buf or '',
                               'base_info': {}},
                              timeout=35)
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
            if resp['errcode'] == -14:
                # session 过期 → 自动重新登录
                print('[getUpdates] session 过期，触发重新登录...')
                try:
                    self.login_qr()
                    print(f'[getUpdates] 重新登录成功! bot_id={self.bot_id}')
                    # 用新 token 重试一次
                    return self.get_updates(timeout=timeout)
                except Exception as e:
                    print(f'[getUpdates] 重新登录失败: {e}', file=sys.__stdout__)
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
                r = requests.post(url, data=data, headers={'Content-Type': 'application/octet-stream', 'User-Agent': UA}, timeout=timeout, proxies=_get_proxies())
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
        _out = sys.__stdout__ if sys.__stdout__ else sys.stdout
        print(f'[Bot] 监听中... (bot_id={self.bot_id})', file=_out)
        seen = set()
retry_delay = 1          # 初始退避 1s
        max_retry_delay = 60     # 最大退避 60s
        consec_fail = 0          # 连续失败计数
        _relogin_attempts = 0
        while True:
            try:
                # Token 快过期时提前刷新（23.5h阈值，留30min缓冲）
                if not self._token_expired and self._token_near_expiry(threshold_hours=23.5):
                    age = self._token_age_hours()
                    print(f'[Bot] Token 已 {age:.1f}h，接近过期，提前刷新...', file=_out)
                    self._token_expired = True

                # Token 过期时自动重登录
                if self._token_expired:
                    print('[Bot] 检测到 token 过期，获取二维码...', file=_out)
                    qr_id, qr_url = self.login_qr_nonblocking()
                    if not qr_id:
                        # ★ 冷却期内无法生成新码，等待冷却结束（最多等120s）
                        _relogin_attempts += 1
                        wait = 60  # ★ 改为60s，确保超过冷却期
                        print(f'[Bot] 获取二维码冷却中，{wait}s后重试（第{_relogin_attempts}次）', file=_out)
                        time.sleep(wait)
                        continue
                    # 发二维码给指定通知用户（优先）+ seen列表兜底
                    qr_img = str(self._tf.parent / 'wx_qr_relogin.png')
                    notify_uids = []
                    try:
                        tf_data = json.loads(self._tf.read_text('utf-8'))
                        admin_uid = tf_data.get('admin_notify_uid', '')
                        if admin_uid:
                            notify_uids.append(admin_uid)
                    except Exception:
                        pass
                    notify_uids += list(seen)[-3:]
                    sent = False
                    for uid in notify_uids:
                        try:
                            # ★ 优先发图片二维码（更直观，微信内直接扫码）
                            if os.path.exists(qr_img):
                                try:
                                    self.send_image(uid, qr_img)
                                    print(f'[Bot] 二维码图片已发给: {uid}', file=_out)
                                except Exception as img_err:
                                    # 图片发送失败降级为文字链接
                                    print(f'[Bot] 图片发送失败({img_err})，降级为文字链接', file=_out)
                                    self.send_text(uid, f'🔔 Token 已过期，需要重新扫码登录\n\n📱 直接点开链接扫码：\n{qr_url}\n\n扫码后请回复任意消息确认')
                            else:
                                self.send_text(uid, f'🔔 Token 已过期，需要重新扫码登录\n\n📱 直接点开链接扫码：\n{qr_url}\n\n扫码后请回复任意消息确认')
                            # 额外发一条文字提醒（图片+文字双保险）
                            self.send_text(uid, f'⬆️ 请用微信扫码上图二维码，扫码后回复任意消息确认\n\n🔗 备用链接：{qr_url}')
                            print(f'[Bot] 二维码已发给: {uid}', file=_out)
                        except Exception as e:
                            print(f'[Bot] 发给 {uid} 失败: {e}', file=_out)
                        sent = True
                    if not sent:
                        print(f'[Bot] 未能发送二维码，请打开: {qr_img}', file=_out)
                        print(f'[Bot] 二维码链接: {qr_url}', file=_out)
                    # ★ 等待扫码（300s=5min，给用户更充裕的时间）
                    ok = self.poll_qr_status(qr_id, max_wait=300)
                    if ok:
                        print('[Bot] 重登录成功，恢复监听', file=_out)
                        # ★ _on_login_success已经设了_token_expired=False并save到文件
                        _relogin_attempts = 0
                    else:
                        _relogin_attempts += 1
                        # 每3次重试强制刷新二维码冷却
                        if _relogin_attempts % 3 == 0:
                            self._last_qr_expired = True
                            print(f'[Bot] 已重试{_relogin_attempts}次，强制刷新二维码...', file=sys.__stdout__)
                        wait = 60  # ★ 固定60s，确保超过冷却期
                        print(f'[Bot] 扫码超时，{wait}s后重试（第{_relogin_attempts}次）', file=sys.__stdout__)
                        time.sleep(wait)
                        continue
                for msg in self.get_updates(poll_timeout):
                    mid = msg.get('message_id', 0)
                    if not self.is_user_msg(msg) or mid in seen: continue
                    seen.add(mid)
                    if len(seen) > 5000: seen = set(list(seen)[-2000:])
                    # 自动检测并保存user_id（首次收到消息时）
                    from_uid = msg.get('from_user_id', '')
                    if from_uid and not getattr(self, '_admin_uid_saved', False):
                        self._admin_uid_saved = True
                        try:
                            self._save(admin_notify_uid=from_uid)
                            print(f'[Bot] 已自动保存admin_notify_uid: {from_uid}', file=sys.__stdout__)
                        except Exception: pass
                    try: on_message(self, msg)
except Exception as e: print(f'[Bot] 回调异常: {e}')
                # 成功拉取一轮后退避重置
                if consec_fail > 0:
                    print(f'[Bot] 连接恢复，连续失败 {consec_fail} 次后成功')
                consec_fail = 0
                retry_delay = 1
            except KeyboardInterrupt: print('[Bot] 退出'); break
            except Exception as e:
                consec_fail += 1
                print(f'[Bot] 异常(连续第{consec_fail}次): {type(e).__name__}: {e}，{retry_delay}s后重试', file=sys.__stdout__)
                # 连续失败 5 次以上，重建 Session 清除脏连接
                if consec_fail >= 5 and consec_fail % 5 == 0:
                    print(f'[Bot] 连续失败{consec_fail}次，重建 Session...')
                    try:
                        self._session.close()
                    except Exception:
                        pass
                    self._session = requests.Session()
                    from requests.adapters import HTTPAdapter
                    adapter = HTTPAdapter(pool_connections=5, pool_maxsize=10, max_retries=3, pool_block=False)
                    self._session.mount('https://', adapter)
                    self._session.mount('http://', adapter)
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
                ct = requests.get(f'{CDN_BASE}/download?encrypted_query_param={quote(eq)}', headers={'User-Agent': UA}, timeout=60, proxies=_get_proxies()).content
                pt = AES.new(aes_key, AES.MODE_ECB).decrypt(ct); pt = pt[:-pt[-1]]
                fname = sub.get('file_name') or f'{uuid.uuid4().hex[:8]}{ext or ".bin"}'
                p = os.path.join(_TEMP_DIR, fname); open(p, 'wb').write(pt)
                paths.append(p); print(f'[WX] media saved: {fname}', file=sys.__stdout__)
            except Exception as e:
                print(f'[WX] media dl err ({key}): {e}', file=sys.__stdout__)
            break  # one media per item
    return paths

try:
    agent = GeneraticAgent()
    agent.verbose = False
except Exception as e:
    print(f'[WX] GeneraticAgent init failed: {e}', file=sys.__stdout__)
    import traceback; traceback.print_exc(file=sys.__stdout__)
    agent = None

_TAG_PATS = [r'<' + t + r'>.*?</' + t + r'>' for t in ('thinking', 'tool_use', 'details', 'think', 'reasoning', 'analysis', 'internal')]
_TAG_PATS.append(r'<file_content>.*?</file_content>')
_TAG_PATS.append(r'<summary>.*?</summary>')  # 双重保障：TAG_PATS也清洗summary

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

def _extract_answer(t):
    """从 agent 回复中提取最终答案，丢弃所有思考过程。
    策略：取最后一个 Turn 内容，清理后返回。
    split 结果格式: [text_before, DELIM, turn_text, DELIM, turn_text, ...]
    奇数索引是 DELIM，偶数索引是内容。取最后一个 DELIM 之后的内容。
    """
    _ph = []
    safe = re.sub(r'`{4,}.*?`{4,}', lambda m: (_ph.append(m.group(0)), f'\x00PH{len(_ph)-1}\x00')[1], t, flags=re.DOTALL)
    parts = re.split(r'(\**LLM Running \(Turn \d+\) \.\.\.\**)', safe)
    parts = [re.sub(r'\x00PH(\d+)\x00', lambda m: _ph[int(m.group(1))], p) for p in parts]
    # 找到最后一个 DELIM（奇数索引），取其后的内容
    last_delim_idx = -1
    for i in range(len(parts)):
        if re.match(r'\**LLM Running \(Turn \d+\) \.\.\.\**', parts[i]):
            last_delim_idx = i
    if last_delim_idx >= 0 and last_delim_idx + 1 < len(parts):
        content = ''.join(parts[last_delim_idx + 1:])
    else:
        # 无 Turn 分隔符，返回全文（可能是最终 done 消息）
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
    print(f'[WX] 收到: {text[:80]} media={media_paths}', file=sys.__stdout__)

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
    if text == '/pc':
        _USER_MODE[uid] = 'pc'
        bot.send_text(uid, '🖥️ 已切换为电脑端模式 — 富文本/表格/长内容', context_token=ctx)
        return
    if text == '/mobile':
        _USER_MODE[uid] = 'mobile'
        bot.send_text(uid, '📱 已切换为手机端模式 — 简洁排版/emoji/短段落', context_token=ctx)
        return
    if text == '/auto':
        _USER_MODE.pop(uid, None)
        bot.send_text(uid, '🔄 已切换为自动检测模式', context_token=ctx)
        return

    # ── Token 统计 ──
    if text.startswith('/token'):
        try:
            import subprocess as _sp
            _cmd = [sys.executable, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'token_stats.py')]
            _arg = text[len('/token'):].strip()
            if _arg in ('week', 'month'):
                _cmd.append(f'--{_arg}')
            elif _arg:
                _cmd.extend(['--date', _arg])
            _r = _sp.run(_cmd, capture_output=True, text=True, timeout=30)
            _out = _r.stdout.strip()
            if _out:
                bot.send_text(uid, _out, context_token=ctx)
            else:
                bot.send_text(uid, f'❌ token统计无输出\nstderr: {_r.stderr[:200]}', context_token=ctx)
        except Exception as _e:
            bot.send_text(uid, f'❌ token统计失败: {_e}', context_token=ctx)
        return

    # ── K线图请求拦截 ──
    _kl_match = re.search(r'[Kk]线.*?(\d{6})|(\d{6}).*?[Kk]线', text)
    if _kl_match:
        _kl_code = _kl_match.group(1) or _kl_match.group(2)
        bot.send_text(uid, f'📈 正在获取 {_kl_code} K线数据...', context_token=ctx)
        png_path = _gen_kline(_kl_code) if _gen_kline else None
        if png_path and os.path.isfile(png_path):
            bot.send_image(uid, png_path, context_token=ctx)
        else:
            bot.send_text(uid, f'❌ {_kl_code} K线图生成失败，请检查代码或稍后重试', context_token=ctx)
        return

    # ── ScoreSys 评分：直接读最新 Excel ──
    if text == '/score':
        def _run_score():
            import glob as _gl, os
            score_dir = r'D:\Project\ScoreSys'
            # 找最新的评分 Excel（支持多种命名）
            candidates = []
            for pat in ['评分结果_*.xlsx', 'score_*.xlsx']:
                candidates.extend(_gl.glob(os.path.join(score_dir, pat)))
            if not candidates:
                bot.send_text(uid, '❌ 未找到评分 Excel，请确认 ScoreSys 已运行', context_token=ctx)
                return
            out_xlsx = max(candidates, key=os.path.getmtime)
            try:
                import openpyxl
                wb = openpyxl.load_workbook(out_xlsx, read_only=True)
                ws = wb.active
                rows = list(ws.iter_rows(values_only=True))
                if len(rows) < 2:
                    bot.send_text(uid, '❌ 评分结果为空', context_token=ctx)
                    return
                header = [str(c) for c in rows[0]]
                data_rows = rows[1:]
                # 列名匹配：支持中英文混合表头（如"股票名称\n(Name)"）
                def _find_col(*keywords):
                    for i, h in enumerate(header):
                        hl = h.lower()
                        for kw in keywords:
                            if kw in hl:
                                return i
                    return None
                score_col = _find_col('score', '评分', '总分') or 2
                name_col = _find_col('name', '名称', '股票名称') or 1
                code_col = _find_col('code', '代码', '股票代码') or 0
                data_rows.sort(key=lambda x: x[score_col] if isinstance(x[score_col], (int, float)) else 0, reverse=True)
                top20 = data_rows[:20]
                # 手机/电脑自适应格式
                lines = []
                for rank, row in enumerate(top20, 1):
                    medal = ['🥇','🥈','🥉'][rank-1] if rank <= 3 else f'{rank}.'
                    name = row[name_col] if name_col < len(row) else ''
                    code = row[code_col] if code_col < len(row) else '?'
                    score = row[score_col] if score_col < len(row) else '?'
                    name = name if name else code
                    lines.append(f'{medal}{name}({code}) ⭐{score}')
                output = '📊 ScoreSys Top20 评分结果\n\n' + '\n'.join(lines)
                bot.send_text(uid, output, context_token=ctx)
            except ImportError:
                bot.send_text(uid, f'✅ 评分文件: {out_xlsx}\n(缺少 openpyxl，无法解析)', context_token=ctx)
            except Exception as _e:
                bot.send_text(uid, f'❌ 读取评分异常: {_e}', context_token=ctx)
        threading.Thread(target=_run_score, daemon=True).start()
        return

    # ── BfM 信号：从 BfM API 获取实时 picks + 八维信号 ──
    if text == '/bfm':
        def _run_bfm():
            import urllib.request, json as _json
            bfm_url = 'http://127.0.0.1:9004/data'
            try:
                req = urllib.request.Request(bfm_url, headers={'Accept': 'application/json'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = _json.loads(resp.read().decode('utf-8'))
                picks = data.get('picks', [])
                hot8 = data.get('hot8', [])
                ts = data.get('time', '')
                if not picks and not hot8:
                    bot.send_text(uid, '📊 BfM 当前无选中股票', context_token=ctx)
                    return
                lines = ['📊 **BfM 实时信号**', f'🕐 {ts}\n']
                # 八维权重标签
                _DIM_LABELS = ['情绪', '板块', '龙头', '资金', '量价', '封板', '稳定', '表现']
                if picks:
                    lines.append(f'**🔟 精选 {len(picks)} 只**')
                    for i, p in enumerate(picks[:10], 1):
                        name = p.get('name', '').strip()
                        symbol = p.get('symbol', '')
                        sector = p.get('sector', '')
                        score = p.get('score', {})
                        total = score.get('total', 0) if isinstance(score, dict) else 0
                        # 八维信号摘要（取top3维度）
                        if isinstance(score, dict):
                            dims = [(k, v) for k, v in score.items()
                                    if k != 'total' and isinstance(v, (int, float))]
                            dims.sort(key=lambda x: -x[1])
                            top3 = ' '.join(f'{k[:2]}{v:.0f}' for k, v in dims[:3])
                        else:
                            top3 = ''
                        lines.append(f'{i}. {name}({symbol}) [{sector}] ⭐{total:.0f}  {top3}')
                if hot8:
                    lines.append(f'\n**🔥 热门 {len(hot8)} 只**')
                    for i, h in enumerate(hot8[:5], 1):
                        name = h.get('name', '').strip()
                        sym = h.get('symbol', '')
                        heat = h.get('heat', 0)
                        pct = h.get('pct_change', 0)
                        arrow = '📈' if pct >= 0 else '📉'
                        lines.append(f'  {name}({sym}) 热度{heat} {arrow}{pct:+.1f}%')
                output = '\n'.join(lines)
                bot.send_text(uid, output, context_token=ctx)
            except urllib.error.URLError as e:
                bot.send_text(uid, f'❌ 连接 BfM 失败: {e}\n请确认 BfM 已启动（端口9004）', context_token=ctx)
            except Exception as e:
                bot.send_text(uid, f'❌ BfM 查询异常: {e}', context_token=ctx)
        threading.Thread(target=_run_bfm, daemon=True).start()
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

            result = ''
            raw_accum = ''

            def _wx_send(text):
                s = text.strip()
                if not s: return False
                t0 = time.time()
                try:
                    print(f'[WX] _wx_send start len={len(s)} uid={uid[:20]} ctx={ctx[:20] if ctx else ""}', file=sys.__stdout__)
                    r = bot.send_text(uid, s, context_token=ctx)
                    print(f'[WX] send ok len={len(s)} dt={time.time()-t0:.1f}s', file=sys.__stdout__)
                    return True
                except Exception as e:
                    print(f'[WX] send err {type(e).__name__}: {e}', file=sys.__stdout__)
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
    print(f'[CDP] {"[OK] 已启动" if ok else "[FAIL] 启动失败"}', file=sys.__stdout__)

if __name__ == '__main__':
    # ★ 抑制 Windows 崩溃弹窗（pythonw 无 stdout，任何未捕获异常都会弹 Windows 错误对话框）
    if os.name == 'nt':
        import ctypes
        # SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX | SEM_NOOPENFILEERRORBOX
        ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002 | 0x8000)
        # 同时设置未处理异常过滤器，静默退出
        import sys as _sys
        _orig_except = _sys.excepthook
        def _silent_except(exc_type, exc_val, exc_tb):
            _trace.write(f'[{time.strftime("%H:%M:%S")}] FATAL: {exc_type.__name__}: {exc_val}\n')
            _trace.flush()
            # 不调用 _orig_except（避免弹窗），直接退出
            os._exit(1)
        _sys.excepthook = _silent_except

    _trace.write(f'[{time.strftime("%H:%M:%S")}] TRACE: entering __main__\n')
    _trace.flush()
    _ensure_cdp()  # 启动前确保 CDP 可用
    _trace.write(f'[{time.strftime("%H:%M:%S")}] TRACE: after _ensure_cdp\n')
    _trace.flush()
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
            timeout=15
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
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    print(f'[NEW] Process starting {time.strftime("%m-%d %H:%M")}')
    bot = WxBotClient()
    if not bot.token or bot._token_expired:
        _stdout_save = sys.__stdout__ if sys.__stdout__ else _logf
        sys.stdout = sys.stderr = _stdout_save  # restore for QR display
        if bot.token and bot._token_expired:
            print('[Bot] token已过期，启动重登...', file=sys.__stdout__)
        bot.login_qr()
        sys.stdout = sys.stderr = _logf
    else:
        # token 有值但可能已过期，快速检测（5s超时，不阻塞主流程）
        _token_ok = False
        try:
            import threading as _th
            _result = [None]
            def _check():
                try:
                    r = bot._post('ilink/bot/getupdates', {'limit': 1, 'timeout': 10})
                    _result[0] = r
                except:
                    pass
            t = _th.Thread(target=_check, daemon=True)
            t.start()
            t.join(timeout=5)
            _test = _result[0]
            if _test is None:
                # ★ 超时≠token过期，可能是网络波动；重试2次再决定
                print('[启动检测] 首次API超时，3s后重试(第1次)...', file=sys.__stdout__)
                time.sleep(3)
                _result2 = [None]
                def _check2():
                    try:
                        _result2[0] = bot._post('ilink/bot/getupdates', {'limit': 1, 'timeout': 1})
                    except:
                        pass
                t2 = _th.Thread(target=_check2, daemon=True)
                t2.start()
                t2.join(timeout=5)
                _test = _result2[0]
                if _test is None:
                    print('[启动检测] 第1次重试超时，再等3s重试(第2次)...', file=sys.__stdout__)
                    time.sleep(3)
                    _result3 = [None]
                    def _check3():
                        try:
                            _result3[0] = bot._post('ilink/bot/getupdates', {'limit': 1, 'timeout': 1})
                        except:
                            pass
                    t3 = _th.Thread(target=_check3, daemon=True)
                    t3.start()
                    t3.join(timeout=5)
                    _test = _result3[0]
                if _test is None:
                    # 3次全超时：标记token过期，触发重登
                    print('[启动检测] 3次全超时，标记token过期→触发重登', file=sys.__stdout__)
                    bot._token_expired = True
                    _token_ok = False
                elif _test.get('errcode') == 0:
                    _token_ok = True
                elif _test.get('errcode') == -14:
                    bot._token_expired = True
                else:
                    print(f'[启动检测] 业务错误 errcode={_test.get("errcode")}, 不标记过期', file=sys.__stdout__)
                    _token_ok = True  # 其他错误也不标记
            elif _test.get('errcode') == -14:
                bot._token_expired = True
            elif _test.get('errcode') == 0:
                _token_ok = True
            else:
                # ★ 其他业务错误不一定是token过期，不标记
                print(f'[启动检测] 业务错误 errcode={_test.get("errcode")}, 不标记过期', file=sys.__stdout__)
        except:
            # ★ 异常不标记过期，让run_loop自己处理
            print('[启动检测] 预检异常，跳过（非token问题）', file=sys.__stdout__)
    # Start agent in a supervised daemon thread that auto-restarts on crash
    def _agent_wrapper():
        while True:
            try:
                print('[Bot] agent.run() 启动', file=sys.__stdout__)
                agent.run()
            except Exception as e:
                print(f'[Bot] agent.run() 异常退出: {e}，5s后重启', file=sys.__stdout__)
                time.sleep(5)
    
    # ★ Watchdog：监控主run_loop是否存活，死亡则重启整个进程
    def _watchdog():
        import subprocess as _sp
        _my_pid = os.getpid()
        _ps_cmd = (
            'Get-Process python -ErrorAction SilentlyContinue | '
            'Select-Object Id, @{Name="Cmd";Expression={(Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine}} | '
            'Where-Object { $_.Cmd -like "*wechatapp*" } | ForEach-Object { "$($_.Id) $($_.Cmd)" }'
        )
        while True:
            time.sleep(30)
            try:
                _out = _sp.check_output(
                    ['powershell', '-NoProfile', '-Command', _ps_cmd],
                    timeout=15
                ).decode('utf-8', errors='replace').strip()
                if not _out:
                    print('[Watchdog] 无wechatapp进程，5s后重启', file=sys.__stdout__)
                    time.sleep(5)
                    os.system(f'start /B python "{__file__}"')
                    sys.exit(0)
            except Exception as e:
                pass
    threading.Thread(target=_watchdog, daemon=True).start()
    threading.Thread(target=_agent_wrapper, daemon=True).start()
    print(f'WeChat Bot 已启动 (bot_id={bot.bot_id})', file=sys.__stdout__)
    bot.run_loop(on_message)