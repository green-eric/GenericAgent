#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股利好监控系统 - HTTP 服务器入口
负责处理HTTP请求和数据响应

重构后版本：ServerHandler 仅负责 HTTP 协议处理，
业务逻辑委托给 controllers 模块，响应构建委托给 response_builder 模块。
"""

import hmac
import json
import os
import threading
import time
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional


class DataEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理Python set类型和其他不可序列化类型"""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, frozenset):
            return list(obj)
        return super().default(obj)


from urllib.parse import parse_qs, urlparse

from modules import log_system_error, run_pipeline
from modules.logging_config import setup_all_loggers
from modules.utils import BJT, config_manager, get_config_value
from modules.constants import DIST_DIR, CALIBRATION_CACHE_FILE, LOG_DIR

from .api_handlers import (
    build_agent_response,
    build_response_data,
    validate_request_params,
)
from .cache_manager import pipeline_lock, server_cache
from .controllers import ConfigController, DataController, SystemController
from .data_formatter import format_hot8_data, format_news_data, is_market_hours
from .pipeline_manager import PARAMS, get_pipeline_data as _get_pipeline_data

logger = setup_all_loggers()
log = logger


class _ForceRefreshRateLimiter:
    """force_refresh 速率限制器

    防止客户端反复发送 force_refresh=true 导致 Pipeline 连续执行，
    触发大量 API 调用和计算开销。

    策略：每个客户端 IP 在冷却时间（默认30秒）内只允许一次 force_refresh。
    全局维度也限制：任何时间窗口内最多 N 次 force_refresh/秒。
    """

    def __init__(self, cooldown: float = 30.0) -> None:
        self._cooldown = cooldown
        self._per_ip: Dict[str, float] = {}
        self._global_last: float = 0.0
        self._lock = threading.Lock()

    def allow(self, client_ip: str) -> bool:
        now = time.time()
        with self._lock:
            if now - self._global_last < 5.0:
                return False
            last_time = self._per_ip.get(client_ip, 0.0)
            if now - last_time < self._cooldown:
                return False
            self._per_ip[client_ip] = now
            self._global_last = now
            return True

    def get_cooldown_remaining(self, client_ip: str) -> float:
        now = time.time()
        with self._lock:
            last_time = self._per_ip.get(client_ip, 0.0)
            remaining = self._cooldown - (now - last_time)
            return max(0.0, remaining)

    def cleanup(self) -> None:
        now = time.time()
        with self._lock:
            expired_threshold = now - self._cooldown * 2
            self._per_ip = {
                ip: t for ip, t in self._per_ip.items() if t > expired_threshold
            }


_force_refresh_limiter = _ForceRefreshRateLimiter(cooldown=30.0)


