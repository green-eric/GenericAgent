#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股利好监控系统 - 流水线管理模块
负责数据刷新和缓存控制
"""

import json
import os
import threading
import time
from typing import Any, Dict, List, Tuple

from modules import log_system_error, run_pipeline
from modules.logging_config import setup_all_loggers
from modules.param_loader import load_params
from modules.utils import get_config_value

from .cache_manager import backtest_lock, pipeline_lock, server_cache
from .data_formatter import format_hot8_data, format_news_data
from modules.sector_registry import aggregate_sector_heat

logger = setup_all_loggers()
log = logger

# 快速启动数据获取锁，防止惊群效应（多线程并发请求时重复执行网络请求）
_quick_start_lock = threading.Lock()

# 快速启动数据 TTL（秒），防止长期保留过时数据
# 增加TTL给后台pipeline更多时间完成（full pipeline需要5-10分钟）
QUICK_START_TTL = 900  # 15分钟

# 刷新状态标记 - 标记后台刷新是否正在进行中
_refresh_in_progress = False

# 全局参数变量
PARAMS: Dict[str, float] = {k: float(v) for k, v in load_params().items()}

# 配置文件的MD5哈希，用于检测变更
_config_file_hash: str = ""


def _get_config_hash() -> str:
    """获取配置文件的MD5哈希值"""
    import hashlib

    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.yaml"
    )
    try:
        with open(config_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return ""


def reload_params(force: bool = False) -> bool:
    """重新加载配置参数

    Args:
        force: 是否强制重载（忽略变更检测）

    Returns:
        bool: 是否实际发生了重载
    """
    global PARAMS, _config_file_hash

    # 检查配置文件是否变更
    if not force:
        current_hash = _get_config_hash()
        if current_hash == _config_file_hash and _config_file_hash:
            # 配置未变更，不需要重载
            return False

    old_params = dict(PARAMS)
    PARAMS = {k: float(v) for k, v in load_params().items()}
    _config_file_hash = _get_config_hash()

    # 检查是否有实际变更
    changed_keys = [k for k in PARAMS if PARAMS.get(k) != old_params.get(k)]
    if changed_keys:
        log.info(f"参数已重新加载，变更项: {changed_keys}")

        # 热更新交易代理参数
        try:
            from modules.trading.api import reload_agent_params

            if reload_agent_params():
                log.info("交易代理参数已同步更新")
        except ImportError as e:
            log.warning(f"无法导入交易代理重载函数: {e}")
    else:
        log.info("参数检查完成，无变更")

    return True


def _do_refresh_pipeline_data(force_refresh: bool) -> Dict[str, Any]:
    """实际执行流水线数据刷新（带超时保护）

    Args:
        force_refresh: 是否强制刷新

    Returns:
        流水线数据字典，如果超时则返回空字典
    """
    import concurrent.futures

    max_stocks = get_config_value("system.pipeline.picks_limit", 20)
    pipeline_timeout = 120  # Pipeline 最大执行时间（秒）

    if force_refresh:
        from modules.news_fetcher import NEWS_CACHE

        # 使用 Cache 公共方法删除特定键，避免直接访问内部分片属性
        pipeline_cache_keys = ["pipeline:result:latest"]
        NEWS_CACHE.delete_keys(pipeline_cache_keys)
        # 同时清除所有缓存确保干净状态
        NEWS_CACHE.clear()
        server_cache.pop("quick_start_data", None)
        log.info("Pipeline缓存已清空，强制刷新数据 [FORCE_REFRESH]")

    log.info(
        f"执行run_pipeline获取新数据 [force_refresh={force_refresh}, timeout={pipeline_timeout}s]"
    )

    # 使用线程池执行，带超时保护
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run_pipeline, PARAMS)
        try:
            pipeline_result = future.result(timeout=pipeline_timeout)
        except concurrent.futures.TimeoutError:
            log.error(f"Pipeline执行超时({pipeline_timeout}秒)，返回空数据")
            return {}

    # 兼容5/6/7元组返回值
    result_len = len(pipeline_result)
    hot8_with_names = pipeline_result[0]
    rt_picks = pipeline_result[1]
    quotes = pipeline_result[2]
    all_news = pipeline_result[3]
    sec_sum = pipeline_result[4]

    if result_len >= 6:
        news_stats = pipeline_result[5]
    else:
        news_stats = {}

    if result_len >= 7:
        supplemental_sources = pipeline_result[6]
    else:
        supplemental_sources = set()

    if result_len >= 7:
        log.info(
            f"返回7元组: hot8={len(hot8_with_names)}, supplemental={len(supplemental_sources)}"
        )
    elif result_len == 6:
        log.info(f"返回6元组: hot8={len(hot8_with_names)}")
    else:
        log.info(f"返回5元组: hot8={len(hot8_with_names)}")

    # 转换supplemental_sources为set（兼容pipeline返回的list类型）
    if isinstance(supplemental_sources, list):
        supplemental_sources = set(supplemental_sources)

    # 异步推送新闻告警，避免阻塞主流程
    def async_push_news() -> None:
        try:
            from modules import push_feishu_news_alert

            push_feishu_news_alert(all_news)
        except Exception as e:
            log.warning(f"异步推送新闻失败: {e}")

    thread = threading.Thread(target=async_push_news, daemon=True)
    thread.start()

    # 确保按总分降序排序
    rt_picks.sort(key=lambda x: x.get("score", {}).get("total", 0), reverse=True)

    # 限制股票数量
    rt_picks = rt_picks[:max_stocks]

    # 打印前10个股票，以便调试
    log.info(f"run_pipeline返回股票数量: {len(rt_picks)}")
    log.info(
        f"排序后的前10个股票: {[(p.get('name', p.get('symbol')), p.get('symbol'), p.get('score', {}).get('total', 0)) for p in rt_picks[:10]]}"
    )
    log.info(f"run_pipeline返回新闻数量: {len(all_news)}")

    old_pipeline_data = server_cache.get("pipeline_data") or {}
    old_quick_data = server_cache.get("quick_start_data") or {}
    old_news = old_pipeline_data.get("news", {}) if old_pipeline_data else {}
    if not old_news:
        old_news = old_quick_data.get("news", {}) if old_quick_data else {}

    if len(all_news) == 0 and old_news:
        log.warning("本次获取新闻为空，从缓存恢复之前的数据")
        formatted_news = old_news
        # 确保 formatted_news 有正确的结构
        if not isinstance(formatted_news, dict):
            formatted_news = {"top_news": [], "recent_news": [], "all_news": []}
        news_stats = (
            old_pipeline_data.get("news_stats", news_stats)
            or old_quick_data.get("news_stats", news_stats)
            or {}
        )
        sec_sum = (
            old_pipeline_data.get("sec_sum", sec_sum)
            or old_quick_data.get("sec_sum", sec_sum)
            or {}
        )
    else:
        formatted_news = format_news_data(all_news)

    log.info(
        f"format_news_data返回top_news数量: {len(formatted_news.get('top_news', []))}"
    )
    log.info(
        f"format_news_data返回recent_news数量: {len(formatted_news.get('recent_news', []))}"
    )
    log.info(
        f"format_news_data返回all_news数量: {len(formatted_news.get('all_news', []))}"
    )

    # 确保 news_stats 始终有默认值，避免前端显示为空
    if not news_stats:
        news_stats = {}
    # 填充默认值
    news_stats.setdefault("total_fetched", len(all_news))
    news_stats.setdefault("after_dedup", len(formatted_news.get("all_news", [])))
    news_stats.setdefault("after_24h_filter", len(formatted_news.get("all_news", [])))
    news_stats.setdefault("after_stock_filter", len(formatted_news.get("all_news", [])))
    news_stats.setdefault("avg_score_all", news_stats.get("avg_score_all", 0.0))
    news_stats.setdefault("avg_score_picks", news_stats.get("avg_score_picks", 0.0))

    pipeline_data = {
        "hot8": format_hot8_data(hot8_with_names, quotes, supplemental_sources),
        "picks": rt_picks,
        "quotes": quotes,
        "news": formatted_news,
        "sec_sum": sec_sum,
        "sector_heat": aggregate_sector_heat(sec_sum),
        "news_stats": news_stats,
    }
    server_cache["pipeline_data"] = pipeline_data
    server_cache["last_update"] = time.time()
    server_cache["last_pipeline_start_time"] = time.time()  # 防抖标记
    server_cache["warmup_complete"] = True  # 标记预热完成
    # 只有当新闻数据有效时才删除快速启动缓存，保留备份
    formatted_all_news = formatted_news.get("all_news", [])
    log.info(
        f"_DEBUG: formatted_news.keys={list(formatted_news.keys())}, all_news count={len(formatted_all_news)}, bool={bool(formatted_all_news)}"
    )
    if formatted_all_news:
        server_cache.pop("quick_start_data", None)
        log.info("Pipeline有有效新闻，删除quick_start_data")
    else:
        log.info("Pipeline新闻为空，保留quick_start_data作为备份")
    log.info(
        f"流水线数据已更新: hot8={len(hot8_with_names)}, picks={len(rt_picks)}, news={len(all_news)}, sec_sum={sec_sum}, news_stats={news_stats}"
    )
    return pipeline_data


def _run_backtest_async(trigger_source: str = "scheduled") -> None:
    """异步执行回测（定时刷新或手动刷新触发）

    Args:
        trigger_source: 触发来源，"scheduled" 或 "manual"
    """
    try:
        from modules import run_backtest

        bt_result = run_backtest(
            days=get_config_value("system.backtest.default_days", 60), params=PARAMS
        )
        current_time = time.time()
        server_cache["backtest_data"] = bt_result
        server_cache["last_bt_update"] = current_time
        server_cache["last_bt_trigger_source"] = trigger_source
        server_cache["bt_in_progress"] = False
        bt_result["_bt_timestamp"] = current_time
        bt_result["_bt_trigger_source"] = trigger_source
        bt_result["_bt_in_progress"] = False
        _save_backtest_cache(bt_result, trigger_source, current_time)
        _save_backtest_to_redis(bt_result)
        log.info(f"回测数据已更新（来源={trigger_source}，文件+Redis）")
    except Exception as e:
        log.error(f"回测执行失败: {e}")
        server_cache["bt_in_progress"] = False


def _ensure_backtest_data(
    force_refresh: bool = False, trigger_source: str = "scheduled"
) -> Dict[str, Any]:
    """确保回测数据存在，如果不存在或过期则执行回测

    启动时不运行回测，直接返回缓存数据（Redis > 文件 > 空数据）

    Args:
        force_refresh: 是否强制刷新（忽略时间间隔）
        trigger_source: 触发来源 ("manual" 手工 / "scheduled" 定时)

    Returns:
        回测数据字典
    """
    current_time = time.time()
    backtest_interval = get_config_value(
        "system.business_constants.intervals.backtest_interval", 3600
    )  # 1小时

    bt_result = server_cache.get("backtest_data") or {}
    last_bt_update = server_cache.get("last_bt_update", 0)

    # 检查服务器启动时间，如果是刚启动（<5分钟），不运行回测
    server_start_time = server_cache.get("server_start_time", 0)
    is_startup = (
        (current_time - server_start_time) < 300 if server_start_time > 0 else True
    )

    # 启动时不运行回测，只使用缓存数据
    if is_startup:
        log.info(
            f"启动模式：跳过回测执行，使用缓存数据（启动时间: {server_start_time}）"
        )

    # 检查是否需要执行回测
    needs_update = (
        force_refresh  # 强制刷新
        and not is_startup  # 非启动状态
        or not bt_result  # 数据为空
        and not is_startup  # 非启动状态
        or current_time - last_bt_update > backtest_interval  # 数据过期
    )

    # 启动时：优先从 Redis 加载，其次从文件加载
    if is_startup and not bt_result:
        # 1. 尝试从 Redis 加载
        redis_bt, redis_ts = _load_backtest_from_redis()
        if redis_bt and redis_bt.get("trades", 0) > 0:
            log.info(f"从Redis恢复回测数据：trades={redis_bt.get('trades', 0)}")
            bt_result = redis_bt
            server_cache["backtest_data"] = bt_result
            server_cache["last_bt_update"] = redis_ts
            # 从 Redis 数据中读取触发源（保留原始触发来源）
            redis_trigger = redis_bt.get("_bt_trigger_source", "scheduled") if redis_bt else "scheduled"
            server_cache["last_bt_trigger_source"] = redis_trigger
            bt_result["_bt_timestamp"] = redis_ts
            bt_result["_bt_trigger_source"] = redis_trigger
            return bt_result

        # 2. 尝试从文件加载
        file_bt, file_trigger, file_ts = _load_backtest_cache()
        if file_bt and file_bt.get("trades", 0) > 0:
            log.info(
                f"从文件恢复回测数据：trades={file_bt.get('trades', 0)}, history={len(file_bt.get('history', []))}"
            )
            bt_result = file_bt
            server_cache["backtest_data"] = bt_result
            server_cache["last_bt_update"] = file_ts
            server_cache["last_bt_trigger_source"] = file_trigger
            # 保存到 Redis
            _save_backtest_to_redis(bt_result)
            bt_result["_bt_timestamp"] = file_ts
            bt_result["_bt_trigger_source"] = file_trigger
            return bt_result

        # 3. 启动时无缓存，返回空数据结构
        log.info("启动时无回测缓存，返回空数据")
        empty_result = {
            "trades": 0,
            "history": [],
            "total_return": 0,
            "max_drawdown": 0,
            "win_rate": 0,
            "_bt_timestamp": current_time,
            "_bt_trigger_source": "scheduled",
            "_bt_in_progress": False,
        }
        return empty_result

    # 非启动状态：继续原有逻辑
    # 服务器重启后从缓存文件恢复数据（如果内存缓存为空）
    if not bt_result and not force_refresh:
        # 内存缓存为空，尝试从文件加载
        file_bt, file_trigger, file_ts = _load_backtest_cache()
        if file_bt and file_bt.get("trades", 0) > 0:
            log.info(
                f"从缓存文件恢复回测数据：trades={file_bt.get('trades', 0)}, history={len(file_bt.get('history', []))}"
            )
            bt_result = file_bt
            server_cache["backtest_data"] = bt_result
            server_cache["last_bt_update"] = file_ts
            server_cache["last_bt_trigger_source"] = file_trigger
            # 重新检查是否需要更新（使用从文件加载的数据）
            needs_update = force_refresh or current_time - file_ts > backtest_interval

    # 强制刷新时立即标记为 manual，这样 API 返回时能正确显示
    if force_refresh:
        server_cache["last_bt_trigger_source"] = "manual"

    log.info(
        f"回测检查: trigger_source={trigger_source}, force_refresh={force_refresh}, 数据存在={bool(bt_result)}, "
        f"过期检查={current_time - last_bt_update:.0f}秒前, needs_update={needs_update}, is_startup={is_startup}"
    )

    if needs_update and not is_startup:
        log.info(
            f"回测需要更新: force_refresh={force_refresh}, last_bt_update={last_bt_update}, current_time={current_time}"
        )

        # 强制刷新时跳过缓存，直接重新计算
        if force_refresh:
            # 手动刷新：直接执行新回测
            log.info(f"手动刷新，执行同步回测... (来源: {trigger_source})")
        else:
            # 非强制刷新：尝试从缓存文件加载
            cached_bt, file_trigger, file_ts = _load_backtest_cache()
            log.info(
                f"从缓存文件加载: trades={cached_bt.get('trades', 0) if cached_bt else 0}, trigger={file_trigger}, ts={file_ts}"
            )

            # 检查缓存是否过期（定时回测需要检查，手动刷新已跳过此处）
            cache_age = current_time - file_ts if file_ts else float("inf")
            cache_valid = cache_age <= backtest_interval

            if cached_bt and cached_bt.get("trades", 0) > 0 and cache_valid:
                # 缓存有效：恢复缓存数据
                server_cache["backtest_data"] = cached_bt
                server_cache["last_bt_update"] = file_ts
                server_cache["last_bt_trigger_source"] = file_trigger
                log.info(f"从缓存文件恢复回测数据（未过期，{cache_age:.0f}s前）")
                cached_bt["_bt_timestamp"] = file_ts
                cached_bt["_bt_trigger_source"] = file_trigger
                return cached_bt
            elif cached_bt and cached_bt.get("trades", 0) > 0:
                # 缓存过期：执行新回测
                log.info(
                    f"缓存已过期（{cache_age:.0f}s > {backtest_interval}s），执行新回测"
                )
            else:
                # 无缓存：执行新回测
                log.info("无有效缓存，执行新回测")

        # 缓存无效或为空，同步执行回测（带锁保护防止并发）
        log.info(
            f"回测数据为空或过期，执行同步回测... (来源: {trigger_source}, force_refresh={force_refresh})"
        )

        # 尝试获取回测锁（最多等5秒）
        lock_acquired = backtest_lock.acquire(timeout=5)
        if not lock_acquired:
            log.warning("回测正在执行中，跳过本次请求")
            bt_result = server_cache.get("backtest_data") or {}
            bt_result["_bt_timestamp"] = server_cache.get("last_bt_update", 0)
            bt_result["_bt_trigger_source"] = server_cache.get(
                "last_bt_trigger_source", "scheduled"
            )
            bt_result["_bt_in_progress"] = True
            server_cache["bt_in_progress"] = True
            return bt_result

        try:
            server_cache["bt_in_progress"] = True
            from concurrent.futures import ThreadPoolExecutor, TimeoutError
            from modules import run_backtest

            backtest_timeout = get_config_value(
                "system.backtest.timeout", 600
            )  # 默认600秒超时（与config.yaml一致）

            log.info(
                f"开始执行回测: days={get_config_value('system.backtest.default_days', 60)}, timeout={backtest_timeout}秒"
            )

            def run_backtest_sync() -> Dict[str, Any]:
                return run_backtest(
                    days=get_config_value("system.backtest.default_days", 60),
                    params=PARAMS,
                )

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_backtest_sync)
                try:
                    bt_result = future.result(timeout=backtest_timeout)
                    server_cache["backtest_data"] = bt_result
                    server_cache["last_bt_update"] = current_time
                    server_cache["last_bt_trigger_source"] = trigger_source
                    server_cache["bt_in_progress"] = False
                    _save_backtest_cache(bt_result, trigger_source, current_time)
                    _save_backtest_to_redis(bt_result)
                    log.info("回测数据已更新并保存（文件+Redis）")
                    bt_result["_bt_timestamp"] = current_time
                    bt_result["_bt_trigger_source"] = trigger_source
                    bt_result["_bt_in_progress"] = False
                    return bt_result
                except TimeoutError:
                    log.error(f"回测执行超时({backtest_timeout}秒)，返回缓存数据")
                    server_cache["bt_in_progress"] = False
                    result = server_cache.get("backtest_data") or {}
                    result["_bt_timestamp"] = server_cache.get("last_bt_update", 0)
                    result["_bt_trigger_source"] = server_cache.get(
                        "last_bt_trigger_source", "scheduled"
                    )
                    result["_bt_in_progress"] = False
                    return result
        except Exception as e:
            log.error(f"同步回测执行失败: {e}")
            server_cache["bt_in_progress"] = False
            bt_result["_bt_timestamp"] = server_cache.get("last_bt_update", 0)
            bt_result["_bt_trigger_source"] = server_cache.get(
                "last_bt_trigger_source", "scheduled"
            )
            bt_result["_bt_in_progress"] = False
            return bt_result
        finally:
            backtest_lock.release()

    # 添加回测时间戳到结果中（始终添加）
    # 服务器重启后从缓存恢复，回测应标记为scheduled
    bt_result["_bt_timestamp"] = server_cache.get("last_bt_update", 0)

    # 使用cache中的实际trigger_source，不要强制覆盖
    # 这样重启时显示scheduled，手动刷新后显示manual
    cached_trigger = server_cache.get("last_bt_trigger_source", "scheduled")
    bt_result["_bt_trigger_source"] = cached_trigger

    return bt_result


def _load_backtest_cache() -> Tuple[Dict[str, Any], str, float]:
    """从缓存文件加载回测数据（向后兼容）

    Returns:
        (回测数据, 触发来源, 时间戳)
    """

    cache_file = "data/backtest_cache.json"
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("trades", 0) > 0:
                    # 兼容旧格式：没有保存trigger_source时默认为scheduled
                    trigger_source = data.get("_bt_trigger_source", "scheduled")
                    timestamp = data.get("_bt_timestamp", 0)
                    return data, trigger_source, timestamp
        except Exception as e:
            log.warning(f"加载回测缓存失败: {e}")
    return {}, "scheduled", 0


# ==================== Redis 回测数据缓存 ====================


def _save_backtest_to_redis(data: Dict[str, Any], ttl: int = 3600) -> bool:
    """存储回测数据到 Redis

    Args:
        data: 回测数据
        ttl: 缓存过期时间（秒），默认与回测间隔一致(1小时)

    Returns:
        bool: 是否存储成功
    """
    from modules.news_fetcher import NEWS_CACHE

    if not NEWS_CACHE.use_redis or not NEWS_CACHE.redis_client:
        log.debug("Redis未启用，跳过回测数据存储")
        return False

    try:

        redis_client = NEWS_CACHE.redis_client
        cache_key = "backtest:redis:data"
        cache_ts_key = "backtest:redis:timestamp"

        # 序列化为 JSON 存储
        data_json = json.dumps(data, ensure_ascii=False)
        pipe = redis_client.pipeline()
        pipe.setex(cache_key, ttl, data_json)
        pipe.setex(cache_ts_key, ttl, str(int(time.time())))
        pipe.execute()
        log.info(f"回测数据已存储到Redis: ttl={ttl}秒")
        return True
    except Exception as e:
        log.warning(f"存储回测数据到Redis失败: {e}")
        return False


def _load_backtest_from_redis() -> Tuple[Dict[str, Any], float]:
    """从 Redis 加载回测数据

    Returns:
        Tuple[回测数据, 时间戳]
    """
    from modules.news_fetcher import NEWS_CACHE

    if not NEWS_CACHE.use_redis or not NEWS_CACHE.redis_client:
        return {}, 0

    try:

        redis_client = NEWS_CACHE.redis_client
        cache_key = "backtest:redis:data"
        cache_ts_key = "backtest:redis:timestamp"

        pipe = redis_client.pipeline()
        pipe.get(cache_key)
        pipe.get(cache_ts_key)
        results = pipe.execute()

        data_json = results[0]
        timestamp_str = results[1]

        if data_json:
            data = json.loads(data_json)
            timestamp = int(timestamp_str) if timestamp_str else 0
            age = int(time.time()) - timestamp if timestamp else 0
            log.info(f"从Redis加载回测数据: trades={data.get('trades', 0)}, {age}秒前")
            return data, timestamp
    except Exception as e:
        log.warning(f"从Redis加载回测数据失败: {e}")

    return {}, 0


def _save_backtest_cache(
    data: Dict[str, Any], trigger_source: str, timestamp: float
) -> None:
    """保存回测数据到缓存文件"""

    cache_file = "data/backtest_cache.json"
    # 添加trigger_source和timestamp到缓存数据
    data["_bt_trigger_source"] = trigger_source
    data["_bt_timestamp"] = timestamp
    try:
        os.makedirs(os.path.dirname(cache_file) or ".", exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log.info("回测数据已保存到缓存文件")
    except Exception as e:
        log.error(f"保存回测缓存失败: {e}")


def _get_backtest_result(force_refresh: bool = False) -> Dict[str, Any]:
    """获取回测结果（统一处理trigger_source和缓存恢复）

    优化: 检测CLI写入的缓存文件更新，自动加载新数据到内存缓存

    Args:
        force_refresh: 是否强制刷新

    Returns:
        回测数据字典
    """
    bt_result = server_cache.get("backtest_data") or {}
    cached_trades = bt_result.get("trades", 0)

    log.info(
        f"_get_backtest_result: force_refresh={force_refresh}, cached_trades={cached_trades}"
    )

    if bt_result and "trades" in bt_result and bt_result.get("trades", 0) > 0:
        cached_trigger = server_cache.get("last_bt_trigger_source", "scheduled")
        cached_ts = server_cache.get("last_bt_update", 0)

        if not cached_trigger:
            file_bt, file_trigger, file_ts = _load_backtest_cache()
            if file_bt and file_bt.get("trades", 0) > 0:
                log.info(f"从文件恢复trigger_source: trigger={file_trigger}")
                cached_trigger = file_trigger or "scheduled"
                cached_ts = file_ts
                server_cache["backtest_data"] = file_bt
                server_cache["last_bt_update"] = file_ts
                server_cache["last_bt_trigger_source"] = cached_trigger
                bt_result = file_bt

        if cached_trigger != "cli":
            cache_file = "data/backtest_cache.json"
            if os.path.exists(cache_file):
                try:
                    file_bt, file_trigger, file_ts = _load_backtest_cache()
                    if (
                        file_bt
                        and file_bt.get("trades", 0) > 0
                        and file_ts > cached_ts + 1
                    ):
                        log.info(
                            f"检测到CLI更新的回测缓存(文件时间{file_ts:.0f} > 内存时间{cached_ts:.0f})，"
                            f"trigger={file_trigger}, trades={file_bt.get('trades', 0)}"
                        )
                        server_cache["backtest_data"] = file_bt
                        server_cache["last_bt_update"] = file_ts
                        server_cache["last_bt_trigger_source"] = file_trigger or "cli"
                        bt_result = file_bt
                        cached_trigger = file_trigger or "cli"
                        cached_ts = file_ts
                except Exception as e:
                    log.debug(f"检查CLI缓存更新失败: {e}")

        bt_result["_bt_timestamp"] = cached_ts
        bt_result["_bt_trigger_source"] = cached_trigger
        bt_result["_bt_in_progress"] = server_cache.get("bt_in_progress", False)
    else:
        log.info("缓存无回测数据，需要执行新回测")

    return bt_result


def _merge_pipeline_and_quick(pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
    """统一合并 pipeline 数据与 quick_start 数据

    规则：
    1. pipeline 新闻为空 → 使用 quick_start 新闻/新闻统计/板块
    2. pipeline picks 为空或全是 _quick_start → 使用 quick_start picks
    3. pipeline hot8 为空 → 使用 quick_start hot8

    Args:
        pipeline_data: 流水线数据（会被浅拷贝，不修改原始数据）

    Returns:
        合并后的数据字典（浅拷贝，不影响原始 pipeline_data）
    """
    quick_data = server_cache.get("quick_start_data")
    if not quick_data or not isinstance(quick_data, dict):
        return pipeline_data

    merged = dict(pipeline_data)  # 浅拷贝，不修改原始数据
    changed = False

    # 1. 新闻为空时从 quick_start 补充
    pipeline_news = pipeline_data.get("news", {})
    pipeline_all_news = pipeline_news.get("all_news") if pipeline_news else None
    if not pipeline_all_news:
        quick_news = quick_data.get("news", {})
        quick_all_news = quick_news.get("all_news") if quick_news else None
        if quick_all_news:
            merged["news"] = quick_news
            merged["news_stats"] = quick_data.get("news_stats", {})
            merged["sec_sum"] = quick_data.get("sec_sum", {})
            merged["sector_heat"] = quick_data.get("sector_heat", {})
            changed = True

    # 2. picks 为空或全是 _quick_start → 使用 quick_start picks
    cached_picks = merged.get("picks", [])
    if not cached_picks or all(p.get("_quick_start", False) for p in cached_picks):
        quick_picks = quick_data.get("picks", [])
        if quick_picks:
            merged["picks"] = quick_picks
            changed = True

    # 3. hot8 为空 → 使用 quick_start hot8
    if not merged.get("hot8") or len(merged.get("hot8", [])) == 0:
        quick_hot8 = quick_data.get("hot8", [])
        if quick_hot8:
            merged["hot8"] = quick_hot8
            changed = True

    if changed:
        log.debug("[merge] 已从 quick_start_data 补充缺失字段")

    return merged


def _build_empty_pipeline_data() -> Dict[str, Any]:
    """构建空的流水线数据结构"""
    return {
        "hot8": [],
        "picks": [],
        "quotes": {},
        "news": {"top_news": [], "recent_news": [], "all_news": []},
        "sec_sum": {},
        "sector_heat": {},
        "news_stats": {},
    }


def _trigger_background_refresh(force_refresh: bool) -> bool:
    """尝试触发后台异步刷新（非阻塞）

    采用 stale-while-revalidate 模式：
    先返回旧缓存数据，后台异步刷新，下次请求获取新数据。

    Args:
        force_refresh: 是否强制刷新

    Returns:
        是否成功触发后台刷新
    """
    global _refresh_in_progress

    current_time = time.time()

    # 强制刷新时跳过冷却期检查（用户明确要求刷新）
    if not force_refresh:
        # 添加刷新冷却期：连续失败后等待30秒再重试（缩短从60秒）
        last_refresh_time = getattr(
            _trigger_background_refresh, "_last_refresh_time", 0
        )
        last_refresh_failed = getattr(
            _trigger_background_refresh, "_last_refresh_failed", False
        )

        # 如果上次刷新失败且距今不足30秒，跳过刷新（非强制刷新）
        if last_refresh_failed and (current_time - last_refresh_time) < 30:
            log.info(
                f"上次刷新失败，冷却期中（剩余{int(30 - (current_time - last_refresh_time))}秒），跳过后台触发"
            )
            return False

    _trigger_background_refresh._last_refresh_time = current_time

    lock_acquired = pipeline_lock.acquire(blocking=False)
    if not lock_acquired:
        log.info("流水线正在刷新中，跳过后台触发")
        return False

    def _bg_refresh() -> None:
        global _refresh_in_progress
        try:
            _refresh_in_progress = True
            pipeline_data = _do_refresh_pipeline_data(force_refresh)
            if pipeline_data and len(pipeline_data) > 0:
                server_cache["pipeline_data"] = pipeline_data
                server_cache["last_update"] = time.time()
                server_cache["warmup_complete"] = True
                log.info("后台异步刷新完成")
                _trigger_background_refresh._last_refresh_failed = False
            else:
                # 即使返回空数据，也重置失败标记（避免无限冷却）
                # 空数据可能是网络问题，下次可以再试
                log.warning("后台异步刷新返回空数据，重置失败标记以允许重试")
                _trigger_background_refresh._last_refresh_failed = False
        except Exception as e:
            log.error(f"后台异步刷新失败: {e}")
            _trigger_background_refresh._last_refresh_failed = True
        finally:
            _refresh_in_progress = False
            pipeline_lock.release()

    thread = threading.Thread(target=_bg_refresh, daemon=True)
    thread.start()
    log.info(f"已触发后台异步刷新 [force_refresh={force_refresh}]")
    return True


def get_pipeline_data(
    force_refresh: bool = False,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """获取流水线数据和回测数据

    采用 stale-while-revalidate 策略：
    - 缓存有效期内：直接返回缓存数据
    - 缓存过期但有旧数据：立即返回旧数据，后台触发刷新
    - 缓存过期且无旧数据：阻塞等待刷新完成（仅首次启动）
    - 强制刷新：阻塞等待刷新完成

    Args:
        force_refresh: 是否强制刷新

    Returns:
        (流水线数据, 回测数据)
    """
    try:
        reload_params()

        current_time = time.time()
        cache_validity = get_config_value("system.schedule.pipeline_cache", 60)
        last_update = server_cache.get("last_update", 0)
        warmup_complete = server_cache.get("warmup_complete", False)
        cached_data = server_cache.get("pipeline_data")

        # 1. 缓存有效且非强制刷新 → 直接返回（最新数据）
        if (
            not force_refresh
            and cached_data
            and last_update > 0
            and current_time - last_update < cache_validity
        ):
            log.debug(
                f"[CACHE_HIT] 返回最新缓存数据 (age={current_time - last_update:.0f}s < {cache_validity}s)"
            )
            bt_result = _get_backtest_result(force_refresh)
            return cached_data, bt_result

        # 2. 缓存过期但有旧数据且非强制刷新 → stale-while-revalidate
        #    立即返回旧数据，后台触发刷新，前端下次请求获取新数据
        #    但如果数据过期超过 max_staleness 秒，则强制阻塞刷新
        max_staleness = get_config_value("system.server.max_staleness", 300)
        if not force_refresh and cached_data and isinstance(cached_data, dict):
            cache_age = current_time - last_update if last_update > 0 else float("inf")
            # 数据过期超过最大容忍时间，强制同步刷新
            if cache_age > max_staleness:
                log.warning(
                    f"缓存数据已严重过期({cache_age:.0f}s > max_staleness={max_staleness}s)，强制同步刷新"
                )
                # 跳过 stale-while-revalidate，进入步骤3进行同步刷新
            else:
                # SWR：缓存过期但在容忍范围内，返回旧数据并触发后台刷新
                log.debug(
                    f"[SWR] 缓存已过期({cache_age:.0f}s > {cache_validity}s)，返回旧数据并触发后台刷新"
                )
                _trigger_background_refresh(False)
                # 统一合并：从 quick_start_data 补充缺失字段
                cached_data = _merge_pipeline_and_quick(cached_data)
                bt_result = _get_backtest_result(force_refresh)
                return cached_data, bt_result

        # 3. 强制刷新 或 无缓存数据 → 阻塞等待刷新完成
        lock_acquired = pipeline_lock.acquire(timeout=5)
        if not lock_acquired:
            # 无法获取锁，返回缓存数据（如果有）
            if not cached_data:
                # 冷启动：无法获取锁且无缓存，尝试返回快速启动数据
                quick_data = _get_quick_start_data()
                if quick_data:
                    log.info("锁超时且缓存为空，返回快速启动数据")
                    bt_result = _get_backtest_result(force_refresh)
                    return quick_data, bt_result
                cached_data = _build_empty_pipeline_data()
                log.warning("锁超时且缓存为空，返回空数据结构")
            else:
                log.info("锁超时，返回缓存数据")
                # 统一合并：从 quick_start_data 补充缺失字段
                cached_data = _merge_pipeline_and_quick(cached_data)
            bt_result = _get_backtest_result(force_refresh)
            bt_result.setdefault("_bt_timestamp", server_cache.get("last_bt_update", 0))
            bt_result.setdefault("_bt_trigger_source", "scheduled")
            return cached_data, bt_result

        try:
            # 预热阶段处理：立即返回快速数据，后台异步刷新
            if not warmup_complete:
                existing_data = server_cache.get("pipeline_data")
                if (
                    existing_data
                    and isinstance(existing_data, dict)
                    and existing_data.get("hot8")
                ):
                    # 统一合并：从 quick_start_data 补充缺失字段
                    existing_data = _merge_pipeline_and_quick(existing_data)
                    log.info("系统正在预热中，使用已有缓存数据")
                    bt_result = _ensure_backtest_data(force_refresh, "scheduled")
                    return existing_data, bt_result

                # 无缓存且正在预热：使用快速启动数据（有缓存去重，只执行一次）
                quick_data = _get_quick_start_data()
                log.info("冷启动：获取快速启动数据")
                _trigger_background_refresh(False)
                bt_result = _ensure_backtest_data(force_refresh, "scheduled")
                if quick_data:
                    return quick_data, bt_result
                # 快速启动也失败时，继续阻塞等待

            # 阻塞式刷新（强制刷新或首次加载）
            pipeline_data = _do_refresh_pipeline_data(force_refresh)
            if pipeline_data:
                server_cache["pipeline_data"] = pipeline_data
                server_cache["last_update"] = current_time
                server_cache["warmup_complete"] = True
                trigger_type = "强制刷新" if force_refresh else "同步刷新"
                log.info(f"[{trigger_type}] 流水线数据已更新")

            trigger_source = "manual" if force_refresh else "scheduled"
            bt_result = _ensure_backtest_data(force_refresh, trigger_source)

            if not pipeline_data:
                pipeline_data = (
                    server_cache.get("pipeline_data") or _build_empty_pipeline_data()
                )
            return pipeline_data, bt_result
        finally:
            pipeline_lock.release()
    except Exception as e:
        log_system_error(e, "pipeline")
        cached_data = server_cache.get("pipeline_data")
        if not cached_data:
            cached_data = _build_empty_pipeline_data()
            log.warning(f"异常 fallback 且缓存为空: {e}")
        trigger_source = "manual" if force_refresh else "scheduled"
        bt_result = _ensure_backtest_data(force_refresh, trigger_source)
        return cached_data, bt_result


def get_pipeline_data_lite(force_refresh: bool = False) -> Dict[str, Any]:
    """获取流水线核心数据（不含回测），用于 /data?type=core 快速响应

    与 get_pipeline_data() 的区别：
    - 不调用 _ensure_backtest_data()，避免回测阻塞
    - 冷启动时立即返回缓存或空壳，不等待 pipeline_lock
    - 缓存过期时触发后台刷新但立即返回旧数据
    - force_refresh 采用 SWR 策略：先返回旧数据，后台异步刷新
    - 适用于首屏渲染等对延迟敏感的场景

    Args:
        force_refresh: 是否强制刷新

    Returns:
        流水线数据字典（不含回测数据）
    """
    try:
        reload_params()

        current_time = time.time()
        cache_validity = get_config_value("system.schedule.pipeline_cache", 60)
        last_update = server_cache.get("last_update", 0)
        cached_data = server_cache.get("pipeline_data")

        # force_refresh 时：采用 SWR 策略，先返回旧缓存，后台异步刷新
        # 避免前端等待完整 pipeline 执行（5-10分钟），导致页面长时间无响应
        if force_refresh:
            # 清除新闻缓存，确保后台刷新获取最新数据
            from modules.news_fetcher import NEWS_CACHE
            pipeline_cache_keys = ["pipeline:result:latest"]
            NEWS_CACHE.delete_keys(pipeline_cache_keys)
            NEWS_CACHE.clear()

            # 保留旧缓存数据用于立即返回（不清除 pipeline_data）
            if cached_data and isinstance(cached_data, dict):
                # 返回旧数据 + 触发后台异步刷新
                log.info("[lite] force_refresh: 返回旧缓存数据，触发后台异步刷新")
                _trigger_background_refresh(True)
                cached_data = _merge_pipeline_and_quick(dict(cached_data))
                return cached_data
            else:
                # 无缓存数据：尝试获取快速启动数据
                quick_data = server_cache.get("quick_start_data")
                if quick_data and isinstance(quick_data, dict):
                    log.info("[lite] force_refresh: 无缓存，返回快速启动数据，触发后台异步刷新")
                    _trigger_background_refresh(True)
                    quick_data["_quick_start_mode"] = True
                    return quick_data

                # 完全冷启动：短暂等待（最多3秒）让快速启动数据就绪
                for wait_attempt in range(6):
                    quick_data = server_cache.get("quick_start_data")
                    if quick_data and isinstance(quick_data, dict):
                        log.info(f"[lite] force_refresh: 等待{wait_attempt * 0.5}秒后获取到快速启动数据")
                        _trigger_background_refresh(True)
                        quick_data["_quick_start_mode"] = True
                        return quick_data
                    time.sleep(0.5)

                # 仍无数据，触发后台刷新并返回空壳
                log.warning("[lite] force_refresh: 无缓存且无快速启动数据，触发后台刷新")
                _trigger_background_refresh(True)
                return _build_empty_pipeline_data()

        # 非强制刷新：检查缓存有效性
        # current_time/cache_validity/last_update/cached_data 已在 force_refresh 之前声明

        # 1. 缓存有效 → 直接返回（最快路径）
        if (
            cached_data
            and isinstance(cached_data, dict)
            and last_update > 0
            and current_time - last_update < cache_validity
        ):
            return cached_data

        # 2. 缓存过期但有旧数据 → 检查新闻是否有效，无效则尝试快速启动数据
        if cached_data and isinstance(cached_data, dict):
            # 统一合并：从 quick_start_data 补充缺失字段
            merged_data = _merge_pipeline_and_quick(cached_data)
            if merged_data is not cached_data:
                # 合并发生了变更，说明从 quick_start 补充了数据
                _trigger_background_refresh(False)
                return merged_data

            cache_age = current_time - last_update if last_update > 0 else float("inf")
            log.info(f"[lite] 缓存已过期({cache_age:.0f}s)，返回旧数据并触发后台刷新")
            _trigger_background_refresh(False)
            return cached_data

        # 3. 无缓存数据 → 尝试快速启动数据或获取锁
        # 先检查快速启动数据缓存（_get_quick_start_data 有去重，只执行一次网络请求）
        quick_data = server_cache.get("quick_start_data")
        if quick_data and isinstance(quick_data, dict):
            # 检查是否有正在进行的刷新，如果有则直接返回快速启动数据
            # 不等待，避免阻塞（后台刷新会更新缓存，下次请求会获取新数据）
            if _refresh_in_progress:
                log.info("[lite] 检测到后台刷新正在进行，立即返回快速启动数据")
            else:
                # 触发后台刷新
                _trigger_background_refresh(False)

            # 标记为预热中（quick_start 模式）
            quick_data["_quick_start_mode"] = True
            return quick_data

        # warmup 还未完成，立即返回空壳并触发后台刷新
        # 优化：不再等待或阻塞同步获取，冷启动时保证 <1s 响应
        # 前端收到空壳后会自动轮询刷新
        log.info("[lite] warmup未完成，立即返回空壳并触发后台刷新")
        empty = _build_empty_pipeline_data()
        empty["_quick_start_mode"] = True
        empty["_warming_up"] = True
        empty["_message"] = "系统正在启动中，数据将很快更新"
        _trigger_background_refresh(False)
        return empty

    except Exception as e:
        log_system_error(e, "pipeline_lite")
        return server_cache.get("pipeline_data") or _build_empty_pipeline_data()


def _get_quick_start_data() -> Dict[str, Any]:
    """获取快速启动数据，用于系统刚启动时的快速响应

    使用缓存避免重复执行：首次调用执行网络请求，后续调用直接返回缓存结果。

    Returns:
        包含基础数据的字典
    """
    # 去重：如果已有快速启动数据缓存，直接返回
    # 快速路径：无锁检查缓存（GIL 保障 dict 单键读取原子性）
    cached = server_cache.get("quick_start_data")
    if cached and isinstance(cached, dict):
        log.info("快速启动数据已有缓存，直接返回")
        return cached

    # 慢速路径：加锁防止惊群（多线程并发请求只执行一次网络请求）
    with _quick_start_lock:
        # 双重检查：获取锁后再次检查缓存
        cached = server_cache.get("quick_start_data")
        if cached and isinstance(cached, dict):
            log.info("快速启动数据已有缓存（双重检查），直接返回")
            return cached

        try:
            from modules.sector_manager import load_seed_pools, load_seed_pool_names
            from modules.quote_fetcher import fetch_quotes
            from modules.news_fetcher import fetch_all_news
            from modules.server.data_formatter import format_news_data

            # 加载种子池数据
            pools = load_seed_pools()
            pool_symbols = []
            for stocks in pools.values():
                pool_symbols.extend(stocks)

            # 只取前20只股票进行快速行情获取（减少到20只，加快响应）
            quick_symbols = pool_symbols[:20]
            log.info(f"快速启动模式：获取{len(quick_symbols)}只股票的行情数据")

            # 获取行情数据（带超时保护，最多10秒）
            # 注意：不能使用 with 语句，因为 __exit__ 会调用 shutdown(wait=True)，
            # 导致超时后仍阻塞等待线程完成，使超时保护失效
            import concurrent.futures

            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            future = executor.submit(fetch_quotes, quick_symbols)
            try:
                quotes = future.result(timeout=10)
                log.info(f"快速启动模式：成功获取{len(quotes)}只股票的行情数据")
            except concurrent.futures.TimeoutError:
                log.warning("快速启动模式：获取行情数据超时（10秒），使用空数据")
                quotes = {}
            finally:
                executor.shutdown(wait=False)

            # 加载股票名称
            seed_names = load_seed_pool_names()

            # 构建基础数据结构（先不含新闻，新闻后台加载）
            quick_data: Dict[str, Any] = {
                "hot8": [],
                "picks": [],
                "quotes": quotes,
                "news": {"top_news": [], "recent_news": [], "all_news": []},
                "sec_sum": {},
                "sector_heat": {},
                "news_stats": {},
                "_quick_start": True,
                "_message": "系统正在预热中，数据将很快更新",
            }

            # 构建热门股票列表（按涨幅排序，取前8只）
            hot8_list: List[Dict[str, Any]] = []
            for symbol, quote_data in quotes.items():
                if quote_data and isinstance(quote_data, dict):
                    pct = quote_data.get("pct", quote_data.get("pct_change", 0))
                    name = seed_names.get(symbol, symbol)
                    if isinstance(quotes, dict) and symbol in quotes:
                        quote_name = quotes[symbol].get("name", name)
                        if quote_name and quote_name != symbol:
                            name = quote_name
                    heat = int(abs(pct) * 10) if pct else 0
                    hot8_list.append(
                        {
                            "symbol": symbol,
                            "name": name,
                            "heat": heat,
                            "pct_change": pct if pct else 0,
                            "supplemental": True,
                        }
                    )
            hot8_list.sort(key=lambda x: abs(x.get("pct_change", 0)), reverse=True)
            quick_data["hot8"] = hot8_list[:8]

            # 构建精选股票列表（按涨幅排序）
            picks_list: List[Dict[str, Any]] = []

            # 构建简单的精选股票列表
            for symbol, quote_data in quotes.items():
                if quote_data and isinstance(quote_data, dict):
                    name = seed_names.get(symbol, symbol)
                    quick_pick = {
                        "symbol": symbol,
                        "name": name,
                        "price": quote_data.get("price", 0),
                        "pct_change": quote_data.get("pct", 0),
                        "score": {
                            "total": 0,
                            "sentiment": 0,
                            "sector": 0,
                            "leader": 0,
                            "fund": 0,
                            "vp": 0,
                            "seal": 0,
                        },
                        "_quick_start": True,
                    }
                    picks_list.append(quick_pick)

            # 按涨幅排序
            picks_list.sort(key=lambda x: x.get("pct_change", 0), reverse=True)
            # 限制数量
            quick_data["picks"] = picks_list[:20]

            # 同步计算板块热度（基于种子池行情数据，无需等新闻）
            try:
                sector_pcts: Dict[str, List[float]] = {}
                for sector_name, stock_codes in pools.items():
                    for code in stock_codes:
                        # 规范化股票代码（加sh/sz前缀匹配quotes键）
                        if code.startswith("6") or code.startswith("9"):
                            norm_code = f"sh{code}"
                        elif code.startswith("0") or code.startswith("3"):
                            norm_code = f"sz{code}"
                        else:
                            norm_code = code
                        q = quotes.get(norm_code)
                        if q and isinstance(q, dict):
                            pct = q.get("pct", q.get("pct_change", 0))
                            if pct is not None:
                                sector_pcts.setdefault(sector_name, []).append(abs(pct))
                if sector_pcts:
                    # 构建与 aggregate_sector_heat 兼容的 sec_sum
                    quick_sec_sum = {}
                    for s_name, pcts in sector_pcts.items():
                        avg_pct = sum(pcts) / len(pcts) if pcts else 0
                        quick_sec_sum[s_name] = {
                            "count": len(pcts),
                            "avg_pct": round(avg_pct, 2),
                        }
                    quick_data["sec_sum"] = quick_sec_sum
                    quick_data["sector_heat"] = aggregate_sector_heat(quick_sec_sum)
                    log.info(
                        f"快速启动模式：同步计算板块热度完成，{len(quick_sec_sum)}个板块"
                    )
            except Exception as sec_err:
                log.warning(f"快速启动模式：同步板块热度计算失败: {sec_err}")

            # 缓存基本数据（行情+股票），立即返回让前端渲染
            # 先缓存不含新闻的版本，前端可以立即显示热门股票和精选
            # 添加 TTL 防止长期保留过时数据
            server_cache.set("quick_start_data", quick_data, ttl=QUICK_START_TTL)

            # 后台异步加载新闻数据（不阻塞快速启动）
            # 重要：使用 copy() 创建新字典，避免后台线程修改已返回的引用
            # 这样前端拿到的 quick_data 在后台线程更新时不会被影响
            quick_data_ref = quick_data  # 保留引用用于返回

            def _load_news_async() -> None:
                """分阶段加载新闻：先1页快讯快速展示，再3页完整数据"""
                # === 阶段1：快速获取1页新闻（~20条），立即缓存供前端展示 ===
                try:
                    log.info("快速启动模式[阶段1]：获取1页快讯...")
                    quick_news_items = fetch_all_news(pages=1, merge_sources=True)
                    if quick_news_items:
                        quick_formatted = format_news_data(quick_news_items)
                        quick_updated = dict(quick_data_ref)
                        quick_updated["news"] = quick_formatted
                        quick_updated["news_stats"] = {
                            "total_fetched": len(quick_formatted.get("all_news", [])),
                            "after_dedup": len(quick_formatted.get("all_news", [])),
                            "after_24h_filter": len(quick_formatted.get("all_news", [])),
                            "after_stock_filter": len(quick_formatted.get("all_news", [])),
                            "avg_score_all": 0.0,
                            "avg_score_picks": 0.0,
                            "_partial": True,  # 标记为部分数据
                        }
                        server_cache.set("quick_start_data", quick_updated, ttl=QUICK_START_TTL)
                        log.info(
                            f"快速启动模式[阶段1]：快讯已缓存，{len(quick_news_items)}条新闻"
                        )
                except Exception as e:
                    log.warning(f"快速启动模式[阶段1]：快讯获取失败: {e}")

                # === 阶段2：获取完整3页新闻 + 板块热度分析 ===
                max_retries = 1
                retry_delay = 5

                for attempt in range(max_retries + 1):
                    try:
                        log.info(
                            f"快速启动模式[阶段2]：获取完整新闻数据... (尝试 {attempt + 1}/{max_retries + 1})"
                        )
                        news_items = fetch_all_news(pages=3)
                        formatted_news = format_news_data(news_items)
                        all_news = formatted_news.get("all_news", [])

                        if not all_news and attempt < max_retries:
                            log.warning(
                                f"快速启动模式[阶段2]：获取新闻为空，将在 {retry_delay} 秒后重试"
                            )
                            time.sleep(retry_delay)
                            continue

                        updated_data = dict(quick_data_ref)
                        updated_data["news"] = formatted_news
                        updated_data["news_stats"] = {
                            "total_fetched": len(all_news) if all_news else 0,
                            "after_dedup": len(all_news) if all_news else 0,
                            "after_24h_filter": len(all_news) if all_news else 0,
                            "after_stock_filter": len(all_news) if all_news else 0,
                            "avg_score_all": 0.0,
                            "avg_score_picks": 0.0,
                        }

                        # 从新闻计算板块热度
                        try:
                            from modules.scorer.extraction import analyze_news

                            _, sec_sum, _ = analyze_news(news_items)
                            if sec_sum and isinstance(sec_sum, dict):
                                updated_data["sec_sum"] = sec_sum
                                updated_data["sector_heat"] = aggregate_sector_heat(
                                    sec_sum
                                )
                                log.info(
                                    f"快速启动模式[阶段2]：板块热度计算完成，{len(sec_sum)}个板块"
                                )
                        except Exception as sec_err:
                            log.warning(f"快速启动模式[阶段2]：板块热度计算失败 {sec_err}")

                        server_cache.set(
                            "quick_start_data", updated_data, ttl=QUICK_START_TTL
                        )
                        log.info(
                            f"快速启动模式[阶段2]：完整数据已缓存，新闻{len(news_items)}条"
                        )
                        return
                    except Exception as e:
                        log.warning(
                            f"快速启动模式[阶段2]：后台获取新闻失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}"
                        )
                        if attempt < max_retries:
                            log.info(f"将在 {retry_delay} 秒后重试...")
                            time.sleep(retry_delay)
                        else:
                            log.error("快速启动模式[阶段2]：新闻加载重试次数用尽，不再重试")

            import threading

            news_thread = threading.Thread(target=_load_news_async, daemon=True)
            news_thread.start()

            log.info(
                f"快速启动模式：生成{len(quick_data_ref['picks'])}只精选股票，{len(quick_data_ref['hot8'])}只热门股票（新闻后台加载中）"
            )
            return quick_data_ref
        except Exception as e:
            log.error(f"快速启动数据生成失败: {e}")
            return {}



