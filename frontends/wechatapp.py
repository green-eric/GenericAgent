# 微信 Bot — wechatapp.py
# 版本: 2.0.0 — 彻底重写，修复所有已知问题
# 功能: 微信消息收发 + Agent 入口，与评分系统无直接耦合
import os, sys, re, threading, queue, time, socket, json, struct, base64, uuid, hashlib, math, shutil, subprocess
from pathlib import Path
from urllib.parse import quote

# ── 自启动日志重定向 ──
_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'temp')
os.makedirs(_LOG_DIR, exist_ok=True)
_logf = open(os.path.join(_LOG_DIR, 'wechatbot_stdout.log'), 'a', encoding='utf-8')
_logf_err = open(os.path.join(_LOG_DIR, 'wechatbot_stderr.log'), 'a', encoding='utf-8')
sys.stdout = _logf
sys.stderr = _logf_err
sys.__stdout__ = _logf
sys.__stderr__ = _logf_err
_builtin_print = print
def print(*args, file=None, **kwargs):
    if file is None or file is sys.__stdout__ or file is sys.__stderr__:
        file = _logf
    _builtin_print(*args, file=file, **kwargs)
print(f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] wechatapp.py v2.0.0 启动', file=sys.stdout)

# ── 清理 .pyc 缓存 ──
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

_API_HOST = 'ilinkai.weixin.qq.com'

# ── 代理配置 ──
_PROXY = 'http://127.0.0.1:7897'
_PROXIES = {'http': _PROXY, 'https': _PROXY}
_PROXY_OK = None
_PROXY_CHECK_TIME = 0

def _check_proxy():
    """检测代理是否可用。结果缓存60秒避免重复检测。"""
    global _PROXY_OK, _PROXY_CHECK_TIME
    if _PROXY_OK is not None and time.time() - _PROXY_CHECK_TIME < 60:
        return _PROXY_OK
    try:
        # 用腾讯接口检测，比httpbin快且不被墙
        r = requests.get(f'https://{_API_HOST}/ilink/bot/get_bot_qrcode',
                         params={'bot_type': 3}, timeout=5, proxies=_PROXIES)
        _PROXY_OK = r.status_code < 500  # 只要能连上就行，不要求业务成功
    except Exception:
        _PROXY_OK = False
    _PROXY_CHECK_TIME = time.time()
    print(f'[WX] 代理检测: {"可用" if _PROXY_OK else "不可用，将直连"}', file=sys.__stdout__)
    return _PROXY_OK

def _get_proxies():
    if _check_proxy():
        return _PROXIES
    return None

from Crypto.Cipher import AES
_trace.write(f'[{time.strftime("%H:%M:%S")}] TRACE: after Crypto.Cipher.AES\n')
_trace.flush()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'temp')
from agentmain import GeneraticAgent
try:
    from kline_chart import generate_kline as _gen_kline
except ImportError:
    _gen_kline = None
    print('[WX] kline_chart.py 未找到，K线功能不可用', file=sys.__stdout__)
_trace.write(f'[{time.strftime("%H:%M:%S")}] TRACE: after agentmain import\n')
_trace.flush()

# ── 常量 ──
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

# ── 设备模式 ──
_USER_MODE = {}

def _guess_device(text, uid):
    if uid in _USER_MODE:
        return _USER_MODE[uid]
    if len(text) > 150 or '```' in text or '\n|' in text:
        return 'pc'
    return 'mobile'

