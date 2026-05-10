import os, sys, re, threading, queue, time, socket, json, struct, base64, uuid, hashlib, math, shutil, subprocess
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
_trace.write(f'[{time.strftime("%H:%M:%S")}] TRACE: after import requests,qrcode\n')
_trace.flush()
import socket as _socket
_trace.write(f'[{time.strftime("%H:%M:%S")}] TRACE: after import socket\n')
_trace.flush()

_API_HOST = 'ilinkai.weixin.qq.com'

# 显式代理配置：不依赖环境变量（nssm服务为SYSTEM用户，无用户环境变量）
_PROXY = 'http://127.0.0.1:7897'
_PROXIES = {'http': _PROXY, 'https': _PROXY}
os.environ.setdefault('http_proxy', _PROXY)
os.environ.setdefault('https_proxy', _PROXY)
os.environ.setdefault('HTTP_PROXY', _PROXY)
os.environ.setdefault('HTTPS_PROXY', _PROXY)

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
        self._token_expired = False  # ★ 初始化token过期标记
        if not self.token: self._load()

    def _load(self):
        if self._tf.exists():
            d = json.loads(self._tf.read_text('utf-8'))
            self.token, self.bot_id, self._buf = d.get('bot_token',''), d.get('ilink_bot_id',''), d.get('updates_buf','')
            self._login_time = d.get('login_time', '')  # 记录登录时间用于过期检测
            self._admin_notify_uid = d.get('admin_notify_uid', '')  # 恢复通知用户
            self._admin_uid_saved = bool(self._admin_notify_uid)

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

    def _token_near_expiry(self, threshold_hours=20):
        """token是否接近过期（默认20小时，微信token通常24小时过期）"""
        age = self._token_age_hours()
        return age >= 0 and age >= threshold_hours

    def _post(self, ep, body, timeout=15):
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
             'Authorization': f'Bearer {tok}'}
        try:
            r = requests.post(f'{API}/{ep}', data=data, headers=h, timeout=timeout, proxies=_PROXIES)
            r.raise_for_status()
            resp = r.json()
            # 检查业务层错误码
            ec = resp.get('errcode')
            if ec and ec != 0:
                em = resp.get('errmsg', '')
                print(f'[POST] {ep} 业务错误: errcode={ec} errmsg={em}', file=sys.__stderr__)
                if ec == -14:
                    # ★ 刚重登完成30s内忽略-14，避免QR死循环
                    if time.time() - getattr(self, '_relogin_time', 0) < 30:
                        print(f'[POST] {ep} -14 在grace period内，忽略', file=sys.__stdout__)
                    else:
                        self._token_expired = True
                    self._buf = ''
                    self._save()
            return resp
        except requests.exceptions.Timeout:
            print(f'[POST] {ep} 超时 (> {timeout}s)', file=sys.__stderr__)
            return {'errcode': -2, 'errmsg': 'timeout', 'endpoint': ep}
        except requests.exceptions.ConnectionError as e:
            print(f'[POST] {ep} 连接错误: {e}', file=sys.__stderr__)
            return {'errcode': -3, 'errmsg': 'connection_error', 'endpoint': ep}
        except Exception as e:
            print(f'[POST] {ep} 未知错误: {type(e).__name__}: {e}', file=sys.__stderr__)
            return {'errcode': -99, 'errmsg': str(e), 'endpoint': ep}

    def login_qr(self, poll_interval=2):
        r = requests.get(f'{API}/ilink/bot/get_bot_qrcode', params={'bot_type': 3}, headers={'User-Agent': UA}, timeout=10, proxies=_PROXIES)
        r.raise_for_status()
        d = r.json()
        qr_id, url = d['qrcode'], d.get('qrcode_img_content', '')
        print(f'[QR登录] ID: {qr_id}')
        if url:
            img = self._tf.parent / 'wx_qr.png'
            qrcode.make(url).save(str(img))
            qr = qrcode.QRCode(border=1); qr.add_data(url); qr.make(fit=True); qr.print_ascii(invert=True)
        last = ''
        while True:
            time.sleep(poll_interval)
            try: s = requests.get(f'{API}/ilink/bot/get_qrcode_status', params={'qrcode': qr_id}, headers={'User-Agent': UA}, timeout=60, proxies=_PROXIES).json()
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
        """获取二维码并保存到文件，返回 qr_id。不阻塞主循环。10分钟冷却期避免重复生成。"""
        # ★ 冷却期检查：10分钟内不重复请求API生成二维码（覆盖退避周期60+120+240+480s）
        QR_COOLDOWN = 600
        now = time.time()
        last = getattr(self, '_last_qr_gen_time', 0)
        if now - last < QR_COOLDOWN:
            _out = sys.__stdout__ if sys.__stdout__ else sys.stdout
            print(f'[QR] 冷却中（{QR_COOLDOWN - int(now - last)}s后可用），跳过重复生成', file=_out)
            old_qr_id = getattr(self, '_last_qr_id', None)
            old_url = getattr(self, '_last_qr_url', None)
            if old_qr_id:
                return old_qr_id, old_url
            return None, None
        try:
            r = requests.get(f'{API}/ilink/bot/get_bot_qrcode',
                             params={'bot_type': 3}, headers={'User-Agent': UA}, timeout=10, proxies=_PROXIES)
            r.raise_for_status()
            d = r.json()
            qr_id, url = d['qrcode'], d.get('qrcode_img_content', '')
            _out = sys.__stdout__ if sys.__stdout__ else sys.stdout
            print(f'[QR] ID: {qr_id}', file=_out)
            if url:
                img_path = str(self._tf.parent / 'wx_qr_relogin.png')
                qrcode.make(url).save(img_path)
                print(f'[QR] 二维码已保存: {img_path}', file=_out)
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
        self._save(login_time=self._login_time)
        self._token_expired = False
        self._relogin_time = time.time()  # 30s grace period after relogin
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
                                 headers={'User-Agent': UA}, timeout=60, proxies=_PROXIES).json()
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
                return False
        print(f'[QR] 超时（{max_wait}s）', file=sys.__stdout__)
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
                r = requests.post(url, data=data, headers={'Content-Type': 'application/octet-stream', 'User-Agent': UA}, timeout=timeout, proxies=_PROXIES)
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
        self._token_expired = getattr(self, '_token_expired', False)
        _relogin_attempts = 0  # 连续重登失败次数（指数退避）
        while True:
            try:
                # Token 快过期时提前刷新（非阻塞）
                if not getattr(self, '_token_expired', False) and self._token_near_expiry(threshold_hours=20):
                    age = self._token_age_hours()
                    print(f'[Bot] Token 已 {age:.1f}h，接近过期，提前刷新...', file=_out)
                    self._token_expired = True

                # Token 过期时自动重登录（非阻塞）
                if getattr(self, '_token_expired', False):
                    print('[Bot] 检测到 token 过期，获取二维码...', file=_out)
                    qr_id, qr_url = self.login_qr_nonblocking()
                    if not qr_id:
                        print('[Bot] 获取二维码失败，30s后重试', file=_out)
                        time.sleep(30)
                        continue
                    # 发二维码给指定通知用户（优先）+ seen列表兜底
                    qr_img = str(self._tf.parent / 'wx_qr_relogin.png')
                    notify_uids = []
                    # 从token文件读指定通知用户
                    try:
                        tf_data = json.loads(self._tf.read_text('utf-8'))
                        admin_uid = tf_data.get('admin_notify_uid', '')
                        if admin_uid:
                            notify_uids.append(admin_uid)
                    except Exception:
                        pass
                    # 兜底：发给最近的用户
                    notify_uids += list(seen)[-3:]
                    sent = False
                    for uid in notify_uids:
                        try:
                            self.send_image(uid, qr_img)
                            self.send_text(uid, 'Token 已过期/即将过期，请扫码重新登录\n扫码后请回复任意消息确认')
                            sent = True
                            print(f'[Bot] 二维码已发给: {uid}', file=_out)
                        except Exception as e:
                            print(f'[Bot] 发给 {uid} 失败: {e}', file=_out)
                    if not sent:
                        print('[Bot] 未能发送二维码，请扫码: D:\\GenericAgent\\wx_qr_relogin.png', file=_out)
                    # 等待扫码（180s）
                    ok = self.poll_qr_status(qr_id, max_wait=180)
                    if ok:
                        print('[Bot] 重登录成功，恢复监听', file=_out)
                        self._token_expired = False
                        _relogin_attempts = 0
                    else:
                        # 指数退避：60s → 120s → 240s → 480s（最大8分钟）
                        wait = min(60 * (2 ** _relogin_attempts), 480)
                        _relogin_attempts += 1
                        print(f'[Bot] 扫码超时，{wait}s后重试（第{_relogin_attempts}次）', file=sys.__stdout__)
                        time.sleep(wait)
                        # _token_expired 保持 True，下次循环继续重登
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

