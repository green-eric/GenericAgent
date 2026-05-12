# -*- coding: utf-8 -*-
def _extract_quarterly_block(text: str) -> Tuple[str, str]:
    """提取最新单季报段落及日期"""
    pattern = r"统计截止日期为(\d{4}(?:0331|0630|0930))的Q[123]单季报"
    matches = list(re.finditer(pattern, text))
    return "", ""