def get_pipeline_data(
    force_refresh: bool = False,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """获取流水线数据和回测数据（包装函数）"""
    return _get_pipeline_data(force_refresh)


def reload_params() -> None:
    """重新加载配置参数（兼容函数）"""
    from .pipeline_manager import reload_params as _reload_params

    _reload_params()


def background_data_updater() -> None:
    """后台数据更新（兼容函数）"""
    from .background_tasks import background_data_updater as _background_updater

    _background_updater()


def agent_report_updater() -> None:
    """Agent报告更新（兼容函数）"""
    from .background_tasks import agent_report_updater as _agent_updater

    _agent_updater()


background_thread_running: bool = False


class ServerHandler(SimpleHTTPRequestHandler):
    """HTTP 请求处理器（重构后版本）

    仅负责 HTTP 协议处理（路由分发、认证、响应发送），
    业务逻辑委托给 controllers 模块。
    """

    server_cache = server_cache
    pipeline_lock = pipeline_lock

    def _set_cors_headers(self) -> None:
        allowed_origin = os.getenv("ALLOWED_ORIGIN", "")
        if not allowed_origin:
            allowed_origin = "*"
            log.warning("CORS ALLOWED_ORIGIN 未设置，建议在生产环境配置具体域名")
        elif allowed_origin == "*":
            log.warning(
                "CORS ALLOWED_ORIGIN 设置为 '*'，存在安全风险，建议在生产环境配置具体域名"
            )

        self.send_header("Access-Control-Allow-Origin", allowed_origin)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-Key")
        self.send_header("Access-Control-Max-Age", "86400")

    def _check_api_key(self) -> bool:
        api_key = os.getenv("API_KEY", "")
        enforce_auth = os.getenv("ENFORCE_API_AUTH", "false").lower() == "true"

        if not api_key:
            if enforce_auth:
                log.warning(
                    f"API认证强制模式但未配置API_KEY，拒绝请求 from {self.client_address[0]}"
                )
                self.send_response(401)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    json.dumps(
                        {"error": "服务器未配置API_KEY，请设置API_KEY环境变量"},
                        ensure_ascii=False,
                        cls=DataEncoder,
                    ).encode("utf-8")
                )
                return False
            return True

        request_key = self.headers.get("X-API-Key", "")
        if not hmac.compare_digest(request_key, api_key):
            log.warning(f"API Key 验证失败: 请求来源 {self.client_address[0]}")
            self.send_response(401)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {"error": "未授权访问"}, ensure_ascii=False, cls=DataEncoder
                ).encode("utf-8")
            )
            return False
        return True

    def _check_read_auth(self) -> bool:
        require_read_auth = os.getenv("REQUIRE_READ_AUTH", "false").lower() == "true"
        if not require_read_auth:
            return True
        return self._check_api_key()

    def _send_json_response(self, status_code: int, data: Dict[str, Any]) -> None:
        try:
            self.send_response(status_code)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            response_json = json.dumps(data, ensure_ascii=False, cls=DataEncoder)
            self.wfile.write(response_json.encode("utf-8"))
        except Exception as e:
            log.error(f"发送JSON响应失败: {e}")

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        log.debug(f"接收到POST请求: {self.path}")

        if parsed.path == "/api/trade/delete":
            if not self._check_api_key():
                return
            try:
                content_length_str = self.headers.get("Content-Length", "0")
                try:
                    content_length = int(content_length_str)
                except ValueError:
                    content_length = 0

                if content_length == 0:
                    self._send_json_response(
                        400, {"success": False, "message": "请求体为空"}
                    )
                    return

                post_data = self.rfile.read(content_length).decode("utf-8")
                params = parse_qs(post_data)
                ConfigController.handle_trade_delete(self, params)
            except Exception as e:
                log.error(f"处理删除请求时发生异常: {e}", exc_info=True)
                self._send_json_response(
                    500, {"success": False, "message": "服务器内部错误"}
                )

        elif parsed.path == "/api/params-config":
            if not self._check_api_key():
                return
            try:
                content_length_str = self.headers.get("Content-Length", "0")
                try:
                    content_length = int(content_length_str)
                except ValueError:
                    content_length = 0

                if content_length == 0:
                    self._send_json_response(
                        400, {"success": False, "message": "请求体为空"}
                    )
                    return

                post_data = self.rfile.read(content_length).decode("utf-8")
                params = json.loads(post_data)
                ConfigController.handle_params_config_post(self, params)
            except Exception as e:
                log.error(f"处理参数更新请求时发生异常: {e}", exc_info=True)
                self._send_json_response(
                    500, {"success": False, "message": "服务器内部错误"}
                )
        else:
            self.send_error(404, "Not found")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        log.debug(f"接收到请求: {self.path}")
        if not self._check_read_auth():
            return

        if parsed.path == "/data":
            self._handle_data_route(parsed)
        elif parsed.path == "/cache/stats":
            SystemController.handle_cache_stats(self)
        elif parsed.path == "/logs":
            query_params = parse_qs(parsed.query)
            SystemController.handle_logs(self, query_params)
        elif parsed.path == "/system/errors":
            SystemController.handle_system_errors(self)
        elif parsed.path == "/system/status":
            SystemController.handle_system_status(self)
        elif parsed.path == "/api/seed-pool":
            SystemController.handle_seed_pool(self)
        elif parsed.path == "/api/backtest/refresh":
            DataController.handle_backtest_refresh(self)
        elif parsed.path == "/system/performance":
            SystemController.handle_performance(self)
        elif parsed.path == "/system/resources":
            SystemController.handle_resources(self)
        elif parsed.path == "/health":
            SystemController.handle_health_check(self)
        elif parsed.path == "/api/params-config":
            ConfigController.handle_params_config_get(self)
        elif parsed.path == "/" or parsed.path == "/index.html":
            self.path = "/index.html"
            self.send_static_file()
        else:
            self.send_static_file()

    def _handle_data_route(self, parsed: Any) -> None:
        query_params = parse_qs(parsed.query)
        valid_params: Dict[str, tuple] = {
            "type": (str, False, ["all", "core", "secondary", "calibration"])
        }
        is_valid, error_msg = validate_request_params(query_params, valid_params)
        if not is_valid:
            self.send_error(400, error_msg)
            return
        data_type = query_params.get("type", ["all"])[0]

        if data_type == "core":
            force_refresh = (
                query_params.get("force_refresh", ["false"])[0].lower() == "true"
            )
            DataController.handle_core_data(self, force_refresh)
        elif data_type == "secondary":
            DataController.handle_secondary_data(self)
        elif data_type == "calibration":
            DataController.handle_calibration_data(self)
        else:
            force_refresh = (
                query_params.get("force_refresh", ["false"])[0].lower() == "true"
            )
            if force_refresh:
                client_ip = self.client_address[0]
                if not _force_refresh_limiter.allow(client_ip):
                    cooldown_remaining = _force_refresh_limiter.get_cooldown_remaining(
                        client_ip
                    )
                    log.warning(
                        f"force_refresh 限流: IP={client_ip}, 冷却剩余={cooldown_remaining:.0f}秒"
                    )
                    self._send_json_response(
                        429,
                        {
                            "error": "rate_limited",
                            "message": f"请求过于频繁，请{cooldown_remaining:.0f}秒后再试",
                            "retry_after": int(cooldown_remaining) + 1,
                        },
                    )
                    return
            DataController.handle_data(self, force_refresh)

    def send_static_file(self) -> None:
        try:
            path = self.translate_path(self.path)

            if os.path.isdir(path):
                path = os.path.join(path, "index.html")

            if not os.path.exists(path):
                self.send_error(404, "File not found")
                return

            f = None
            try:
                f = open(path, "rb")
                fs = os.fstat(f.fileno())
                self.send_response(200)

                if path.endswith(".html"):
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                else:
                    self.send_header("Content-Type", self.guess_type(path))

                self.send_header("Content-Length", str(fs[6]))
                self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))

                if path.endswith(".html"):
                    self.send_header(
                        "Cache-Control", "no-cache, no-store, must-revalidate"
                    )
                    self.send_header("Pragma", "no-cache")
                    self.send_header("Expires", "0")
                elif path.endswith((".js", ".css", ".woff2", ".woff", ".ttf")):
                    self.send_header(
                        "Cache-Control", "public, max-age=31536000, immutable"
                    )
                else:
                    self.send_header("Cache-Control", "no-cache")

                self.end_headers()
                self.copyfile(f, self.wfile)
            finally:
                if f:
                    f.close()
        except Exception:
            self.send_error(500, "Internal Server Error")

    def translate_path(self, path: str) -> str:
        import urllib.parse

        path = urllib.parse.unquote(path)
        path = path.split("?", 1)[0]
        path = path.split("#", 1)[0]
        path = path.replace("/assets/", "/assets/")
        if path.endswith("/"):
            path = path + "index.html"
        return os.path.join(DIST_DIR, path.lstrip("/"))

    def send_error(
        self, code: int, message: Optional[str] = None, explain: Optional[str] = None
    ) -> None:
        try:
            self.send_response(code)
        except Exception:
            self.send_response(code, "Error")
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        msg = (
            message.encode("utf-8", errors="replace").decode("utf-8")
            if message
            else self.responses[code][0]
        )
        content = f"<html><body><h1>{code} Error</h1><p>{msg}</p></body></html>"
        self.wfile.write(content.encode("utf-8"))