# ═══ 预编译正则（避免每次_clean/_strip_md调用重复编译） ═══
_RE_COMPILE = lambda p, f=0: re.compile(p, f)
_CLEAN_RES = [
    _RE_COMPILE(r'<summary>.*?</summary>', re.DOTALL),
    _RE_COMPILE(r'^\s*LLM Running \(Turn \d+\) \.{3}\s*$', re.M),
    _RE_COMPILE(r'^\s*(调用工具\w+|读取文件\s+\S+|写入文件\s+\S+|执行脚本\s+\S+).*$', re.M),
    _RE_COMPILE(r'^\s*🔧\s*\w+\(.*$', re.M),
    _RE_COMPILE(r'^\s*(\[Driver\].*|\[CDP\].*|\[Timeout.*\].*|Executing:.*|Timeout Error.*|Error:.*|Traceback.*)$', re.M),
    _RE_COMPILE(r'^\s*args:\s*\{.*$', re.M),
    _RE_COMPILE(r'^\s*🛠️\s*\w+\(.*$', re.M),
    _RE_COMPILE(r'^\s*\{["\']status["\'].*$', re.M),
    _RE_COMPILE(r'^\s*={3,}\s*(Response|Prompt)\s*={3,}\s*$', re.M),
    _RE_COMPILE(r'^\s*["\'](exit_code|stdout|stderr)["\'].*$', re.M),
    _RE_COMPILE(r'^\s*⏳.*$', re.M),
    _RE_COMPILE(r"^\s*(I'll|I'm|Let me|I need to|I will|I can|I should|I've|We need to)\s+.*$", re.M),
    _RE_COMPILE(r'^\s*(抱歉[，！!]?.*|让我先.*|重新来|重新执行|重新搜索).*$', re.M),
    _RE_COMPILE(r'^\s*(好的[，,]?.*|不需要走|直接搜索|直接执行|这个任务).*$', re.M),
    _RE_COMPILE(r'^\s*(让我帮你|我来搜索|我来查|让我查|搜索结果显示|根据搜索结果|现在来回答|现在回复|我来回答).*$', re.M),
    _RE_COMPILE(r'^\s*(首先|其次|最后|然后|接着)\s+(调用|读取|写入|搜索|查看|执行).*$', re.M),
    _RE_COMPILE(r'^\s*工具调用结果.*$', re.M),
    _RE_COMPILE(r'\n{3,}', 0),
]
# 段落级思考过滤（单独处理，含动态参数）
_THINK_KWS = r'用户问的是|但回复规则|规则模板错配|我应该|不过规则说|搜索失败|用已有知识|直接回答|思考过程|分析步骤|规则引用|数据获取成功|让我解析一下|让我换个方式|搜索中|正在搜索|正在获取|稍等一下'