class WxBotClient:
    def __init__(self, token=None, token_file=None):
        self._tf = Path(token_file) if token_file else TOKEN_FILE
        self.token = token
        self.bot_id = None
        self._buf = ''
        self._token_expired = False
        if not self.token:
            self._load()

    def _load(self):
        if self._tf.exists():
            try:
                d = json.loads(self._tf.read_text('utf-8'))
                self.token = d.get('bot_token', '')
                self.bot_id = d.get('ilink_bot_id', '')
                self._buf = d.get('updates_buf', '')
                self._login_time = d.get('login_time', '')
                self._admin_notify_uid = d.get('admin_notify_uid', '')
            except Exception:
                pass

    def _save(self, **kw):
        existing = {}
        if self._tf.exists():
            try:
                existing = json.loads(self._tf.read_text('utf-8'))
            except Exception:
                pass
        d = {
            'bot_token': self.token or '',
            'ilink_bot_id': self.bot_id or '',
            'updates_buf': self._buf or '',
            'saved_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'login_time': getattr(self, '_login_time', '') or existing.get('login_time', ''),
            'admin_notify_uid': getattr(self, '_admin_notify_uid', '') or existing.get('admin_notify_uid', ''),
        }
        d.update(kw)
        self._tf.write_text(json.dumps(d, ensure_ascii=False, indent=2), 'utf-8')

    def _token_age_hours(self):
        if not getattr(self, '_login_time', ''):
            return -1
        try:
            lt = time.mktime(time.strptime(self._login_time, '%Y-%m-%d %H:%M:%S'))
            return (time.time() - lt) / 3600
        except Exception:
            return -1

    def _post(self, ep, body, timeout=30):
        tok = (self.token or '').strip()
        if not tok:
            return {'errcode': -1, 'errmsg': 'no_token'}
        data = json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        h = {
            'Content-Type': 'application/json',
            'AuthorizationType': 'ilink_bot_token',
            'Content-Length': str(len(data)),
            'X-WECHAT-UIN': _uin(),
            'iLink-App-Id': ILINK_APP_ID,
            'iLink-App-ClientVersion': str(ILINK_APP_CLIENT_VERSION),
            'User-Agent': UA,
            'Authorization': f'Bearer {tok}',
        }
        try:
            r = requests.post(f'{API}/{ep}', data=data, headers=h, timeout=timeout, proxies=_get_proxies())
            r.raise_for_status()
            resp = r.json()
            ec = resp.get('errcode')
            if ec and ec != 0:
                em = resp.get('errmsg', '')
                print(f'[POST] {ep} 错误: errcode={ec} errmsg={em}', file=sys.__stderr__)
                if ec == -14:
                    if time.time() - getattr(self, '_relogin_time', 0) < 30:
                        print(f'[POST] {ep} -14 在grace period内，忽略', file=sys.__stdout__)
                    else:
                        self._token_expired = True
                    self._save()
            return resp
        except requests.exceptions.Timeout:
            return {'errcode': -2, 'errmsg': 'timeout'}
        except requests.exceptions.ConnectionError as e:
            return {'errcode': -3, 'errmsg': 'connection_error'}
        except Exception as e:
            return {'errcode': -99, 'errmsg': str(e)}

    def _post_retry(self, ep, body, timeout=30, retries=2):
        """带重试的POST，网络错误时自动重试。"""
        for attempt in range(retries + 1):
            resp = self._post(ep, body, timeout=timeout)
            ec = resp.get('errcode', 0)
            if ec >= 0 or ec == -14:
                return resp
            if attempt < retries:
                wait = 3 * (attempt + 1)
                print(f'[POST] {ep} 重试 {attempt+1}/{retries}，等{wait}s', file=sys.__stdout__)
                time.sleep(wait)
        return resp

    def login_qr(self, poll_interval=2):
        r = requests.get(f'{API}/ilink/bot/get_bot_qrcode', params={'bot_type': 3},
                         headers={'User-Agent': UA}, timeout=10, proxies=_get_proxies())
        r.raise_for_status()
        d = r.json()
        qr_id, url = d['qrcode'], d.get('qrcode_img_content', '')
        print(f'[QR登录] ID: {qr_id}', file=sys.__stdout__)
        if url:
            img = self._tf.parent / 'wx_qr.png'
            qrcode.make(url).save(str(img))
            qr = qrcode.QRCode(border=1)
            qr.add_data(url)
            qr.make(fit=True)
            qr.print_ascii(invert=True)
        last = ''
        while True:
            time.sleep(poll_interval)
            try:
                s = requests.get(f'{API}/ilink/bot/get_qrcode_status',
                                 params={'qrcode': qr_id},
                                 headers={'User-Agent': UA}, timeout=60,
                                 proxies=_get_proxies()).json()
            except requests.exceptions.ReadTimeout:
                continue
            st = s.get('status', '')
            if st != last:
                print(f'  QR状态: {st}', file=sys.__stdout__)
                last = st
            if st == 'confirmed':
                self.token = s.get('bot_token', '')
                self.bot_id = s.get('ilink_bot_id', '')
                self._login_time = time.strftime('%Y-%m-%d %H:%M:%S')
                self._token_expired = False
                self._relogin_time = time.time()
                self._save(login_time=self._login_time)
                print(f'[QR登录] 成功! bot_id={self.bot_id}', file=sys.__stdout__)
                return s
            if st == 'expired':
                raise RuntimeError('二维码过期')

    def login_qr_nonblocking(self):
        """获取二维码，返回 (qr_id, url)。失败返回 (None, None)。"""
        try:
            r = requests.get(f'{API}/ilink/bot/get_bot_qrcode', params={'bot_type': 3},
                             headers={'User-Agent': UA}, timeout=10, proxies=_get_proxies())
            r.raise_for_status()
            d = r.json()
            qr_id, url = d['qrcode'], d.get('qrcode_img_content', '')
            if url:
                img = self._tf.parent / 'wx_qr_relogin.png'
                qrcode.make(url).save(str(img))
            self._last_qr_id = qr_id
            self._last_qr_url = url
            return qr_id, url
        except Exception as e:
            print(f'[QR] 获取失败: {e}', file=sys.__stdout__)
            return None, None

    def _on_login_success(self):
        self._login_time = time.strftime('%Y-%m-%d %H:%M:%S')
        self._save(login_time=self._login_time)
        self._token_expired = False
        self._relogin_time = time.time()
        print(f'[Bot] token刷新，登录时间: {self._login_time}', file=sys.__stdout__)

    def poll_qr_status(self, qr_id, max_wait=180):
        """非阻塞轮询二维码状态。返回 True=确认, False=超时/过期。"""
        deadline = time.time() + max_wait
        while time.time() < deadline:
            try:
                s = requests.get(f'{API}/ilink/bot/get_qrcode_status',
                                 params={'qrcode': qr_id},
                                 headers={'User-Agent': UA}, timeout=30,
                                 proxies=_get_proxies()).json()
                st = s.get('status', '')
                if st == 'confirmed':
                    self.token = s.get('bot_token', '')
                    self.bot_id = s.get('ilink_bot_id', '')
                    self._on_login_success()
                    return True
                if st == 'expired':
                    return False
            except Exception:
                pass
            time.sleep(2)
        return False

    def get_updates(self, timeout=60):
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

    def send_text(self, uid, text, context_token='', media_paths=None):
        """发送文本消息，带重试。返回 True=成功。"""
        if not text or not text.strip():
            return False
        body = {
            'receiver': {'uid': uid},
            'msg_list': [{
                'msg_type': ITEM_TEXT,
                'text': {'content': text},
            }],
            'context_token': context_token or '',
        }
        for attempt in range(3):
            resp = self._post('ilink/bot/send_message', body, timeout=15)
            ec = resp.get('errcode', 0)
            if ec == 0:
                print(f'[WX] send ok len={len(text)} uid={uid[:20]}', file=sys.__stdout__)
                return True
            if ec == -14:
                self._token_expired = True
                print(f'[WX] send token过期', file=sys.__stderr__)
                return False
            em = resp.get('errmsg', '')
            print(f'[WX] send err={ec} {em} attempt={attempt+1}', file=sys.__stderr__)
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
        return False

    def send_typing(self, to_user_id, typing_ticket='', cancel=False):
        return self._post('ilink/bot/sendtyping', {
            'ilink_user_id': to_user_id, 'typing_ticket': typing_ticket,
            'status': 2 if cancel else 1,
            'base_info': {'channel_version': VER}})

    def get_typing_ticket(self, to_user_id, context_token=''):
        payload = {'ilink_user_id': to_user_id}
        if context_token: payload['context_token'] = context_token
        return self._post('ilink/bot/getconfig', payload).get('typing_ticket', '')

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
            'receiver': {'uid': uid},
            'msg_list': [{
                'msg_type': ITEM_TEXT,
                'text': {'content': text},
            }],
            'context_token': context_token or '',
        }
        for attempt in range(3):
            resp = self._post('ilink/bot/send_message', body, timeout=15)
            ec = resp.get('errcode', 0)
            if ec == 0:
                print(f'[WX] send ok len={len(text)} uid={uid[:20]}', file=sys.__stdout__)
                return True
            if ec == -14:
                self._token_expired = True
                print(f'[WX] send token过期', file=sys.__stderr__)
                return False
            em = resp.get('errmsg', '')
            print(f'[WX] send err={ec} {em} attempt={attempt+1}', file=sys.__stderr__)
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
        return False

    def send_image(self, uid, path, context_token=''):
        return self._send_file(uid, path, ITEM_IMAGE, context_token)

    def send_file(self, uid, path, context_token=''):
        return self._send_file(uid, path, ITEM_FILE, context_token)

    def send_video(self, uid, path, context_token=''):
        return self._send_file(uid, path, ITEM_VIDEO, context_token)

    def _send_file(self, uid, path, msg_type, context_token=''):
        """上传文件并发送。"""
        try:
            fname = os.path.basename(path)
            size = os.path.getsize(path)
            # 1. 获取上传URL
            r = self._post('ilink/bot/get_upload_url', {
                'file_name': fname, 'file_size': size, 'file_type': msg_type
            }, timeout=10)
            if r.get('errcode') != 0:
                print(f'[WX] upload_url err: {r}', file=sys.__stderr__)
                return False
            upload_url = r.get('upload_url', '')
            file_id = r.get('file_id', '')
            # 2. 上传
            with open(path, 'rb') as fh:
                up = requests.put(upload_url, data=fh, headers={'Content-Type': 'application/octet-stream'},
                                  timeout=60, proxies=_get_proxies())
            if up.status_code not in (200, 204):
                print(f'[WX] upload fail: {up.status_code}', file=sys.__stderr__)
                return False
            # 3. 发送
            body = {
                'receiver': {'uid': uid},
                'msg_list': [{
                    'msg_type': msg_type,
                    'file': {'file_id': file_id, 'file_name': fname, 'file_size': size},
                }],
                'context_token': context_token or '',
            }
            resp = self._post('ilink/bot/send_message', body, timeout=15)
            ec = resp.get('errcode', 0)
            if ec == 0:
                print(f'[WX] sent file: {fname}', file=sys.__stdout__)
            return ec == 0
        except Exception as e:
            print(f'[WX] send_file err: {e}', file=sys.__stderr__)
            return False

    def get_updates(self, limit=10, timeout=20):
        """拉取消息。返回消息列表（可能为空）。"""
        body = {'limit': limit, 'timeout': timeout}
        if self._buf:
            body['updates_buf'] = self._buf
        resp = self._post('ilink/bot/getupdates', body, timeout=timeout + 10)
        ec = resp.get('errcode', 0)
        if ec == 0:
            self._buf = resp.get('updates_buf', '')
            self._save()  # 持久化buf断点
            return resp.get('msg_list', [])
        if ec == -14:
            self._token_expired = True
        return []

    def run_loop(self, on_message):
        """主循环：拉取消息 → 回调处理。token过期时自动走重登流程。"""
        print('[Bot] run_loop 启动', file=sys.__stdout__)
        seen = set()  # 去重：消息ID集合（有限大小）
        SEEN_MAX = 500

        while True:
            try:
                # ── token过期 → 走重登 ──
                if self._token_expired:
                    print('[Bot] token过期，启动重登...', file=sys.__stdout__)
                    qr_id, url = self.login_qr_nonblocking()
                    if not qr_id:
                        print('[Bot] 获取二维码失败，30s后重试', file=sys.__stdout__)
                        time.sleep(30)
                        continue
                    # 通知管理员扫码
                    qr_img = str(self._tf.parent / 'wx_qr_relogin.png')
                    notify_uids = []
                    try:
                        tf_data = json.loads(self._tf.read_text('utf-8'))
                        admin_uid = tf_data.get('admin_notify_uid', '')
                        if admin_uid:
                            notify_uids.append(admin_uid)
                    except Exception:
                        pass
                    for nuid in notify_uids:
                        self.send_text(nuid, '🔑 Token已过期，请扫码重新登录：\n' + (url or qr_img))
                    # 等待扫码
                    ok = self.poll_qr_status(qr_id, max_wait=180)
                    if not ok:
                        print('[Bot] 扫码超时/过期，重新获取...', file=sys.__stdout__)
                        time.sleep(5)
                        continue
                    self._token_expired = False
                    seen.clear()
                    print('[Bot] 重登成功，恢复消息拉取', file=sys.__stdout__)

                # ── 正常拉取 ──
                try:
                    msgs = self.get_updates(limit=10, timeout=20)
                except Exception as e:
                    print(f'[Bot] get_updates 异常: {e}，10s后重试', file=sys.__stdout__)
                    time.sleep(10)
                    continue

                if not msgs:
                    continue

                for msg in msgs:
                    try:
                        mid = msg.get('msg_id', '') or str(hash(str(msg)))
                        if mid in seen:
                            continue
                        seen.add(mid)
                        if len(seen) > SEEN_MAX:
                            # 清理最旧的1/3
                            seen_list = list(seen)[SEEN_MAX // 3:]
                            seen.clear()
                            seen.update(seen_list)

                        # 只处理用户消息
                        if msg.get('from_user', {}).get('uid', '') == self.bot_id:
                            continue

                        uid = msg.get('from_user', {}).get('uid', '')
                        ctx = msg.get('context_token', '')
                        text = ''
                        media = []
                        for item in msg.get('msg_list', []):
                            mt = item.get('msg_type', 0)
                            if mt == ITEM_TEXT:
                                text += item.get('text', {}).get('content', '')
                            elif mt in (ITEM_IMAGE, ITEM_FILE, ITEM_VIDEO):
                                media.append({'type': mt, 'data': item})

                        if not text and not media:
                            continue

                        # 记录admin_notify_uid
                        if uid and not getattr(self, '_admin_uid_saved', False):
                            self._admin_notify_uid = uid
                            self._admin_uid_saved = True
                            self._save(admin_notify_uid=uid)
                            print(f'[Bot] 记录通知用户: {uid}', file=sys.__stdout__)

                        print(f'[WX] 收到: {text[:80]} media={len(media)} uid={uid[:20]}', file=sys.__stdout__)
                        on_message(self, uid, text, ctx, media)
                    except Exception as e:
                        import traceback
                        print(f'[Bot] 处理消息异常: {e}', file=sys.__stderr__)
                        traceback.print_exc(file=sys.__stderr__)

            except KeyboardInterrupt:
                print('[Bot] 收到中断，退出', file=sys.__stdout__)
                break
            except Exception as e:
                import traceback
                print(f'[Bot] run_loop 未捕获异常: {e}', file=sys.__stderr__)
                traceback.print_exc(file=sys.__stderr__)
                time.sleep(10)

# ── 消息清洗 ──
def _RE_COMPILE(p, f=0):
    return re.compile(p, f)

_FILTER_RES = [
    _RE_COMPILE(r'^\s*🛠️\s*\w+\(.*$', re.M),
    _RE_COMPILE(r'^\s*\{["\']status["\'].*$', re.M),
    _RE_COMPILE(r'^\s*={3,}\s*(Response|Prompt)\s*={3,}\s*$', re.M),
    _RE_COMPILE(r'^\s*["\'](exit_code|stdout|stderr)["\'].*$', re.M),
    _RE_COMPILE(r'^\s*⏳.*$', re.M),
    _RE_COMPILE(r"^\s*(I'll|I'm|Let me|I need to|I will|I can|I should|I've|We need to)\s+.*$", re.M),
    _RE_COMPILE(r'^\s*(抱歉|好的|收到|明白|我来|让我|我将|我需要)\s*[，,：:。.！!]?\s*$', re.M),
    _RE_COMPILE(r'^\s*#{1,6}\s+(工具调用|思考|分析|执行|总结|步骤|处理中)\s*$', re.M),
    _RE_COMPILE(r'^\s*\[(?:Driver|CDP|Timeout|Debug|Usage|Cache|POST|GET|QR|WX|Bot)\].*$', re.M),
    _RE_COMPILE(r'^\s*LLM Running \(Turn \d+\) \.{3}\s*$', re.M),
    _RE_COMPILE(r'^\s*(调用工具\w+|读取文件\s+\S+|写入文件\s+\S+|执行脚本\s+\S+).*$', re.M),
    _RE_COMPILE(r'^\s*🔧\s*\w+\(.*$', re.M),
    _RE_COMPILE(r'^\s*args:\s*\{.*$', re.M),
    _RE_COMPILE(r'^\s*\d+[\.\)]\s*$', re.M),
    _RE_COMPILE(r'^\s*[-—]\s*$', re.M),
    _RE_COMPILE(r'^\s*[-—*#_=~]{3,}\s*$', re.M),
    _RE_COMPILE(r'^\s*$', re.M),
]

def clean(text):
    """清洗Agent输出，只保留用户可见内容。"""
    if not text:
        return ''
    text = text.strip()
    # 快速路径：短文本不处理
    if len(text) < 10:
        return text
    lines = text.split('\n')
    result = []
    for line in lines:
        line = line.rstrip()
        if not line:
            if result and result[-1] != '':
                result.append('')
            continue
        skip = False
        for pat in _FILTER_RES:
            if pat.match(line):
                skip = True
                break
        if not skip:
            result.append(line)
    # 去连续空行
    out = '\n'.join(result).strip()
    while '\n\n\n' in out:
        out = out.replace('\n\n\n', '\n\n')
    return out

def _format_for_device(text, device):
    """根据设备类型格式化输出。"""
    if not text:
        return text
    if device == 'mobile':
        # 手机端：简化markdown
        text = re.sub(r'```\w*\n?', '', text)
        text = re.sub(r'\*\*(.+?)\*\*', r'【\1】', text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'`(.+?)`', r'\1', text)
        text = re.sub(r'^#{1,3}\s+', '', text, flags=re.M)
    return text

# ── 单实例锁 ──
_lock_socket = None

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

def _ensure_single():
    global _lock_socket
    try:
        _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _lock_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _lock_socket.bind(('127.0.0.1', 38765))
        _lock_socket.listen(1)
        print('[WX] 单实例锁成功 (port 38765)', file=sys.__stdout__)
        return True
    except OSError:
        print('[WX] 已有实例在运行 (port 38765 占用)，退出', file=sys.__stderr__)
        return False

# ── 主入口 ──
def main():
    # 单实例检查
    if not _ensure_single():
        sys.exit(1)

    bot = WxBotClient()
    if not bot.token:
        print('[Bot] 无token，启动二维码登录...', file=sys.__stdout__)
        bot.login_qr()

    print(f'[Bot] 已登录 bot_id={bot.bot_id}', file=sys.__stdout__)

    # ── Agent 回调 ──
    def _on_message(bot, uid, text, ctx, media):
        device = _guess_device(text, uid)

        # 特殊命令
        if text.strip() == '/help':
            bot.send_text(uid, '📋 命令:\n/pc - 电脑端模式\n/mobile - 手机端模式\n/help - 帮助', context_token=ctx)
            return
        if text.strip() == '/pc':
            _USER_MODE[uid] = 'pc'
            bot.send_text(uid, '🖥️ 已切换为电脑端模式', context_token=ctx)
            return
        if text.strip() == '/mobile':
            _USER_MODE[uid] = 'mobile'
            bot.send_text(uid, '📱 已切换为手机端模式', context_token=ctx)
            return

        # 先回复"处理中"
        bot.send_text(uid, '⏳ 处理中...', context_token=ctx)

        try:
            agent = GeneraticAgent(session_key=f'wx_{uid}', model=None)
            reply = agent.run(text)
            reply = clean(reply)
            reply = _format_for_device(reply, device)
            if not reply:
                reply = '✅ 已处理（无文本输出）'
            # 分段发送（微信单条限制约2000字）
            MAX_LEN = 1800
            if len(reply) <= MAX_LEN:
                bot.send_text(uid, reply, context_token=ctx)
            else:
                # 按段落分段
                parts = []
                current = ''
                for para in reply.split('\n'):
                    if len(current) + len(para) + 1 > MAX_LEN:
                        if current:
                            parts.append(current)
                        current = para
                    else:
                        current = (current + '\n' + para) if current else para
                if current:
                    parts.append(current)
                for i, part in enumerate(parts):
                    if part.strip():
                        bot.send_text(uid, part, context_token=ctx)
                        if i < len(parts) - 1:
                            time.sleep(0.3)
        except Exception as e:
            import traceback
            print(f'[Bot] Agent处理异常: {e}', file=sys.__stderr__)
            traceback.print_exc(file=sys.__stderr__)
            try:
                bot.send_text(uid, f'❌ 处理异常: {str(e)[:100]}', context_token=ctx)
            except Exception:
                pass

    # ── 启动 Agent 线程 ──
    def _agent_wrapper():
        print('[Bot] Agent线程启动', file=sys.__stdout__)
        try:
            agent = GeneraticAgent(session_key='wx_agent', model=None)
            agent.run()
        except Exception as e:
            print(f'[Bot] Agent异常: {e}', file=sys.__stderr__)
        print('[Bot] Agent线程退出', file=sys.__stdout__)

    threading.Thread(target=_agent_wrapper, daemon=True).start()
    print(f'WeChat Bot 已启动 (bot_id={bot.bot_id})', file=sys.__stdout__)
    bot.run_loop(_on_message)

if __name__ == '__main__':
    main()