def reload_caches() -> None:
    """重新初始化缓存实例"""
    try:
        from modules.cache import Cache

        news_cache_size = get_config_value("system.cache.max_size.news", 300)
        quote_cache_size = get_config_value("system.cache.max_size.quote", 2000)
        kline_cache_size = get_config_value("system.cache.max_size.kline", 2000)

        import modules.kline_fetcher
        import modules.news_fetcher
        import modules.quote_fetcher

        modules.news_fetcher.NEWS_CACHE = Cache(max_size=news_cache_size)
        modules.quote_fetcher.QUOTE_CACHE = Cache(max_size=quote_cache_size)
        modules.kline_fetcher.KLINE_CACHE = Cache(max_size=kline_cache_size)

        log.info(
            f"缓存已重新初始化 - 新闻缓存: {news_cache_size}, 行情缓存: {quote_cache_size}, K线缓存: {kline_cache_size}"
        )
    except Exception as e:
        log.error(f"重新初始化缓存失败: {e}")


def stop_background_thread() -> None:
    """优雅停止后台数据预计算线程"""
    global background_thread_running
    background_thread_running = False
    log.info("后台线程停止信号已发送")


def start_server(host: str = "0.0.0.0", port: int = 9004) -> None:
    global background_thread_running
    background_thread_running = True

    config_watcher_interval = get_config_value(
        "system.server.config_watcher_interval", 30.0
    )
    config_manager.start_watcher(interval=config_watcher_interval)
    config_manager.on_change(lambda new_config: reload_params())

    reload_caches()

    server_cache["warmup_complete"] = False
    server_cache["server_start_time"] = time.time()
    log.info("服务器缓存状态已初始化")

    log.info("开始预热缓存数据...")

    def warmup_task() -> None:
        """启动时不运行完整pipeline，只获取快速数据

        完整pipeline由后台定时任务执行，避免启动阻塞
        """
        try:
            from .pipeline_manager import _get_quick_start_data

            quick_data = _get_quick_start_data()
            if quick_data:
                # 标记为快速启动模式
                quick_data["_quick_start_mode"] = True
                server_cache["quick_start_data"] = quick_data
                server_cache["warmup_in_progress"] = True
                server_cache["warmup_complete"] = True
                log.info("快速预热完成，基础数据已缓存")
            else:
                log.warning("快速预热未返回数据")
                server_cache["warmup_complete"] = True  # 仍然标记完成，避免一直等待

        except Exception as e:
            log.error(f"Warmup异常: {e}")
            server_cache["warmup_complete"] = True  # 仍然标记完成

    warmup_thread = threading.Thread(target=warmup_task, daemon=True)
    warmup_thread.start()
    log.info("缓存预热线程已启动，等待warmup完成...")

    # 轮询等待warmup完成（最多3秒），替代固定sleep(15)
    # 优化：从5秒缩短到3秒，get_pipeline_data_lite已支持冷启动秒回
    warmup_deadline = time.time() + 3.0
    while not server_cache.get("warmup_complete", False):
        if time.time() >= warmup_deadline:
            log.warning("warmup未在5秒内完成，继续启动（后台仍在预热）")
            break
        time.sleep(0.5)
    else:
        log.info(f"warmup已完成，耗时约{time.time() - server_cache.get('server_start_time', time.time()):.1f}秒")

    log.info("启动后台数据预计算线程...")
    from .background_tasks import background_data_updater as bg_updater
    from .background_tasks import agent_report_updater as agent_updater

    background_thread = threading.Thread(target=bg_updater, daemon=True)
    background_thread.start()
    log.info("后台数据预计算线程已启动")

    log.info("启动agent_report更新线程...")
    agent_thread = threading.Thread(target=agent_updater, daemon=True)
    agent_thread.start()
    log.info("agent_report更新线程已启动")

    # 启动 Redis 新闻缓存定时存储线程
    try:
        from .scheduler import _news_cache_task

        news_cache_thread = threading.Thread(target=_news_cache_task, daemon=True)
        news_cache_thread.start()
        log.info("Redis新闻缓存定时存储线程已启动")
    except Exception as e:
        log.warning(f"启动Redis新闻缓存线程失败: {e}")

    server = ThreadingHTTPServer((host, port), ServerHandler)
    log.info(f"Server started at http://{host}:{port}")
    server_timeout = get_config_value("system.server.server_timeout", 30)
    server.timeout = server_timeout
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("收到停止信号，正在关闭服务器...")
        stop_background_thread()
        server.shutdown()
        log.info("服务器已关闭")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ashare Server")
    parser.add_argument(
        "--port", type=int, default=9004, help="Server port (default: 9004)"
    )
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Server host (default: 0.0.0.0)"
    )
    args = parser.parse_args()
    start_server(host=args.host, port=args.port)