def _strip_md(t, device='mobile'):
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
        code_max_lines = 15 if device == 'pc' else 8
        code_keep_lines = 11 if device == 'pc' else 6
        if len(lines) > code_max_lines:
            kept = lines[:code_keep_lines]
            return f'{fence}{lang_line}\n' + '\n'.join(kept) + f'\n⋯ ({len(lines)-code_keep_lines} 行省略)\n' + fence
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
    if device == 'pc':
        t = re.sub(r'^#{5}\s+(.+)', r'  ▸ \1', t, flags=re.M)
        t = re.sub(r'^#{6}\s+(.+)', r'    ◦ \1', t, flags=re.M)
    else:
        t = re.sub(r'^#{5,6}\s+', '', t, flags=re.M)                 # H5-H6: strip (too small on mobile)
    # unordered list: bullet with slight indent
    t = re.sub(r'^\s*[-*+]\s+', '  • ', t, flags=re.M)
    # ordered list: keep number but add spacing
    t = re.sub(r'^(\s*)(\d+)\.\s+', r'\1\2. ', t, flags=re.M)
    # blockquote: replace with indented style + vertical bar
    t = re.sub(r'^\s*>\s?(.+)', r'│ \1', t, flags=re.M)
    # horizontal rules: enhance with double line
    t = re.sub(r'^\s*[-*_]{3,}\s*$', '─' * 12, t, flags=re.M)
    # Add emoji to common keywords (case-insensitive, only if not already prefixed)
    # NOTE: Excluding '异常','错误','失败' to avoid GBK encoding crashes when these appear in exception messages
    t = re.sub(r'(?<!📌 )(?<!🔹 )(?<!▪️ )\b(注意|警告)\b', r'⚠️ \1', t)
    t = re.sub(r'(?<!\w)(成功|完成|通过|OK|done)\b', r'✅ \1', t, flags=re.I)
    t = re.sub(r'(?<!\w)(提示|说明|备注|Note)\b', r'💡 \1', t, flags=re.I)
    return re.sub(r'\n{3,}', '\n\n', t).strip()

