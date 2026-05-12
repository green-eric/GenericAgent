#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 数据库管理层 - 财务数据持久化
 存储：财报数据、行情数据、评分结果
================================================================================
"""
import sqlite3
import pandas as pd
import json
from datetime import datetime
from typing import Optional, Dict


class StockDatabase:
    """股票财务数据库"""
    
    def __init__(self, db_path: str = 'stock_data.db'):
        self.db_path = db_path
        self._init_tables()
    
    def _init_tables(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 财务报告数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS financials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                report_date TEXT NOT NULL,
                ann_date TEXT,
                report_type TEXT,
                revenue REAL,
                oper_cost REAL,
                oper_profit REAL,
                net_profit_parent REAL,
                net_profit_ex REAL,
                fin_expense REAL,
                total_assets REAL,
                total_liab REAL,
                total_equity REAL,
                equity_parent REAL,
                current_assets REAL,
                current_liab REAL,
                ocf REAL,
                capex REAL,
                cash_from_sales REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, report_date)
            )
        ''')
        
        # 行情数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                open_price REAL,
                high_price REAL,
                low_price REAL,
                close_price REAL,
                volume REAL,
                total_mv REAL,
                pe_ttm REAL,
                pb REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, trade_date)
            )
        ''')
        
        # 评分结果表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                eval_date TEXT NOT NULL,
                total_score REAL,
                growth REAL,
                profitability REAL,
                cash_flow REAL,
                leverage REAL,
                valuation REAL,
                roe_ttm REAL,
                gross_margin_ttm REAL,
                net_margin_ttm REAL,
                q_revenue_yoy REAL,
                q_net_profit_yoy REAL,
                asset_liability_ratio REAL,
                de_ratio REAL,
                current_ratio REAL,
                net_profit_ratio REAL,
                pe_ttm REAL,
                total_mv REAL,
                rating TEXT,
                veto TEXT,
                veto_reason TEXT,
                raw_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, eval_date)
            )
        ''')
        
        # 股票信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks (
                symbol TEXT PRIMARY KEY,
                name TEXT,
                industry TEXT,
                list_date TEXT,
                market TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_financials_symbol ON financials(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_financials_date ON financials(report_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_quotes_symbol ON quotes(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scores_symbol ON scores(symbol)')
        
        conn.commit()
        conn.close()
    
    def save_financials(self, symbol: str, df: pd.DataFrame):
        """保存财务数据（事务批量写入）"""
        if df.empty:
            return 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        rows = []
        for _, row in df.iterrows():
            rows.append((
                symbol,
                str(row.get('report_date', '')),
                str(row.get('ann_date', '')),
                float(row.get('revenue', 0) or 0),
                float(row.get('oper_cost', 0) or 0),
                float(row.get('oper_profit', 0) or 0),
                float(row.get('net_profit_parent', 0) or 0),
                float(row.get('net_profit_ex', 0) or 0),
                float(row.get('fin_expense', 0) or 0),
                float(row.get('total_assets', 0) or 0),
                float(row.get('total_liab', 0) or 0),
                float(row.get('total_equity', 0) or 0),
                float(row.get('equity_parent', 0) or 0),
                float(row.get('current_assets', 0) or 0),
                float(row.get('current_liab', 0) or 0),
                float(row.get('ocf', 0) or 0),
                float(row.get('capex', 0) or 0),
                float(row.get('cash_from_sales', 0) or 0),
                now
            ))
        
        cursor.executemany('''
            INSERT OR REPLACE INTO financials 
            (symbol, report_date, ann_date, revenue, oper_cost, oper_profit,
             net_profit_parent, net_profit_ex, fin_expense,
             total_assets, total_liab, total_equity, equity_parent,
             current_assets, current_liab, ocf, capex, cash_from_sales,
             updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', rows)
        
        conn.commit()
        conn.close()
        return len(rows)
    
    def get_financials(self, symbol: str, max_date: str = None) -> pd.DataFrame:
        """获取财务数据"""
        conn = sqlite3.connect(self.db_path)
        
        if max_date:
            query = '''
                SELECT * FROM financials 
                WHERE symbol = ? AND report_date <= ?
                ORDER BY report_date
            '''
            df = pd.read_sql(query, conn, params=(symbol, max_date))
        else:
            query = 'SELECT * FROM financials WHERE symbol = ? ORDER BY report_date'
            df = pd.read_sql(query, conn, params=(symbol,))
        
        conn.close()
        return df
    
    def get_latest_financials(self, symbol: str, min_quarters: int = 4) -> Optional[pd.DataFrame]:
        """获取最新财务数据（至少指定季度数）"""
        conn = sqlite3.connect(self.db_path)
        query = '''
            SELECT * FROM financials 
            WHERE symbol = ?
            ORDER BY report_date DESC
            LIMIT ?
        '''
        df = pd.read_sql(query, conn, params=(symbol, min_quarters * 2))  # 多取一些
        conn.close()
        return df
    
    def save_score(self, symbol: str, eval_date: str, score_data: Dict):
        """保存评分结果"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 提取评分指标
        scores = score_data.get('scores', {})
        
        cursor.execute('''
            INSERT OR REPLACE INTO scores
            (symbol, eval_date, total_score, growth, profitability, cash_flow,
             leverage, valuation, roe_ttm, gross_margin_ttm, net_margin_ttm,
             q_revenue_yoy, q_net_profit_yoy, asset_liability_ratio, de_ratio,
             current_ratio, net_profit_ratio, pe_ttm, total_mv, rating, veto, veto_reason, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            symbol, eval_date,
            score_data.get('total_score', 0),
            scores.get('growth', 0),
            scores.get('profitability', 0),
            scores.get('cash_flow', 0),
            scores.get('leverage', 0),
            scores.get('valuation', 0),
            score_data.get('roe_ttm'),
            score_data.get('gross_margin_ttm'),
            score_data.get('net_margin_ttm'),
            score_data.get('q_revenue_yoy'),
            score_data.get('q_net_profit_yoy'),
            score_data.get('asset_liability_ratio'),
            score_data.get('de_ratio'),
            score_data.get('current_ratio'),
            score_data.get('net_profit_ratio'),
            score_data.get('pe_ttm'),
            score_data.get('total_mv'),
            score_data.get('rating'),
            score_data.get('veto'),
            score_data.get('veto_reason'),
            json.dumps(score_data, ensure_ascii=False, default=str)
        ))
        
        conn.commit()
        conn.close()
    
    def get_scores(self, eval_date: str = None, min_score: float = 0) -> pd.DataFrame:
        """获取评分结果"""
        conn = sqlite3.connect(self.db_path)
        
        if eval_date:
            query = '''
                SELECT * FROM scores 
                WHERE eval_date = ? AND total_score >= ?
                ORDER BY total_score DESC
            '''
            df = pd.read_sql(query, conn, params=(eval_date, min_score))
        else:
            query = 'SELECT * FROM scores ORDER BY total_score DESC'
            df = pd.read_sql(query, conn)
        
        conn.close()
        return df
    
    def save_stock_info(self, symbol: str, name: str = None, industry: str = None):
        """保存股票基本信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO stocks (symbol, name, industry, updated_at)
            VALUES (?, ?, ?, ?)
        ''', (symbol, name, industry, now))
        
        conn.commit()
        conn.close()
    
    def save_stock_info_batch(self, info_list: list):
        """批量保存股票信息 [(symbol, name, industry), ...]"""
        if not info_list:
            return 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.executemany('''
            INSERT OR REPLACE INTO stocks (symbol, name, industry, updated_at)
            VALUES (?, ?, ?, ?)
        ''', [(s, n, i, now) for s, n, i in info_list])
        
        conn.commit()
        conn.close()
        return len(info_list)
    
    def save_quote(self, symbol: str, quote: dict, trade_date: str = None):
        """保存行情数据"""
        if not trade_date:
            trade_date = datetime.now().strftime('%Y-%m-%d')
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO quotes
            (symbol, trade_date, total_mv, pe_ttm)
            VALUES (?, ?, ?, ?)
        ''', (
            symbol,
            trade_date,
            float(quote.get('total_mv', 0) or 0),
            float(quote.get('pe_ttm', 0) or 0)
        ))
        
        conn.commit()
        conn.close()
    
    def get_quote(self, symbol: str) -> dict:
        """获取最新行情数据"""
        conn = sqlite3.connect(self.db_path)
        query = '''
            SELECT total_mv, pe_ttm FROM quotes
            WHERE symbol = ? ORDER BY trade_date DESC LIMIT 1
        '''
        df = pd.read_sql(query, conn, params=(symbol,))
        conn.close()
        
        if not df.empty:
            return {
                'total_mv': df.iloc[0].get('total_mv', 0) or 0,
                'pe_ttm': df.iloc[0].get('pe_ttm', 0) or 0
            }
        return {'total_mv': 0, 'pe_ttm': 0}
    
    def get_stock_info(self, symbol: str = None) -> dict:
        """获取股票信息"""
        conn = sqlite3.connect(self.db_path)
        
        if symbol:
            query = 'SELECT * FROM stocks WHERE symbol = ?'
            df = pd.read_sql(query, conn, params=(symbol,))
        else:
            query = 'SELECT * FROM stocks'
            df = pd.read_sql(query, conn)
        
        conn.close()
        if symbol:
            return df.iloc[0].to_dict() if not df.empty else {}
        return df.to_dict('records') if not df.empty else []
    
    def get_symbols_with_financials(self, min_quarters: int = 4) -> list:
        """获取有足够财务数据的股票代码列表"""
        conn = sqlite3.connect(self.db_path)
        query = '''
            SELECT symbol, COUNT(*) as cnt
            FROM financials
            GROUP BY symbol
            HAVING cnt >= ?
        '''
        df = pd.read_sql(query, conn, params=(min_quarters,))
        conn.close()
        return df['symbol'].tolist()
    
    def get_db_stats(self) -> Dict:
        """获取数据库统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM financials')
        fin_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT symbol) FROM financials')
        fin_symbols = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM scores')
        score_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM stocks')
        stock_count = cursor.fetchone()[0]
        
        import os
        db_size = os.path.getsize(self.db_path) / 1024 / 1024 if os.path.exists(self.db_path) else 0
        
        conn.close()
        
        return {
            'financials': fin_count,
            'symbols_with_fin': fin_symbols,
            'scores': score_count,
            'stocks': stock_count,
            'db_size_mb': round(db_size, 2)
        }
    
    def clear_old_data(self, days: int = 90):
        """清理旧数据"""
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM financials WHERE updated_at < ?', (cutoff,))
        fin_del = cursor.rowcount
        
        cursor.execute('DELETE FROM quotes WHERE created_at < ?', (cutoff,))
        quote_del = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return {'financials': fin_del, 'quotes': quote_del}