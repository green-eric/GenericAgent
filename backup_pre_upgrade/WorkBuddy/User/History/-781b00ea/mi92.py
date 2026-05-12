"""
API客户端 - 连接东方财富金融数据API
"""

import requests
import json
import time
from typing import Dict, List, Optional
import logging
from config import EASTMONEY_CONFIG

class EastMoneyAPIClient:
    """东方财富API客户端"""

    def __init__(self):
        self.base_url = EASTMONEY_CONFIG['base_url']
        self.api_key = EASTMONEY_CONFIG['api_key']
        self.timeout = EASTMONEY_CONFIG['timeout']
        self.retry_times = EASTMONEY_CONFIG['retry_times']
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
        
        # 设置默认请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Origin': 'http://quote.eastmoney.com',
            'Referer': 'http://quote.eastmoney.com/'
        })

    def _make_request(self,
                     endpoint: str,
                     params: Dict = None,
                     method: str = 'GET') -> Optional[Dict]:
        """
        发送HTTP请求，带重试机制

        Args:
            endpoint: API端点路径
            params: 请求参数
            method: HTTP方法

        Returns:
            JSON响应数据或None
        """
        url = f"{self.base_url}{endpoint}"

        for attempt in range(self.retry_times):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    # 检查响应内容是否为JSON
                    try:
                        return response.json()
                    except json.JSONDecodeError:
                        # 如果不是JSON，返回文本内容
                        return {'content': response.text}
                else:
                    self.logger.warning(f"API请求失败: {response.status_code}, URL: {url}")

            except requests.exceptions.RequestException as e:
                self.logger.error(f"请求异常 (尝试 {attempt + 1}/{self.retry_times}): {str(e)}")
                if attempt < self.retry_times - 1:
                    time.sleep(2 ** attempt)  # 指数退避

        return None

    def get_stock_list(self, market: str = 'A股') -> List[Dict]:
        """
        获取股票列表

        Args:
            market: 市场类型 ('A股', '港股', '美股')

        Returns:
            股票列表
        """
        try:
            # 这里需要根据东方财富API的具体接口进行调整
            # 示例参数，实际使用时需要查阅官方文档
            params = {
                'pageIndex': 1,
                'pageSize': 1000,
                'sortField': 'total_mv',
                'sortType': 'desc'
            }

            result = self._make_request('/emapigateway/quote/getstocklist', params)
            return result.get('data', []) if result else []

        except Exception as e:
            self.logger.error(f"获取股票列表失败: {str(e)}")
            return []

    def get_financial_report(self,
                           stock_code: str,
                           report_year: int = 2025,
                           report_type: str = '年报') -> Optional[Dict]:
        """
        获取财务报表示例

        Args:
            stock_code: 股票代码
            report_year: 报告年份
            report_type: 报告类型 ('年报', '季报')

        Returns:
            财务报告数据
        """
        try:
            # 这里需要根据实际的API接口进行调整
            params = {
                'ts_code': f'{stock_code}.SZ' if '0' <= stock_code[0] <= '9' else f'{stock_code}.SH',
                'ann_date': f'{report_year}',
                'type': 'L'
            }

            result = self._make_request('/emapigateway/finance/report', params)
            return result

        except Exception as e:
            self.logger.error(f"获取财务报告失败: {str(e)}")
            return None

    def get_stock_basic_info(self, stock_code: str) -> Optional[Dict]:
        """
        获取股票基本信息

        Args:
            stock_code: 股票代码

        Returns:
            股票基本信息
        """
        try:
            params = {
                'ts_code': stock_code
            }

            result = self._make_request('/emapigateway/quote/getbasicinfo', params)
            return result

        except Exception as e:
            self.logger.error(f"获取股票基本信息失败: {str(e)}")
            return None

    def batch_get_financial_data(self,
                               stock_codes: List[str],
                               report_year: int = 2025) -> List[Dict]:
        """
        批量获取财务数据

        Args:
            stock_codes: 股票代码列表
            report_year: 报告年份

        Returns:
            财务数据列表
        """
        financial_data = []
        total_stocks = len(stock_codes)

        for i, code in enumerate(stock_codes):
            try:
                self.logger.info(f"正在处理 {i+1}/{total_stocks}: {code}")

                # 获取股票基本信息
                basic_info = self.get_stock_basic_info(code)
                if not basic_info:
                    continue

                # 获取财务报告
                report = self.get_financial_report(code, report_year)
                if report:
                    # 合并基本信息和财务数据
                    combined_data = {
                        'stock_code': code,
                        'stock_name': basic_info.get('name', ''),
                        **report
                    }
                    financial_data.append(combined_data)

                # 避免请求过于频繁
                time.sleep(0.1)

            except Exception as e:
                self.logger.error(f"处理股票 {code} 时出错: {str(e)}")
                continue

        return financial_data