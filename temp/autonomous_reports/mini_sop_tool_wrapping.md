# Mini-SOP 2: 工具封装模式

## 触发
需要把重复操作/复合逻辑封装为可复用工具时

## 流程
1. **需求分析** — 确定输入/输出/边界条件/错误处理策略
2. **设计接口** — 统一返回格式，统一命名规范（动词_名词）
3. **分步实现** — 核心逻辑 → 边界处理 → 异常捕获 → 格式化输出
4. **测试验证** — 至少测3种场景：正常/边界/异常
5. **写入产出** — `./xxx_tool.py` 或 `./xxx.py`
6. **更新记忆** — 新工具名写入 `global_mem_insight.txt` L1索引

## 模板结构
```python
"""xxx_tool.py — 一句话描述"""
import ...
def xxx(param, max_results=10):
    try:
        return [{"type": "...", ...}]
    except Exception:
        return []
def format_results(results):
    ...
if __name__ == "__main__":
    import argparse
    ...
```

## 关键原则
- 每个函数返回统一格式（list of dict）
- 异常必须捕获并返回空列表，不向上抛
- 必须有 `format_results` 配套
- 必须有 `if __name__ == "__main__"` CLI入口
