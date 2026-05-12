"""新闻数据获取模块（多API合并版）"""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

from .cache import Cache
from .http_client import get_session
from .rate_limiter import RateLimiter
from .retry import circuit_breaker, retry_with_backoff
from .utils import get_config_value, BJT

log = logging.getLogger("ashare.data")

# API状态线程锁
# 锁获取顺序：_news_api_status_lock (第2层) -> _news_storage_lock (第3层)
# 参见 cache_manager.py 中的锁获取顺序规范
_news_api_status_lock = threading.Lock()

# 从配置文件获取熔断器参数
NEWS_CIRCUIT_BREAKER_CONFIG = get_config_value(
    "system.data_fetcher.news_circuit_breaker", {}
)
NEWS_FAILURE_THRESHOLD = NEWS_CIRCUIT_BREAKER_CONFIG.get("failure_threshold", 5)
NEWS_RECOVERY_TIMEOUT = NEWS_CIRCUIT_BREAKER_CONFIG.get("recovery_timeout", 15)

# API状态管理 - 每个API独立的状态
NEWS_API_STATUS: Dict[str, Dict[str, Any]] = {}

# 从配置文件获取缓存大小
news_cache_size: int = get_config_value("system.cache.max_size.news", 500)
NEWS_CACHE = Cache(max_size=news_cache_size)

# 新闻API频率限制器 (使用配置文件)
_news_rate_config = get_config_value("system.rate_limiter.news", {"rate": 20})
NEWS_RATE_LIMITER = RateLimiter(
    max_requests=_news_rate_config.get("rate", 20), time_window=1
)

# 新闻存储持久化
# 锁获取顺序：在 _news_api_status_lock 之后获取
# 参见 cache_manager.py 中的锁获取顺序规范
_news_storage_lock = threading.Lock()
_news_db_conn: Optional[sqlite3.Connection] = None