def _clean(t, device='mobile'):
    # 使用预编译正则批量过滤（避免每次重复编译）
    for _re in _CLEAN_RES:
        t = _re.sub('', t)
    # TAG patterns (含file_content等，需DOTALL)
    for p in _TAG_PATS:
        t = re.sub(p, '', t, flags=re.DOTALL)
    # 段落级思考过滤
    _para_pats = _THINK_KWS
    t = re.sub(r'(?:^[^\n]*(?:' + _para_pats + r')[^\n]*\n?){1,6}', '', t, flags=re.M)
    # strip_md + 去多余空行
    t = _strip_md(t, device).strip()
    # ═══ 去重：全局去重（保留首次出现的行，后续非相邻重复也移除） ═══
    lines = t.split('\n')
    seen = set()
    deduped = []
    for line in lines:
        s = line.strip()
        # 空行始终保留
        if not s:
            deduped.append(line)
            continue
        # 非空行：全局去重（首次保留，后续重复跳过）
        if s in seen:
            continue
        seen.add(s)
        deduped.append(line)
    t = '\n'.join(deduped)
    # 行内子串去重：检测行内重复的短句（如"xxx\nxxx\nxxx内容"中xxx重复）
    # 策略：如果一行包含2+次出现的短句（8~60字），只保留最后一次出现及其后续内容
    _lines_final = []
    for _line in t.split('\n'):
        _s = _line.strip()
        if not _s:
            _lines_final.append(_line)
            continue
        # 检测行内重复子串：尝试不同长度的子串
        _deduped_line = _line
        for _sub_len in range(8, min(61, len(_s) // 2 + 1)):
            for _start in range(len(_s) - _sub_len * 2 + 1):
                _sub = _s[_start:_start + _sub_len]
                if _s.count(_sub) >= 2:
                    # 找到最后一次出现的位置，截取从该位置开始
                    _last_pos = _s.rfind(_sub)
                    _candidate = _s[_last_pos:]
                    if len(_candidate) < len(_deduped_line):
                        _deduped_line = _candidate
        _lines_final.append(_deduped_line)
    t = '\n'.join(_lines_final)
    # 段落级去重：按空行分段落，全局去重（保留首次出现）
    paras = re.split(r'\n\n+', t)
    seen_paras = set()
    dedup_paras = []
    for para in paras:
        p = para.strip()
        if not p:
            continue
        if p in seen_paras:
            continue
        seen_paras.add(p)
        dedup_paras.append(p)
    return '\n\n'.join(dedup_paras)

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

    def _handle():
        try:
            # 设备感知 sys_hint
            device = _guess_device(text, uid)
            if device == 'pc':
                sys_hint = (
                    "你是直接回复用户的助手。禁止输出思考过程、分析步骤、规则引用、工具调用描述。"
                    "只输出最终答案。格式：可用markdown表格、代码块（≤15行）、分隔线，详尽回复。"
                    "如果搜索失败，直接用知识回答。"
                )
            else:
                sys_hint = (
                    "你是直接回复用户的助手。禁止输出思考过程、分析步骤、规则引用、工具调用描述。"
                    "只输出最终答案。格式：emoji分段，每段2-3行，不超过500字。"
                    "如果搜索失败，直接用知识回答。"
                )
            prompt = text if text.startswith('/') else f"{sys_hint}\n\n用户问题：{text}"
            # ★ 修复：传入图片路径给agent
            images = media_paths if media_paths else None
            dq = agent.put_task(prompt, source="wechat", images=images)
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

            # ═══ 接收 agent 输出（只发最终done消息，不发中间chunk） ═══
            max_turns = 10
            turn_count = 0

            try:
                while True:
                    item = dq.get(timeout=120)
                    if 'done' in item:
                        result = item['done']
                        break
                    raw = item.get('next', '')
                    raw_accum += raw
                    turn_count += 1

                    # 上下文过大时提前结束
                    if len(raw_accum) > 12000:
                        print(f'[WX] 上下文已达{len(raw_accum)}字符，提前结束', file=sys.__stdout__)
                        result = raw_accum
                        break
                    if turn_count >= max_turns:
                        print(f'[WX] 达到最大轮次{max_turns}，强制结束', file=sys.__stdout__)
                        result = raw_accum
                        break
            except queue.Empty:
                result = raw_accum if raw_accum else '⏰ 响应超时，请稍后重试'
                print('[WX] agent 120s 超时', file=sys.__stdout__)

            # ═══ 只发送最终完整回复 ═══
            final = _clean(result, device)
            if not final.strip():
                final = _clean(_extract_answer(result), device)
            if final.strip():
                max_len = 2800 if device == 'pc' else 1400
                if len(final) > max_len:
                    final = final[:max_len]
                _wx_send(final)
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
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    print(f'[NEW] Process starting {time.strftime("%m-%d %H:%M")}')
    bot = WxBotClient()
    if not bot.token:
        _stdout_save = sys.__stdout__ if sys.__stdout__ else _logf
        sys.stdout = sys.stderr = _stdout_save  # restore for QR display
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
                # ★ 超时≠token过期，可能是网络波动；重试1次再决定
                print('[启动检测] 首次API超时，5s后重试...', file=sys.__stdout__)
                time.sleep(5)
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
                    # 强制标记过期，让run_loop直接进入重登录流程（避免getupdates持续超时死循环）
                    print('[启动检测] 重试仍超时，强制标记token过期→进入重登流程', file=sys.__stdout__)
                    bot._token_expired = True
                elif _test.get('errcode') == 0:
                    _token_ok = True
                elif _test.get('errcode') == -14:
                    bot._token_expired = True
                # 其他errno不标记过期（可能是临时错误）
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
    threading.Thread(target=_agent_wrapper, daemon=True).start()
    print(f'WeChat Bot 已启动 (bot_id={bot.bot_id})', file=sys.__stdout__)
    bot.run_loop(on_message)