def _init_news_storage() -> None:
    """初始化新闻存储数据库"""
    enable_persistence = get_config_value(
        "system.data_fetcher.storage.enable_persistence", False
    )
    if not enable_persistence:
        return

    db_path = get_config_value(
        "system.data_fetcher.storage.db_path", "data/news_cache.db"
    )

    try:
        # 确保目录存在
        db_path_obj = Path(db_path)
        db_path_obj.parent.mkdir(parents=True, exist_ok=True)

        # 连接数据库
        global _news_db_conn
        _news_db_conn = sqlite3.connect(str(db_path_obj), check_same_thread=False)

        # 创建表
        cursor = _news_db_conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_cache (
                id TEXT PRIMARY KEY,
                title TEXT,
                digest TEXT,
                ctime INTEGER,
                source TEXT,
                url TEXT,
                quality_score REAL,
                stored_at INTEGER,
                raw_data TEXT
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ctime ON news_cache(ctime)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_source ON news_cache(source)
        """)
        _news_db_conn.commit()

        log.info(f"新闻存储数据库初始化成功: {db_path}")
    except Exception as e:
        log.warning(f"新闻存储数据库初始化失败: {e}")


def _save_news_to_storage(news_list: List[Dict[str, Any]]) -> None:
    """保存新闻到持久化存储"""
    enable_persistence = get_config_value(
        "system.data_fetcher.storage.enable_persistence", False
    )
    if not enable_persistence or not _news_db_conn:
        return

    try:
        with _news_storage_lock:
            cursor = _news_db_conn.cursor()
            stored_at = int(time.time())

            for news in news_list:
                news_id = news.get("id")
                if not news_id:
                    continue

                # 检查是否已存在
                cursor.execute("SELECT id FROM news_cache WHERE id = ?", (news_id,))
                if cursor.fetchone():
                    continue

                # 插入新闻
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO news_cache 
                    (id, title, digest, ctime, source, url, quality_score, stored_at, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        str(news_id),
                        news.get("title", ""),
                        news.get("digest", ""),
                        news.get("ctime", 0),
                        news.get("source", ""),
                        news.get("url", ""),
                        news.get("quality_score", 0.0),
                        stored_at,
                        str(news.get("raw", "")),
                    ),
                )

            _news_db_conn.commit()
            log.debug(f"保存了 {len(news_list)} 条新闻到持久化存储")
    except Exception as e:
        log.warning(f"保存新闻到持久化存储失败: {e}")


def _load_news_from_storage(hours: int = 24) -> List[Dict[str, Any]]:
    """从持久化存储加载新闻"""
    enable_persistence = get_config_value(
        "system.data_fetcher.storage.enable_persistence", False
    )
    if not enable_persistence or not _news_db_conn:
        return []

    try:
        with _news_storage_lock:
            cursor = _news_db_conn.cursor()
            cutoff_time = int(time.time()) - hours * 3600

            cursor.execute(
                """
                SELECT id, title, digest, ctime, source, url, quality_score, raw_data
                FROM news_cache
                WHERE ctime >= ?
                ORDER BY ctime DESC
            """,
                (cutoff_time,),
            )

            rows = cursor.fetchall()
            news_list = []

            for row in rows:
                news = {
                    "id": row[0],
                    "title": row[1],
                    "digest": row[2],
                    "ctime": row[3],
                    "source": row[4],
                    "url": row[5],
                    "quality_score": row[6],
                }
                if row[7]:
                    try:
                        import ast

                        news["raw"] = ast.literal_eval(row[7])
                    except (ValueError, SyntaxError):
                        pass
                news_list.append(news)

            log.debug(f"从持久化存储加载了 {len(news_list)} 条新闻")
            return news_list
    except Exception as e:
        log.warning(f"从持久化存储加载新闻失败: {e}")
        return []


def _cleanup_old_news() -> None:
    """清理旧新闻"""
    enable_persistence = get_config_value(
        "system.data_fetcher.storage.enable_persistence", False
    )
    if not enable_persistence or not _news_db_conn:
        return

    persist_after_hours = get_config_value(
        "system.data_fetcher.storage.persist_after_hours", 6
    )
    cutoff_time = int(time.time()) - (persist_after_hours + 24) * 3600  # 多保留24小时

    try:
        with _news_storage_lock:
            cursor = _news_db_conn.cursor()
            cursor.execute("DELETE FROM news_cache WHERE ctime < ?", (cutoff_time,))
            deleted_count = cursor.rowcount
            _news_db_conn.commit()

            if deleted_count > 0:
                log.info(f"清理了 {deleted_count} 条旧新闻")
    except Exception as e:
        log.warning(f"清理旧新闻失败: {e}")


# 初始化新闻存储
_init_news_storage()

# 从配置文件获取股市相关关键词列表
STOCK_RELATED_KEYWORDS = get_config_value(
    "system.business_constants.stock_related_keywords",
    [
        # 股票相关
        "股票",
        "股市",
        "股价",
        "涨停",
        "跌停",
        "涨停板",
        "跌停板",
        "开盘",
        "收盘",
        "成交量",
        "成交额",
        "换手率",
        "市盈率",
        "市净率",
        "K线",
        "均线",
        "MACD",
        "KDJ",
        "量比",
        "委比",
        "内外盘",
        "盘口",
        "筹码",
        "庄家",
        "主力",
        "游资",
        "机构",
        "散户",
        "追涨",
        "杀跌",
        "抄底",
        "逃顶",
        "套牢",
        "解套",
        "获利了结",
        "割肉",
        "建仓",
        "加仓",
        "减仓",
        "清仓",
        # 指数相关
        "上证指数",
        "深证成指",
        "创业板指",
        "沪深300",
        "中证500",
        "科创50",
        "中小板指",
        "指数",
        "大盘",
        "盘面",
        "走势",
        "行情",
        "反弹",
        "回调",
        "震荡",
        "上涨",
        "下跌",
        "横盘",
        "突破",
        "跌破",
        "支撑位",
        "阻力位",
        "压力位",
        # 行业相关
        "行业",
        "板块",
        "概念",
        "题材",
        "热点",
        "领涨",
        "领跌",
        "龙头",
        "妖股",
        "白马股",
        "蓝筹股",
        "成长股",
        "价值股",
        "周期股",
        "科技股",
        "医药股",
        "消费股",
        "新能源",
        "半导体",
        "芯片",
        "5G",
        "人工智能",
        "大数据",
        "云计算",
        "互联网",
        "金融",
        "银行",
        "保险",
        "券商",
        "地产",
        "汽车",
        "医药",
        "医疗",
        "农业",
        "军工",
        "有色",
        "煤炭",
        "钢铁",
        "化工",
        "建材",
        "机械",
        "电力",
        "环保",
        # 政策相关
        "政策",
        "利好",
        "利空",
        "监管",
        "证监会",
        "央行",
        "银保监会",
        "财政部",
        "发改委",
        "国务院",
        "宏观",
        "经济",
        "GDP",
        "CPI",
        "PPI",
        "利率",
        "汇率",
        "通胀",
        "通缩",
        "货币",
        "财政",
        "减税",
        "降费",
        "补贴",
        "扶持",
        "调控",
        "改革",
        "开放",
        # 公司相关
        "公司",
        "企业",
        "上市公司",
        "财报",
        "业绩",
        "利润",
        "营收",
        "亏损",
        "盈利",
        "增长",
        "下降",
        "公告",
        "停牌",
        "复牌",
        "重组",
        "并购",
        "收购",
        "股权转让",
        "增发",
        "配股",
        "分红",
        "送股",
        "转增",
        "回购",
        "增持",
        "减持",
        "解禁",
        "质押",
        "违约",
        "破产",
        # 交易相关
        "交易",
        "买卖",
        "成交",
        "委托",
        "撤单",
        "竞价",
        "集合竞价",
        "连续竞价",
        "涨停价",
        "跌停价",
        "开盘价",
        "收盘价",
        "最高价",
        "最低价",
        "均价",
        "现价",
        "昨收",
        # 市场相关
        "市场",
        "投资者",
        "散户",
        "机构",
        "主力",
        "庄家",
        "游资",
        "外资",
        "北向资金",
        "南向资金",
        "聪明资金",
        "增量资金",
        "存量资金",
        "热钱",
        "避险资金",
        "抄底资金",
        # 技术相关
        "技术分析",
        "基本面",
        "技术面",
        "消息面",
        "资金面",
        "量价关系",
        "趋势",
        "形态",
        "支撑",
        "阻力",
        "突破",
        "回调",
        "反弹",
        "反转",
        "整理",
        "洗盘",
        "出货",
        "建仓",
        # 其他相关
        "分析师",
        "研报",
        "评级",
        "目标价",
        "推荐",
        "买入",
        "卖出",
        "持有",
        "观望",
        "风险",
        "机会",
        "策略",
        "操作",
        "建议",
        "预测",
        "展望",
        "分析",
        "解读",
        "评论",
    ],
)


@retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=5.0)
def _retry_get(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 10,
) -> requests.Response:
    """带重试机制的GET请求

    Args:
        url: 请求URL
        params: 请求参数
        headers: 请求头
        timeout: 超时时间（秒）

    Returns:
        requests.Response: 响应对象

    Raises:
        requests.exceptions.RequestException: 请求异常
    """
    session = get_session()
    try:
        r = session.get(url, params=params, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r
    except requests.exceptions.Timeout as e:
        log.warning(f"请求超时: {url} - {e}")
        raise
    except requests.exceptions.SSLError as e:
        log.warning(f"SSL错误（将快速重试）: {url} - {e}")
        raise
    except requests.exceptions.RequestException as e:
        log.warning(f"请求失败: {url} - {e}")
        raise


# ========== API配置定义 ==========

# 从配置文件获取新闻API配置
NEWS_API_CONFIGS = []
news_api_configs = get_config_value("system.external_api.news_api_configs", {})
for api_name, api_config in news_api_configs.items():
    NEWS_API_CONFIGS.append(api_config)

# 如果配置文件中没有配置，使用默认配置
if not NEWS_API_CONFIGS:
    # 同花顺新闻API配置（主源）
    THS_NEWS_CONFIG = {
        "name": "ths",
        "url": get_config_value(
            "system.external_api.news_url",
            "https://news.10jqka.com.cn/tapp/news/push/stock/",
        ),
        "headers": {
            "Referer": "https://news.10jqka.com.cn",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
        },
        "timeout": 10,
        "enabled": True,
    }

    # 新浪财经API配置（备用源）
    SINA_NEWS_CONFIG = {
        "name": "sina",
        "url": get_config_value(
            "system.external_api.news_backup_urls",
            ["https://feed.mix.sina.com.cn/api/roll/get"],
        )[0]
        if get_config_value(
            "system.external_api.news_backup_urls",
            ["https://feed.mix.sina.com.cn/api/roll/get"],
        )
        else "https://feed.mix.sina.com.cn/api/roll/get",
        "headers": {
            "Referer": "https://finance.sina.com.cn",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/javascript, */*",
        },
        "timeout": 10,
        "enabled": True,
    }

    # 东方财富7x24快讯API配置（备用源）
    EM_NEWS_CONFIG = {
        "name": "eastmoney",
        "url": get_config_value(
            "system.external_api.news_backup_urls",
            [
                "https://feed.mix.sina.com.cn/api/roll/get",
                "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns",
            ],
        )[1]
        if len(
            get_config_value(
                "system.external_api.news_backup_urls",
                [
                    "https://feed.mix.sina.com.cn/api/roll/get",
                    "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns",
                ],
            )
        )
        > 1
        else "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns",
        "headers": {
            "Referer": "https://kuaixun.eastmoney.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/javascript, */*",
        },
        "timeout": 10,
        "enabled": True,
    }

    # 财联社快讯API配置（备用源）- 使用akshare获取7x24快讯
    CLS_FLASH_NEWS_CONFIG = {
        "name": "cls_flash",
        "url": "akshare_cls_telegraph",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        },
        "timeout": 30,
        "enabled": True,
    }

    NEWS_API_CONFIGS = [
        THS_NEWS_CONFIG,
        SINA_NEWS_CONFIG,
        EM_NEWS_CONFIG,
        CLS_FLASH_NEWS_CONFIG,
    ]

# 同花顺标签定义 - 优化：只获取all标签，避免重复
# important/opportunity/a_stock 都是 all 的子集，遍历会导致大量重复
THS_TAGS = {
    "all": "",
}


def _init_api_status() -> None:
    """初始化API状态 (线程安全)"""
    with _news_api_status_lock:
        global NEWS_API_STATUS
        for config in NEWS_API_CONFIGS:
            if config["name"] not in NEWS_API_STATUS:
                NEWS_API_STATUS[config["name"]] = {
                    "available": True,
                    "fail_count": 0,
                    "last_fail_time": 0,
                    "recovery_time": 0,
                    "consecutive_failures": 0,
                    "status_updated_at": time.time(),
                    "metrics": {
                        "response_times": [],
                        "success_count": 0,
                        "total_count": 0,
                        "last_success": None,
                        "last_failure": None,
                        "news_count": 0,
                        "duplicate_count": 0,
                        "consecutive_failures": 0,
                        "avg_response_time": 0.0,
                        "success_rate": 0.0,
                    },
                }


def _is_api_available(api_name: str) -> bool:
    """检查API是否可用"""
    if api_name not in NEWS_API_STATUS:
        return True

    status = NEWS_API_STATUS[api_name]
    if status["available"]:
        return True

    # 检查是否需要恢复
    current_time = time.time()
    if current_time >= status.get("recovery_time", 0):
        # 智能恢复策略：基于历史性能数据
        if "metrics" in status:
            metrics = status["metrics"]
            total_count = metrics["total_count"]
            success_count = metrics["success_count"]

            # 计算成功率
            success_rate = success_count / total_count if total_count > 0 else 0

            # 检查最后一次失败时间
            last_failure = metrics["last_failure"]
            if last_failure:
                failure_age = current_time - last_failure
            else:
                failure_age = float("inf")

            # 智能恢复决策
            if (
                success_rate >= 0.7 or failure_age > 1800
            ):  # 成功率≥70%或失败已超过30分钟
                log.info(
                    f"智能恢复新闻API: {api_name} - 历史成功率: {success_rate:.2f}, 失败时间: {failure_age:.0f}s"
                )
                status["available"] = True
                status["fail_count"] = 0
                status["consecutive_failures"] = 0
                status["status_updated_at"] = current_time
                return True
            else:
                log.debug(
                    f"新闻API暂不恢复: {api_name} - 历史成功率: {success_rate:.2f}, 失败时间: {failure_age:.0f}s"
                )
                return False
        else:
            # 没有性能数据，使用默认恢复策略
            log.info(f"尝试恢复新闻API: {api_name}")
            status["available"] = True
            status["fail_count"] = 0
            status["consecutive_failures"] = 0
            status["status_updated_at"] = current_time
            return True

    return False


def _mark_api_failed(api_name: str) -> None:
    """标记API为失败状态 (线程安全)"""
    with _news_api_status_lock:
        current_time = time.time()
        if api_name not in NEWS_API_STATUS:
            NEWS_API_STATUS[api_name] = {
                "available": False,
                "fail_count": 1,
                "last_fail_time": current_time,
                "recovery_time": current_time + NEWS_RECOVERY_TIMEOUT,
                "consecutive_failures": 1,
                "status_updated_at": current_time,
                "metrics": {
                    "response_times": [],
                    "success_count": 0,
                    "total_count": 0,
                    "last_success": None,
                    "last_failure": current_time,
                    "news_count": 0,
                    "duplicate_count": 0,
                    "consecutive_failures": 1,
                    "avg_response_time": 0.0,
                    "success_rate": 0.0,
                },
            }
        else:
            NEWS_API_STATUS[api_name]["fail_count"] += 1
            NEWS_API_STATUS[api_name]["consecutive_failures"] += 1
            NEWS_API_STATUS[api_name]["last_fail_time"] = current_time
            NEWS_API_STATUS[api_name]["status_updated_at"] = current_time
            # 更新metrics
            if "metrics" in NEWS_API_STATUS[api_name]:
                metrics = NEWS_API_STATUS[api_name]["metrics"]
                metrics["total_count"] += 1
                metrics["last_failure"] = current_time
                metrics["consecutive_failures"] += 1
                # 计算平均响应时间和成功率
                if metrics["response_times"]:
                    metrics["avg_response_time"] = sum(metrics["response_times"]) / len(
                        metrics["response_times"]
                    )
                metrics["success_rate"] = (
                    metrics["success_count"] / metrics["total_count"]
                    if metrics["total_count"] > 0
                    else 0
                )

            # 达到阈值后标记为不可用
            if NEWS_API_STATUS[api_name]["fail_count"] >= NEWS_FAILURE_THRESHOLD:
                NEWS_API_STATUS[api_name]["available"] = False
                NEWS_API_STATUS[api_name]["recovery_time"] = (
                    current_time + NEWS_RECOVERY_TIMEOUT
                )
                log.warning(
                    f"新闻API {api_name} 达到失败阈值({NEWS_FAILURE_THRESHOLD}次)，暂时禁用，{NEWS_RECOVERY_TIMEOUT}秒后尝试恢复"
                )


def _validate_news_data(news_item: Dict[str, Any]) -> bool:
    """验证新闻数据的质量"""
    # 检查关键字段是否存在
    required_fields = ["title", "ctime"]
    for field in required_fields:
        if field not in news_item:
            return False

    # 检查标题是否为空
    if not news_item.get("title", "").strip():
        return False

    # 检查时间是否有效
    ctime = news_item.get("ctime")
    if ctime is None:
        return False

    # 检查时间是否在合理范围内（最近7天）
    current_time = time.time()
    seven_days_ago = current_time - 7 * 24 * 3600
    if not isinstance(ctime, (int, float)) or ctime < seven_days_ago:
        return False

    return True


def _parse_ths_response(data: Any) -> List[Dict[str, Any]]:
    """解析同花顺新闻响应"""
    data_obj = data.get("data")
    if not isinstance(data_obj, dict):
        log.warning(f"同花顺data.data不是字典类型: {type(data_obj).__name__}")
        return []

    news_list = data_obj.get("list", [])
    if not isinstance(news_list, list):
        log.warning(f"同花顺data.data.list不是列表类型: {type(news_list).__name__}")
        return []

    # 标准化新闻格式
    standardized = []
    valid_count = 0
    invalid_count = 0

    for item in news_list:
        if not isinstance(item, dict):
            invalid_count += 1
            continue

        # 提取时间
        time_str = item.get("time") or item.get("ctime") or item.get("rtime")
        ctime: Optional[int] = None
        if time_str:
            if isinstance(time_str, str) and time_str.isdigit():
                ctime = int(time_str)
            elif isinstance(time_str, (int, float)):
                ctime = int(time_str)
            elif isinstance(time_str, str):
                # 尝试解析日期字符串
                try:
                    from datetime import datetime

                    # 尝试不同的日期格式
                    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"]:
                        try:
                            dt = datetime.strptime(time_str, fmt)
                            ctime = int(dt.timestamp())
                            break
                        except ValueError:
                            continue
                except Exception as e:
                    log.warning(f"解析新闻时间格式失败: {e}")

        news_item = {
            "id": item.get("id") or item.get("news_id"),
            "title": item.get("title", ""),
            "digest": item.get("digest", item.get("content", "")),
            "ctime": ctime,
            "source": "ths",
            "url": item.get("url") or item.get("news_url"),
            "stock": item.get("stock", []),  # 提取关联股票代码，供热门股票分析使用
            "raw": item,
        }

        # 验证数据质量
        if _validate_news_data(news_item):
            standardized.append(news_item)
            valid_count += 1
        else:
            invalid_count += 1

    log.info(f"同花顺新闻解析完成: 有效{valid_count}条，无效{invalid_count}条")
    return standardized


def _parse_sina_response(data: Any) -> List[Dict[str, Any]]:
    """解析新浪财经7x24快讯响应"""
    if not isinstance(data, dict):
        log.warning(f"新浪响应不是字典类型: {type(data).__name__}")
        return []

    result = data.get("result", {})
    if not isinstance(result, dict):
        log.warning("新浪响应result不是字典类型")
        return []

    data_list = result.get("data", [])
    if not isinstance(data_list, list):
        log.warning("新浪响应data不是列表类型")
        return []

    standardized = []
    valid_count = 0
    invalid_count = 0
    for item in data_list:
        if not isinstance(item, dict):
            invalid_count += 1
            continue

        time_str = item.get("ctime") or item.get("time") or item.get("inputtime")
        ctime: Optional[int] = None
        if time_str:
            if isinstance(time_str, str):
                if time_str.isdigit():
                    ctime = int(time_str)
            elif isinstance(time_str, (int, float)):
                ctime = int(time_str)

        title = (
            item.get("title", "") or item.get("summary", "") or item.get("content", "")
        )
        if len(title) > 100:
            title = title[:100] + "..."

        news_item = {
            "id": item.get("id") or item.get("docid"),
            "title": title,
            "digest": item.get("summary", item.get("content", "")),
            "ctime": ctime,
            "source": "sina",
            "url": item.get("url") or item.get("wapurl") or item.get("href"),
            "raw": item,
        }

        # 验证数据质量
        if _validate_news_data(news_item):
            standardized.append(news_item)
            valid_count += 1
        else:
            invalid_count += 1

    log.info(f"新浪新闻解析完成: 有效{valid_count}条，无效{invalid_count}条")

    if standardized:
        log.info(f"新浪解析成功: {len(standardized)}条新闻")
    return standardized


def _parse_eastmoney_response(data: Any) -> List[Dict[str, Any]]:
    """解析东方财富7x24快讯响应

    实际响应格式:
    {"code": 0, "message": "", "data": {"page_index": 1, "list": [...], "totle_hits": N, "page_size": 20}}
    list item: {"summary", "code", "np_dst", "realSort", "showTime", "uniqueUrl", "title", "mediaName", "url"}
    """
    log.debug(f"东方财富响应keys: {list(data.keys())}")

    # data.data.list
    data_list = None
    if "data" in data and isinstance(data.get("data"), dict):
        data_list = data["data"].get("list", [])
    elif "data" in data and isinstance(data["data"], list):
        data_list = data["data"]

    if not data_list:
        log.warning("东方财富响应中未找到数据列表")
        return []

    standardized = []
    for item in data_list:
        if not isinstance(item, dict):
            continue

        # 时间字段: showTime = "2026-04-04 23:03:25"
        time_str = item.get("showTime") or item.get("showtime") or item.get("ctime")
        ctime = None
        if time_str:
            if isinstance(time_str, str) and time_str.isdigit():
                ctime = int(time_str)
            elif isinstance(time_str, (int, float)):
                ctime = int(time_str)
            elif isinstance(time_str, str):
                try:
                    from datetime import datetime

                    dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                    ctime = int(dt.timestamp())
                except ValueError:
                    pass

        title = item.get("title", "") or item.get("summary", "")
        if len(title) > 100:
            title = title[:100] + "..."

        standardized.append(
            {
                "id": item.get("code") or item.get("news_id") or item.get("id"),
                "title": title,
                "digest": item.get("summary", ""),
                "ctime": ctime,
                "source": "eastmoney",
                "url": item.get("uniqueUrl") or item.get("url"),
                "raw": item,
            }
        )

    if standardized:
        log.info(f"东方财富解析成功: {len(standardized)}条新闻")
    return standardized


def _parse_cls_flash_response(data_list: Any) -> List[Dict[str, Any]]:
    """解析财联社快讯响应

    财联社API /nodeapi/telegraphList 返回格式:
    包含 id, title, content, ctime, level, shareurl, brief 等字段
    URL格式: https://www.cls.cn/detail/{id}
    """
    standardized = []
    valid_count = 0
    invalid_count = 0

    if not isinstance(data_list, list):
        log.warning(f"财联社快讯响应不是列表类型: {type(data_list).__name__}")
        return []

    for item in data_list:
        if not isinstance(item, dict):
            invalid_count += 1
            continue

        ctime: Optional[int] = None

        ctime_val = item.get("ctime")
        if ctime_val:
            try:
                ctime = int(ctime_val)
            except (ValueError, TypeError):
                pass

        if not ctime:
            time_str = (
                item.get("时间")
                or item.get("datetime")
                or item.get("time")
                or item.get("date")
                or item.get("发布时间")
            )
            if time_str:
                if isinstance(time_str, str):
                    if time_str.isdigit():
                        ctime = int(time_str)
                    else:
                        try:
                            from datetime import datetime

                            for fmt in [
                                "%Y-%m-%d %H:%M:%S",
                                "%Y-%m-%d %H:%M",
                                "%Y-%m-%d",
                            ]:
                                try:
                                    dt = datetime.strptime(time_str, fmt)
                                    ctime = int(dt.timestamp())
                                    break
                                except ValueError:
                                    continue
                        except Exception as e:
                            log.warning(f"解析财联社快讯时间格式失败: {e}")
                elif isinstance(time_str, (int, float)):
                    ctime = int(time_str)

        if not ctime:
            ctime = int(time.time())

        title = (
            item.get("title")
            or item.get("内容", "")
            or item.get("content", "")
            or item.get("summary", "")
        )
        if len(title) > 100:
            title = title[:100] + "..."

        news_id = item.get("id") or item.get("news_id")
        url: str = ""
        if news_id:
            url = f"https://www.cls.cn/detail/{news_id}"
        elif item.get("shareurl"):
            url = str(item.get("shareurl", ""))
        elif item.get("url"):
            url = str(item.get("url", ""))

        news_item = {
            "id": news_id or str(ctime),
            "title": title,
            "digest": item.get("brief") or item.get("content") or item.get("内容", ""),
            "ctime": ctime,
            "source": "cls_flash",
            "url": url,
            "raw": item,
        }

        if _validate_news_data(news_item):
            standardized.append(news_item)
            valid_count += 1
        else:
            invalid_count += 1

    log.info(f"财联社快讯解析完成: 有效{valid_count}条，无效{invalid_count}条")
    return standardized


# API解析器映射
API_PARSERS: Dict[str, Callable[[Any], List[Dict[str, Any]]]] = {
    "ths": _parse_ths_response,
    "sina": _parse_sina_response,
    "eastmoney": _parse_eastmoney_response,
    "cls_flash": _parse_cls_flash_response,
}


def _update_api_metrics(
    api_name: str, response_time: float, news_count: int, success: bool
) -> None:
    """更新API请求metrics（公共方法，避免重复代码）

    Args:
        api_name: API名称
        response_time: 响应时间(秒)
        news_count: 获取到的新闻数量
        success: 是否成功
    """
    if api_name not in NEWS_API_STATUS:
        return
    if "metrics" not in NEWS_API_STATUS[api_name]:
        return
    metrics = NEWS_API_STATUS[api_name]["metrics"]
    metrics["response_times"].append(response_time)
    if len(metrics["response_times"]) > 100:
        metrics["response_times"] = metrics["response_times"][-100:]
    metrics["total_count"] += 1
    if success:
        metrics["success_count"] += 1
        metrics["last_success"] = time.time()
        metrics["last_failure"] = None
        metrics["consecutive_failures"] = 0
        metrics["news_count"] += news_count
    else:
        metrics["last_failure"] = time.time()
        metrics["consecutive_failures"] = metrics.get("consecutive_failures", 0) + 1
    if metrics["total_count"] > 0:
        metrics["avg_response_time"] = sum(metrics["response_times"]) / len(
            metrics["response_times"]
        )
        metrics["success_rate"] = metrics["success_count"] / metrics["total_count"]


def _reset_api_success(api_name: str) -> None:
    """重置API成功状态"""
    if api_name in NEWS_API_STATUS:
        NEWS_API_STATUS[api_name]["fail_count"] = 0
        NEWS_API_STATUS[api_name]["consecutive_failures"] = 0
        NEWS_API_STATUS[api_name]["status_updated_at"] = time.time()


def _fetch_news_from_api(
    api_config: Dict[str, Any], tag_value: str = "", page: int = 1
) -> List[Dict[str, Any]]:
    """从指定API获取新闻

    Args:
        api_config: API配置
        tag_value: 标签值
        page: 页码

    Returns:
        标准化的新闻列表
    """
    api_name = api_config["name"]

    # 检查API是否可用
    if not _is_api_available(api_name):
        log.debug(f"新闻API {api_name} 当前不可用，跳过")
        return []

    # 财联社快讯API直接调用财联社接口获取7x24快讯
    if api_name == "cls_flash":
        try:
            NEWS_RATE_LIMITER.wait_if_needed(api_name)

            start_time = time.time()
            api_url = api_config.get("url", "https://www.cls.cn/nodeapi/telegraphList")
            log.info(f"请求新闻API [{api_name}]: {api_url}")

            headers = api_config.get("headers", {})
            timeout = api_config.get("timeout", 30)

            r = _retry_get(api_url, headers=headers, timeout=timeout)
            response_time = time.time() - start_time

            data = r.json()
            roll_data = data.get("data", {}).get("roll_data", [])
            if not roll_data:
                log.warning("财联社快讯返回空数据")
                _update_api_metrics(api_name, response_time, 0, False)
                return []

            news_list = _parse_cls_flash_response(roll_data)

            _reset_api_success(api_name)
            _update_api_metrics(api_name, response_time, len(news_list), True)

            log.info(
                f"从 [{api_name}] 获取到 {len(news_list)} 条新闻，响应时间: {response_time:.2f}s"
            )

            return news_list

        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            _update_api_metrics(api_name, response_time, 0, False)
            _mark_api_failed(api_name)
            log.warning(f"财联社快讯请求失败: {e}")
            return []
        except ValueError as e:
            response_time = time.time() - start_time
            _update_api_metrics(api_name, response_time, 0, False)
            _mark_api_failed(api_name)
            log.warning(f"财联社快讯解析失败: {e}")
            return []
        except Exception as e:
            response_time = time.time() - start_time
            _update_api_metrics(api_name, response_time, 0, False)
            log.warning(f"财联社快讯获取失败: {e}")
            _mark_api_failed(api_name)
            return []

    # 构建请求参数 - 根据不同API构建
    if api_name == "ths":
        params = {
            "page": page,
            "tag": tag_value,
            "track": "website",
            "pagesize": 20,
            "_": int(time.time() * 1000),
        }
    elif api_name == "sina":
        params = {
            "pageid": 153,
            "lid": 2516,  # A股7x24快讯
            "num": 20,
            "page": page,
            "_": int(time.time() * 1000),
        }
    elif api_name == "eastmoney":
        params = {
            "client": "web",
            "biz": "web_724",
            "column": "350",
            "page_size": 20,
            "page_index": page,
            "req_trace": str(int(time.time() * 1000)),
        }
    else:
        params = {"page": page}

    try:
        # 应用频率限制，避免请求过快被API限流
        NEWS_RATE_LIMITER.wait_if_needed(api_name)

        start_time = time.time()
        log.info(f"请求新闻API [{api_name}]: {api_config['url']}")
        r = _retry_get(
            api_config["url"],
            params=params,
            headers=api_config["headers"],
            timeout=api_config["timeout"],
        )
        response_time = time.time() - start_time

        data = r.json()

        # 使用对应的解析器
        parser = API_PARSERS.get(api_name)
        if parser is not None:
            news_list = parser(data)
        else:
            log.warning(f"未找到API {api_name} 的解析器")
            news_list = []

        # 成功获取，重置失败计数
        _reset_api_success(api_name)
        _update_api_metrics(api_name, response_time, len(news_list), True)

        log.info(
            f"从 [{api_name}] 获取到 {len(news_list)} 条新闻，响应时间: {response_time:.2f}s"
        )

        return news_list

    except requests.exceptions.RequestException as e:
        response_time = time.time() - start_time
        _update_api_metrics(api_name, response_time, 0, False)

        is_ssl_error = isinstance(e, (
            requests.exceptions.SSLError,
            requests.exceptions.ConnectionError,
        ))

        if is_ssl_error:
            log.warning(
                f"新闻API [{api_name}] SSL/连接错误: {e} (响应时间: {response_time:.2f}s)，标记为临时不可用"
            )
            _mark_api_failed(api_name)
        else:
            _mark_api_failed(api_name)
            fail_count = NEWS_API_STATUS.get(api_name, {}).get("fail_count", 0)
            consecutive_failures = NEWS_API_STATUS.get(api_name, {}).get(
                "consecutive_failures", 0
            )
            if fail_count <= 1 or fail_count % 5 == 0:
                log.warning(
                    f"新闻API [{api_name}] 请求失败 ({fail_count}次, 连续{consecutive_failures}次): {e} (响应时间: {response_time:.2f}s)"
                )
        return []
    except ValueError as e:
        response_time = time.time() - start_time
        _update_api_metrics(api_name, response_time, 0, False)
        _mark_api_failed(api_name)
        fail_count = NEWS_API_STATUS.get(api_name, {}).get("fail_count", 0)
        consecutive_failures = NEWS_API_STATUS.get(api_name, {}).get(
            "consecutive_failures", 0
        )
        if fail_count <= 1 or fail_count % 5 == 0:
            log.warning(
                f"新闻API [{api_name}] 解析失败 ({fail_count}次, 连续{consecutive_failures}次): {e} (响应时间: {response_time:.2f}s)"
            )
        return []
    except Exception as e:
        response_time = time.time() - start_time
        _update_api_metrics(api_name, response_time, 0, False)
        _mark_api_failed(api_name)
        fail_count = NEWS_API_STATUS.get(api_name, {}).get("fail_count", 0)
        consecutive_failures = NEWS_API_STATUS.get(api_name, {}).get(
            "consecutive_failures", 0
        )
        if fail_count <= 1 or fail_count % 5 == 0:
            log.warning(
                f"新闻API [{api_name}] 未知错误 ({fail_count}次, 连续{consecutive_failures}次): {e} (响应时间: {response_time:.2f}s)"
            )
        return []


def _fetch_all_news_from_single_api(
    api_config: Dict[str, Any],
    max_pages: int = 5,
    twenty_four_hours_ago: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """从单个API获取所有新闻（最多max_pages页，24小时内）

    Args:
        api_config: API配置
        max_pages: 最大页数（动态API会覆盖此值）
        twenty_four_hours_ago: 24小时前的时间

    Returns:
        新闻列表
    """
    from datetime import datetime

    if twenty_four_hours_ago is None:
        twenty_four_hours_ago = datetime.now(BJT) - __import__("datetime").timedelta(
            hours=24
        )

    api_name = api_config["name"]
    all_items: List[Dict[str, Any]] = []

    # 使用动态API页数（如果启用）
    dynamic_max_pages = get_dynamic_api_pages(api_config)
    actual_max_pages = min(dynamic_max_pages, max_pages)

    if dynamic_max_pages != max_pages:
        log.debug(
            f"API [{api_name}] 使用动态页数: {dynamic_max_pages} (配置: {max_pages})"
        )

    # 同花顺需要遍历标签，其他API直接获取
    if api_name == "ths":
        tags_to_fetch = THS_TAGS
    else:
        tags_to_fetch = {"default": ""}

    for tag_name, tag_value in tags_to_fetch.items():
        page = 1
        ssl_retry_count = 0
        max_ssl_retries = 2

        while page <= actual_max_pages:
            try:
                items = _fetch_news_from_api(api_config, tag_value, page)

                if not items and ssl_retry_count < max_ssl_retries:
                    ssl_retry_count += 1
                    log.info(f"[{api_name}] {tag_name} 第{page}页返回空，SSL重试 {ssl_retry_count}/{max_ssl_retries}")
                    time.sleep(1)
                    continue

                if not items:
                    break

                ssl_retry_count = 0
                for item in items:
                    all_items.append(item)

                page += 1
                time.sleep(0.1)

            except Exception as e:
                log.warning(f"获取 [{api_name}] {tag_name} 新闻页面 {page} 失败: {e}")
                break

    # 收集完后统一过滤24小时数据
    filtered_items = []
    for item in all_items:
        ctime = item.get("ctime")
        if ctime:
            from datetime import datetime

            news_time = datetime.fromtimestamp(ctime, tz=BJT)
            if news_time >= twenty_four_hours_ago:
                filtered_items.append(item)
        else:
            # 无时间戳的保留（可能是最新新闻）
            filtered_items.append(item)

    log.info(f"[{api_name}] 获取 {len(all_items)} 条，24h内 {len(filtered_items)} 条")
    return filtered_items


def _merge_news_from_multiple_apis(
    all_news: List[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """合并多个 API 的新闻数据并去重

    去重策略:
    1. ID 去重（精确匹配）
    2. 标题去重（精确匹配，经过标准化处理）
    3. 标题相似度去重（>85% 相似度视为重复，使用 Jaccard 相似度 + 编辑距离）
    4. 时间窗口去重（5 分钟内的相似标题视为重复）

    Args:
        all_news: 各 API 的新闻列表列表

    Returns:
        合并去重后的新闻列表
    """

    def _normalize_title(title: str) -> str:
        """标准化标题，去除标点符号、空格等干扰因素"""
        import re

        # 转为小写
        title = title.lower()
        # 去除标点符号和特殊字符
        title = re.sub(r"[^\w\u4e00-\u9fa5]", "", title)
        # 去除多余空格
        title = title.strip()
        return title

    def _title_similarity_jaccard(t1: str, t2: str) -> float:
        """计算两个标题的 Jaccard 相似度（基于字符集合）"""
        if not t1 or not t2:
            return 0.0
        set1 = set(t1)
        set2 = set(t2)
        intersection = set1 & set2
        union = set1 | set2
        return len(intersection) / len(union) if union else 0.0

    def _title_similarity_edit_distance(t1: str, t2: str) -> float:
        """计算两个标题的编辑距离相似度"""
        if not t1 or not t2:
            return 0.0
        if len(t1) == 0 or len(t2) == 0:
            return 0.0

        # 创建距离矩阵
        m, n = len(t1), len(t2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        # 初始化
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        # 计算编辑距离
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if t1[i - 1] == t2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])

        # 转换为相似度（归一化到 0-1）
        max_len = max(m, n)
        return 1.0 - dp[m][n] / max_len

    def _is_duplicate_title(new_title: str, seen_title: str) -> bool:
        """综合判断两个标题是否重复"""
        # 标准化标题
        norm_new = _normalize_title(new_title)
        norm_seen = _normalize_title(seen_title)

        # 精确匹配
        if norm_new == norm_seen:
            return True

        # 太短的标题不做模糊匹配
        if len(norm_new) <= 4 or len(norm_seen) <= 4:
            return False

        # 计算 Jaccard 相似度
        jaccard_sim = _title_similarity_jaccard(norm_new, norm_seen)

        # 计算编辑距离相似度
        edit_sim = _title_similarity_edit_distance(norm_new, norm_seen)

        # 综合相似度（加权平均）
        combined_sim = 0.6 * jaccard_sim + 0.4 * edit_sim

        # 相似度超过 85% 视为重复
        return combined_sim > 0.85

    seen_ids: set[str] = set()
    seen_titles: set[str] = set()
    seen_normalized: List[Tuple[str, set, int]] = []  # (normalized_title, char_set, len) 用于快速预筛
    merged: List[Dict[str, Any]] = []

    for api_news in all_news:
        for item in api_news:
            # 使用 ID 去重
            item_id = item.get("id")
            if item_id and item_id in seen_ids:
                continue

            # 使用标题去重（精确匹配）
            title = item.get("title", "").strip()
            if title and title in seen_titles:
                continue

            # 模糊标题去重 — 优化：Jaccard预筛 + 编辑距离仅对候选对
            is_duplicate = False
            if title and len(title) > 4:
                norm_title = _normalize_title(title)
                title_chars = set(norm_title)
                title_len = len(norm_title)

                for seen_norm, seen_chars, seen_len in seen_normalized:
                    # 快速长度过滤：长度差异超过40%直接跳过
                    if seen_len > 0 and title_len > 0:
                        len_ratio = min(title_len, seen_len) / max(title_len, seen_len)
                        if len_ratio < 0.6:
                            continue

                    # Jaccard 预筛：字符集合快速比较，低于阈值直接跳过
                    if title_chars and seen_chars:
                        intersection = len(title_chars & seen_chars)
                        union = len(title_chars | seen_chars)
                        jaccard = intersection / union if union else 0
                        if jaccard < 0.5:  # Jaccard < 0.5 不可能是85%相似
                            continue

                    # 候选对：用 normalized 标题直接做编辑距离
                    edit_sim = _title_similarity_edit_distance(norm_title, seen_norm)
                    if edit_sim > 0.85:  # 编辑距离相似度 > 85%
                        is_duplicate = True
                        break

            if is_duplicate:
                continue

            if item_id:
                seen_ids.add(item_id)
            if title:
                seen_titles.add(title)
                norm_t = _normalize_title(title)
                seen_normalized.append((norm_t, set(norm_t), len(norm_t)))

            merged.append(item)

    return merged


def _sort_news_by_time(news_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """按时间排序新闻，最新的在前

    Args:
        news_list: 新闻列表

    Returns:
        排序后的新闻列表
    """

    def get_time(item: Dict[str, Any]) -> float:
        ctime = item.get("ctime")
        if ctime and isinstance(ctime, (int, float)):
            return float(ctime)
        return 0.0

    return sorted(news_list, key=get_time, reverse=True)


def _is_stock_related_news(news_item: Dict[str, Any]) -> bool:
    """检查新闻是否与股市相关

    Args:
        news_item: 新闻项字典

    Returns:
        bool: 是否与股市相关
    """
    import re

    # 提取新闻标题和摘要
    title = news_item.get("title", "").lower()
    digest = news_item.get("digest", "").lower()
    news_item.get("source", "")

    # 检查是否包含股票代码
    # 匹配A股股票代码格式：6位数字，或带前缀如sh600000、sz000000
    stock_code_pattern = r"(sh|sz)?\d{6}"
    if re.search(stock_code_pattern, title) or re.search(stock_code_pattern, digest):
        return True

    # 检查是否包含股票相关关键词
    for keyword in STOCK_RELATED_KEYWORDS:
        if keyword.lower() in title or keyword.lower() in digest:
            # 进一步检查是否包含具体股票名称或代码相关信息
            # 确保关键词匹配不是泛泛而谈的市场信息
            # 检查是否有具体的股票提及
            if any(
                stock_word in title or stock_word in digest
                for stock_word in [
                    "股票",
                    "股价",
                    "涨停",
                    "跌停",
                    "个股",
                    "公司",
                    "上市",
                ]
            ):
                return True

    return False


def parse_news_time(news_item: Dict[str, Any]) -> Optional[Any]:
    """解析新闻时间（供外部调用）

    Args:
        news_item: 新闻项

    Returns:
        datetime对象或None
    """
    from datetime import datetime

    # 优先使用已解析的ctime
    ctime = news_item.get("ctime")
    if ctime and isinstance(ctime, (int, float)):
        return datetime.fromtimestamp(int(ctime), tz=BJT)

    # 尝试从raw字段解析
    raw = news_item.get("raw", {})
    time_str = (
        raw.get("time")
        or raw.get("ctime")
        or raw.get("rtime")
        or news_item.get("time")
        or news_item.get("rtime")
    )

    if not time_str:
        return None

    try:
        if isinstance(time_str, str):
            if time_str.isdigit():
                return datetime.fromtimestamp(int(time_str), tz=BJT)
            elif len(time_str) == 16:
                return datetime.strptime(time_str, "%Y-%m-%d %H:%M").replace(tzinfo=BJT)
            elif len(time_str) == 10:
                return datetime.strptime(time_str, "%Y-%m-%d").replace(tzinfo=BJT)
        elif isinstance(time_str, (int, float)):
            return datetime.fromtimestamp(time_str, tz=BJT)
    except Exception as e:
        log.debug(f"解析新闻时间失败: {e}, time_str={time_str}")

    return None


def fetch_all_news(
    pages: Optional[int] = None,
    merge_sources: bool = True,
    max_workers: Optional[int] = None,
    use_cache: bool = True,
) -> List[Dict[str, Any]]:
    """获取所有新闻（多API合并版）

    Args:
        pages: 每个API获取的最大页数，None则使用配置
        merge_sources: 是否合并多个API的数据
        max_workers: 并发线程数，None则根据API数量动态调整
        use_cache: 是否使用缓存，默认为True

    Returns:
        新闻列表
    """
    from datetime import datetime, timedelta

    log.info("fetch_all_news 开始（多API合并版）")

    # 初始化API状态
    _init_api_status()

    # 计算24小时前的时间
    twenty_four_hours_ago = datetime.now(BJT) - timedelta(hours=24)
    log.info(f"24小时前的时间: {twenty_four_hours_ago.strftime('%Y-%m-%d %H:%M:%S')}")

    # 从配置文件获取最大新闻页数
    max_pages = get_config_value("system.data_fetcher.news_pages", 8)
    if pages is not None:
        max_pages = pages

    # 注意：不再强制 min_pages=10
    # 调用方（如 quick_start）可以传入较少的页数以加快首次加载
    # 后台刷新由 background_data_updater 使用配置中的完整页数
    log.info(f"每个API最大获取页数: {max_pages}")

    # 动态调整并发线程数
    if max_workers is None:
        enabled_apis = [
            config for config in NEWS_API_CONFIGS if config.get("enabled", True)
        ]
        max_workers = min(len(enabled_apis), 5)  # 最多5个线程
    log.info(f"新闻获取并发线程数: {max_workers}")

    # 生成缓存键 - 优化：使用10分钟缓存窗口，减少重复请求和API压力
    cache_key = f"news:multi_api:24h:{max_pages}:{int(time.time() / 600)}"
    cached = NEWS_CACHE.get(cache_key)
    if use_cache and cached:
        log.info(f"使用缓存新闻 {len(cached)} 条")
        NEWS_CACHE.adjust_cache_size()
        return cached  # type: ignore

    # 从持久化存储加载历史新闻
    stored_news = _load_news_from_storage(hours=24)
    {news.get("id") for news in stored_news if news.get("id")}
    if stored_news:
        log.info(f"从持久化存储加载了 {len(stored_news)} 条历史新闻")

    all_api_news: List[List[Dict[str, Any]]] = []

    if not merge_sources:
        # 单API模式 - 只使用同花顺
        log.info("使用单API模式（同花顺）")
        # 从NEWS_API_CONFIGS中找到ths配置
        ths_config = None
        for config in NEWS_API_CONFIGS:
            if config.get("name") == "ths":
                ths_config = config
                break
        # 如果找不到ths配置，使用第一个配置
        if not ths_config and NEWS_API_CONFIGS:
            ths_config = NEWS_API_CONFIGS[0]
        # 如果还是没有配置，返回空列表
        if not ths_config:
            log.warning("没有找到新闻API配置")
            return []
        all_items = _fetch_all_news_from_single_api(
            ths_config, max_pages, twenty_four_hours_ago
        )
        all_api_news = [all_items]
    else:
        # 多API合并模式
        log.info(f"使用多API合并模式，API数量: {len(NEWS_API_CONFIGS)}")

        # 优化：先快速获取财联社快讯（单次请求，无分页，最快出数据）
        cls_config = None
        other_configs = []
        for config in NEWS_API_CONFIGS:
            if config.get("enabled", True):
                if config.get("name") == "cls_flash":
                    cls_config = config
                else:
                    other_configs.append(config)

        cls_news: List[Dict[str, Any]] = []
        if cls_config:
            try:
                log.info("[优先通道] 获取财联社7x24快讯...")
                cls_items = _fetch_news_from_api(cls_config, "", 1)
                if cls_items:
                    cls_news = cls_items
                    all_api_news.append(cls_news)
                    log.info(f"[优先通道] 财联社快讯: {len(cls_news)}条")
            except Exception as e:
                log.warning(f"[优先通道] 财联社快讯获取失败: {e}")

        # 并发获取其他API的新闻
        if other_configs:
            min_apis_for_quick_return = 2  # 至少2个API返回即可开始处理
            api_timeout_seconds = 15  # 单个API超时

            with ThreadPoolExecutor(max_workers=min(len(other_configs), max_workers)) as executor:
                future_to_api = {
                    executor.submit(
                        _fetch_all_news_from_single_api,
                        config,
                        max_pages,
                        twenty_four_hours_ago,
                    ): config["name"]
                    for config in other_configs
                }

                completed_apis = 0
                total_apis = len(future_to_api)
                for future in as_completed(future_to_api, timeout=api_timeout_seconds):
                    api_name = future_to_api[future]
                    try:
                        api_news = future.result(timeout=5)
                        log.info(f"API [{api_name}] 返回 {len(api_news)} 条新闻")
                        all_api_news.append(api_news)
                        completed_apis += 1
                    except TimeoutError:
                        log.warning(f"API [{api_name}] 获取超时，跳过")
                        completed_apis += 1
                    except Exception as e:
                        log.warning(f"API [{api_name}] 获取失败: {e}")
                        completed_apis += 1

                    # 快速返回：当已有足够API返回且超过一半完成时，不再等待
                    # 注意：cls_flash 已经单独优先获取，这里只算其他API
                    effective_count = len(all_api_news) + (1 if cls_news else 0)
                    if (effective_count >= min_apis_for_quick_return
                            and completed_apis >= total_apis / 2):
                        log.info(
                            f"快速返回: 已收集{effective_count}个API数据，"
                            f"完成{completed_apis}/{total_apis}个API"
                        )
                        for f in future_to_api:
                            if not f.done():
                                f.cancel()
                        break

        # 合并所有API的新闻
        all_items = _merge_news_from_multiple_apis(all_api_news)
        log.info(f"合并去重后共 {len(all_items)} 条新闻")

    # 合并历史新闻（去重）
    if stored_news:
        new_ids = {news.get("id") for news in all_items if news.get("id")}
        for news in stored_news:
            news_id = news.get("id")
            if news_id and news_id not in new_ids:
                all_items.append(news)
        log.info(f"合并历史新闻后共 {len(all_items)} 条新闻")

    # 按时间排序
    all_items = _sort_news_by_time(all_items)

    # 过滤24小时外的数据（再次确认）
    filtered_items = []
    for item in all_items:
        news_time = parse_news_time(item)
        if news_time and news_time >= twenty_four_hours_ago:
            filtered_items.append(item)

    log.info(f"24小时内新闻: {len(filtered_items)} 条")

    # 过滤非股市相关的新闻
    stock_related_items = []
    for item in filtered_items:
        if _is_stock_related_news(item):
            stock_related_items.append(item)

    log.info(f"股市相关新闻: {len(stock_related_items)} 条")

    # 按质量排序新闻（如果启用）
    stock_related_items = sort_news_by_quality(stock_related_items)

    # 保存新闻到持久化存储
    _save_news_to_storage(stock_related_items)

    # 清理旧新闻
    _cleanup_old_news()

    # 统计新闻数量（用于前端展示）
    stats = {
        "total_fetched": sum(len(api_news) for api_news in all_api_news)
        if merge_sources
        else len(all_items),
        "after_dedup": len(all_items),
        "after_24h_filter": len(filtered_items),
        "after_stock_filter": len(stock_related_items),
    }

    # 缓存结果（包含统计数据）
    ttl = max(NEWS_CACHE.get_optimal_ttl("news"), 120)
    NEWS_CACHE.set(cache_key, stock_related_items, ttl=ttl)
    NEWS_CACHE.set(cache_key + ":stats", stats, ttl=ttl)
    NEWS_CACHE.adjust_cache_size()

    log.info(
        f"新闻统计: 原始={stats['total_fetched']} 去重后={stats['after_dedup']} 24h内={stats['after_24h_filter']} 相关={stats['after_stock_filter']}"
    )

    return stock_related_items


def calculate_news_quality_score(news_item: Dict[str, Any]) -> float:
    """计算新闻质量评分

    评分维度:
    1. 来源权重 (40%)
    2. 关键词匹配 (30%)
    3. 提及股票数量 (20%)
    4. 标题长度 (10%)

    Args:
        news_item: 新闻项

    Returns:
        float: 质量评分 (0.0-1.0)
    """
    # 读取配置
    enable_quality_scoring: bool = bool(
        get_config_value(
            "system.data_fetcher.news_quality.enable_quality_scoring", True
        )
    )
    if not enable_quality_scoring:
        return 1.0  # 不启用评分时返回满分

    source_weights: Dict[str, float] = get_config_value(
        "system.data_fetcher.news_quality.source_weight",
        {
            "ths": 1.0,
            "eastmoney": 0.9,
            "sina": 0.8,
            "cls_flash": 0.85,
        },
    )
    keyword_bonus: float = float(
        get_config_value("system.data_fetcher.news_quality.keyword_bonus", 0.3)
    )
    stock_count_bonus: float = float(
        get_config_value("system.data_fetcher.news_quality.stock_count_bonus", 0.2)
    )
    float(
        get_config_value("system.data_fetcher.news_quality.title_length_penalty", 0.1)
    )

    score = 0.0

    # 1. 来源权重 (40%)
    source = news_item.get("source", "")
    source_score = source_weights.get(source, 0.7)  # 默认0.7
    score += source_score * 0.4

    # 2. 关键词匹配 (30%)
    title = news_item.get("title", "").lower()
    digest = news_item.get("digest", "").lower()
    keyword_match_count = 0
    for keyword in STOCK_RELATED_KEYWORDS[:50]:  # 只检查前50个高频关键词
        if keyword.lower() in title or keyword.lower() in digest:
            keyword_match_count += 1
            if keyword_match_count >= 3:
                break  # 最多匹配3个
    keyword_score = min(1.0, 0.5 + keyword_match_count * keyword_bonus / 3)
    score += keyword_score * 0.3

    # 3. 提及股票数量 (20%)
    stock_count = len(news_item.get("stock", []))
    stock_score = min(1.0, 0.5 + stock_count * stock_count_bonus)
    score += stock_score * 0.2

    # 4. 标题长度 (10%)
    title_len = len(news_item.get("title", ""))
    if 10 <= title_len <= 50:
        length_score = 1.0
    elif 5 <= title_len < 10:
        length_score = 0.8
    elif 50 < title_len <= 100:
        length_score = 0.8
    else:
        length_score = 0.6
    score += length_score * 0.1

    return max(0.0, min(1.0, score))


def get_dynamic_api_pages(api_config: Dict[str, Any]) -> int:
    """获取API的动态页数

    基于API历史表现动态调整获取页数

    Args:
        api_config: API配置

    Returns:
        int: 动态页数
    """
    enable_dynamic = get_config_value(
        "system.data_fetcher.dynamic_api_priority.enable_dynamic_priority", True
    )
    if not enable_dynamic:
        val = get_config_value("system.data_fetcher.news_pages", 8)
        return int(val) if val is not None else 8

    api_name = api_config["name"]
    min_pages_val = get_config_value(
        "system.data_fetcher.dynamic_api_priority.min_pages", 5
    )
    min_pages = int(min_pages_val) if min_pages_val is not None else 5
    max_pages_val = get_config_value(
        "system.data_fetcher.dynamic_api_priority.max_pages", 15
    )
    max_pages = int(max_pages_val) if max_pages_val is not None else 15
    default_pages_val = get_config_value("system.data_fetcher.news_pages", 8)
    default_pages = int(default_pages_val) if default_pages_val is not None else 8

    # 如果没有历史数据，返回默认页数
    if api_name not in NEWS_API_STATUS:
        return default_pages

    status = NEWS_API_STATUS[api_name]
    metrics = status.get("metrics", {})

    total_count = metrics.get("total_count", 0)
    if total_count < 5:  # 数据不足，使用默认
        return default_pages

    # 计算各维度得分
    success_rate = metrics.get("success_rate", 0.5)
    success_score = success_rate

    avg_response_time = metrics.get("avg_response_time", 5.0)
    # 响应时间越短越好 (0-10秒映射到1-0)
    response_score = max(0.0, min(1.0, 1.0 - avg_response_time / 10.0))

    avg_news_count = metrics.get("news_count", 0) / max(
        1, metrics.get("success_count", 1)
    )
    # 每次获取新闻数越多越好 (0-30条映射到0-1)
    news_score = min(1.0, avg_news_count / 30.0)

    # 综合得分
    success_rate_weight_val = get_config_value(
        "system.data_fetcher.dynamic_api_priority.success_rate_weight", 0.4
    )
    success_rate_weight = (
        float(success_rate_weight_val) if success_rate_weight_val is not None else 0.4
    )
    response_time_weight_val = get_config_value(
        "system.data_fetcher.dynamic_api_priority.response_time_weight", 0.3
    )
    response_time_weight = (
        float(response_time_weight_val) if response_time_weight_val is not None else 0.3
    )
    news_count_weight_val = get_config_value(
        "system.data_fetcher.dynamic_api_priority.news_count_weight", 0.3
    )
    news_count_weight = (
        float(news_count_weight_val) if news_count_weight_val is not None else 0.3
    )

    total_score = (
        success_score * success_rate_weight
        + response_score * response_time_weight
        + news_score * news_count_weight
    )

    # 映射到页数范围
    dynamic_pages = int(min_pages + (max_pages - min_pages) * total_score)

    log.debug(
        f"API [{api_name}] 动态页数: {dynamic_pages} "
        f"(成功率={success_rate:.2f}, 响应时间={avg_response_time:.2f}s, "
        f"平均新闻数={avg_news_count:.1f})"
    )

    return dynamic_pages


def enhance_news_digest(news_item: Dict[str, Any]) -> Dict[str, Any]:
    """增强新闻摘要

    提取关键信息并优化摘要内容

    Args:
        news_item: 新闻项

    Returns:
        Dict[str, Any]: 增强后的新闻项
    """
    title = news_item.get("title", "")
    digest = news_item.get("digest", "")

    # 如果摘要为空，使用标题
    if not digest:
        news_item["digest"] = title
        return news_item

    # 提取数字/百分比
    import re

    number_pattern = r"(\d+(?:\.\d+)?)\s*[万亿千百]?[元元股手万手]?|(\d+(?:\.\d+)?)\s*%"
    numbers = re.findall(number_pattern, title + digest)

    if numbers:
        # 提取关键数字并添加到摘要开头
        key_numbers = []
        for match in numbers[:3]:  # 最多3个
            num_str = match[0] if match[0] else match[1]
            if num_str:
                key_numbers.append(num_str)

        if key_numbers:
            enhanced_digest = f"【关键数据: {', '.join(key_numbers)}】{digest}"
            news_item["digest"] = enhanced_digest

    return news_item


def sort_news_by_quality(news_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """按质量排序新闻

    排序规则:
    1. 质量评分 (高 -> 低)
    2. 时间 (新 -> 旧)

    Args:
        news_list: 新闻列表

    Returns:
        List[Dict[str, Any]]: 排序后的新闻列表
    """
    enable_sorting = get_config_value(
        "system.data_fetcher.news_quality.enable_quality_sorting", True
    )
    if not enable_sorting:
        return news_list

    # 先计算质量评分
    for news in news_list:
        news["quality_score"] = calculate_news_quality_score(news)
        news = enhance_news_digest(news)

    # 排序
    def sort_key(news: Dict[str, Any]) -> Tuple[float, int]:
        quality_score = news.get("quality_score", 0.5)
        ctime = news.get("ctime", 0)
        return (-float(quality_score), -int(ctime))  # 负号表示降序

    return sorted(news_list, key=sort_key)


def get_news_stats() -> Dict[str, Any]:
    """获取新闻统计信息

    Returns:
        新闻统计字典，包含所有必需字段
    """
    # 返回包含所有必需字段的默认值
    # 注意：不依赖缓存内部结构，避免访问私有属性
    return {
        "total_fetched": 0,
        "after_dedup": 0,
        "after_24h_filter": 0,
        "after_stock_filter": 0,
        "avg_score_all": 0.0,
        "avg_score_picks": 0.0,
    }


# 兼容旧接口 - 获取单页新闻（同花顺）
@circuit_breaker(
    failure_threshold=NEWS_FAILURE_THRESHOLD, recovery_timeout=NEWS_RECOVERY_TIMEOUT
)
def _fetch_ths_page(tag_value: str, page: int = 1) -> List[Dict[str, Any]]:
    """获取同花顺新闻页面（兼容旧接口）"""
    # 从NEWS_API_CONFIGS中找到ths配置
    ths_config = None
    for config in NEWS_API_CONFIGS:
        if config.get("name") == "ths":
            ths_config = config
            break
    # 如果找不到ths配置，使用第一个配置
    if not ths_config and NEWS_API_CONFIGS:
        ths_config = NEWS_API_CONFIGS[0]
    # 如果还是没有配置，返回空列表
    if not ths_config:
        log.warning("没有找到新闻API配置")
        return []
    news = _fetch_news_from_api(ths_config, tag_value, page)
    # 返回原始格式以保持兼容
    return [item.get("raw", item) for item in news]


# ==================== Redis 新闻缓存 ====================

# Redis 新闻缓存键
REDIS_NEWS_KEY = "news:redis:all"
REDIS_NEWS_TIMESTAMP_KEY = "news:redis:timestamp"


def store_news_to_redis(news_list: List[Dict[str, Any]], ttl: int = 600) -> bool:
    """存储新闻到 Redis 缓存（用于定时存储）

    Args:
        news_list: 新闻列表
        ttl: 缓存过期时间（秒），默认10分钟

    Returns:
        bool: 是否存储成功
    """
    if not NEWS_CACHE.use_redis or not NEWS_CACHE.redis_client:
        log.debug("Redis未启用，跳过新闻存储")
        return False

    try:
        import json

        redis_client = NEWS_CACHE.redis_client
        # 序列化为 JSON 存储
        news_json = json.dumps(news_list, ensure_ascii=False)
        pipe = redis_client.pipeline()
        pipe.setex(REDIS_NEWS_KEY, ttl, news_json)
        pipe.setex(REDIS_NEWS_TIMESTAMP_KEY, ttl, str(int(time.time())))
        pipe.execute()
        log.info(f"新闻已存储到Redis: {len(news_list)}条, TTL={ttl}秒")
        return True
    except Exception as e:
        log.warning(f"存储新闻到Redis失败: {e}")
        return False


def load_news_from_redis() -> Tuple[List[Dict[str, Any]], int]:
    """从 Redis 缓存加载新闻（用于启动时或缓存为空时）

    Returns:
        Tuple[新闻列表, 新闻时间戳]
    """
    if not NEWS_CACHE.use_redis or not NEWS_CACHE.redis_client:
        return [], 0

    try:
        import json

        redis_client = NEWS_CACHE.redis_client
        pipe = redis_client.pipeline()
        pipe.get(REDIS_NEWS_KEY)
        pipe.get(REDIS_NEWS_TIMESTAMP_KEY)
        results = pipe.execute()

        news_json = results[0]
        timestamp_str = results[1]

        if news_json:
            news_list = json.loads(news_json)
            timestamp = int(timestamp_str) if timestamp_str else 0
            age = int(time.time()) - timestamp if timestamp else 0
            log.info(f"从Redis加载新闻: {len(news_list)}条, 缓存时间: {age}秒前")
            return news_list, timestamp
    except Exception as e:
        log.warning(f"从Redis加载新闻失败: {e}")

    return [], 0


def clear_redis_news_cache() -> bool:
    """清理 Redis 新闻缓存

    Returns:
        bool: 是否清理成功
    """
    if not NEWS_CACHE.use_redis or not NEWS_CACHE.redis_client:
        return False

    try:
        redis_client = NEWS_CACHE.redis_client
        redis_client.delete(REDIS_NEWS_KEY, REDIS_NEWS_TIMESTAMP_KEY)
        log.info("Redis新闻缓存已清理")
        return True
    except Exception as e:
        log.warning(f"清理Redis新闻缓存失败: {e}")
        return False


def fetch_and_store_news_redis(pages: int = 10) -> List[Dict[str, Any]]:
    """获取新闻并存储到 Redis（定时任务用）

    Args:
        pages: 抓取页数

    Returns:
        获取到的新闻列表
    """
    try:
        log.info(f"开始获取新闻并存入Redis (pages={pages})...")
        news = fetch_all_news(pages=pages, use_cache=False)
        if news:
            # 存储到 Redis，TTL 10分钟
            store_news_to_redis(news, ttl=600)
            # 同时存入 NEWS_CACHE 供 pipeline 立即使用
            _cache_news_to_memory(news)
        log.info(f"新闻获取并存入Redis完成: {len(news)}条")
        return news
    except Exception as e:
        log.error(f"获取新闻并存入Redis失败: {e}")
        return []


def _cache_news_to_memory(news_list: List[Dict[str, Any]]) -> None:
    """将新闻存入 NEWS_CACHE 内存缓存（供 pipeline 立即使用）

    Args:
        news_list: 新闻列表
    """
    try:
        pages = get_config_value("system.pipeline.news_pages", 5)
        time_window = 600  # 10分钟缓存窗口
        cache_window = int(time.time() / time_window)
        cache_key = f"news:multi_api:24h:{pages}:{cache_window}"
        NEWS_CACHE.set(cache_key, news_list, ttl=300)  # 5分钟内存缓存
        log.info(f"新闻已存入内存缓存: {len(news_list)}条, key={cache_key}")
    except Exception as e:
        log.warning(f"存入内存缓存失败: {e}")
