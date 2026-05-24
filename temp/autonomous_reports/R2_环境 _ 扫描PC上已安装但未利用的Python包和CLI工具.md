# R02 - 扫描本地Python包和未利用的CLI工具

> 自主行动产出 | 2026-05-04

## 摘要

扫描了用户PC上所有pip安装的Python包和PATH中的CLI工具，筛选出**15个高价值但记忆中未记录**的工具，记录用法要点。

---

## 一、高价值CLI工具（已验证可用）

### 1. ruff 0.15.8 — 极速Python linter+formatter
- **用途**: 替代pylint/flake8/black/isort，一个工具搞定所有
- **用法**: `ruff check .` (检查) / `ruff format .` (格式化) / `ruff check --fix .` (自动修复)
- **优势**: 比pylint快10-100倍，兼容pyproject.toml配置
- **记忆状态**: ❌ 未记录

### 2. uv 0.11.2 — 极速Python包管理器
- **用途**: 替代pip/pipx/venv，Rust编写，速度快5-100倍
- **用法**: `uv pip install xxx` / `uv venv` / `uvx <tool>` (直接运行工具无需安装)
- **优势**: 兼容pip语法，支持lock文件
- **记忆状态**: ❌ 未记录

### 3. tig 2.6.0 — Git终端UI
- **用途**: git的ncurses终端界面，浏览log/diff/staging
- **用法**: 直接输入 `tig` 进入交互界面，`tig log` / `tig blame`
- **记忆状态**: ❌ 未记录

### 4. ngrok 3.37.1 — 内网穿透
- **用途**: 将本地端口暴露到公网，生成临时URL
- **用法**: `ngrok http 8080` / `ngrok tcp 22`
- **注意**: 需要authtoken才能使用
- **记忆状态**: ❌ 未记录

### 5. Docker 29.4.0 — 容器引擎
- **用途**: 容器化部署、隔离环境、快速搭建服务
- **用法**: `docker run` / `docker compose up` / `docker ps`
- **记忆状态**: ❌ 未记录（仅有sc/net等系统工具记录）

### 6. psql (PostgreSQL 18.3) — PostgreSQL客户端
- **用途**: 连接PostgreSQL数据库
- **用法**: `psql -h host -U user -d dbname`
- **记忆状态**: ❌ 未记录

### 7. redis-cli — Redis客户端
- **用途**: 连接Redis数据库
- **用法**: `redis-cli -h host -p 6379`
- **记忆状态**: ❌ 未记录

### 8. pre-commit 4.5.1 — Git提交前检查框架
- **用途**: 配置git hook，在commit前自动运行linter/测试
- **用法**: `pre-commit install` / `pre-commit run --all-files`
- **记忆状态**: ❌ 未记录

### 9. yt-dlp 2026.02.04 — 视频下载器
- **用途**: 下载YouTube/B站/抖音等平台的视频/音频
- **用法**: `yt-dlp URL` / `yt-dlp -x --audio-format mp3 URL` (仅音频)
- **记忆状态**: ✅ L1有提及但未详细说明

### 10. watchdog 6.0.0 — 文件系统监控（Python包）
- **用途**: 监控目录文件变化，触发回调
- **用法**: `watchmedo shell-command --patterns="*.py" --recursive --command='echo ${watch_src_path}' -- .`
- **记忆状态**: ❌ 未记录

### 11. streamlit 1.50.0 — 数据应用框架（Python包）
- **用途**: 快速构建数据可视化Web应用
- **用法**: `streamlit run app.py`
- **记忆状态**: ❌ 未记录

### 12. polars 1.40.1 — 高性能DataFrame库（Python包）
- **用途**: 替代pandas，Rust编写，速度快5-50倍
- **用法**: `import polars as pl; df = pl.read_csv("file.csv")`
- **优势**: 惰性求值(expressions/lazy API)，内存效率高
- **记忆状态**: ❌ 未记录

### 13. ultralytics (Python包) — YOLO目标检测
- **用途**: YOLOv8/v9/v10模型训练和推理
- **用法**: `from ultralytics import YOLO; model = YOLO("yolov8n.pt"); model.predict("image.jpg")`
- **记忆状态**: ❌ 未记录

### 14. cryptography 47.0.0 — 加密库（Python包）
- **用途**: AES/RSA/HMAC/证书等加密操作
- **用法**: `from cryptography.fernet import Fernet`
- **记忆状态**: ❌ 未记录

### 15. APScheduler 3.11.2 — 定时任务调度（Python包）
- **用途**: Python定时任务，类似cron但更灵活
- **用法**: 支持interval/cron/date三种触发器，可持久化到数据库
- **记忆状态**: ❌ 未记录

---

## 二、值得关注但未深入的工具

| 工具 | 说明 |
|------|------|
| dingtalk-stream 0.24.3 | 钉钉机器人SDK |
| discord.py 2.7.1 | Discord机器人SDK |
| lark-oapi 1.5.5 | 飞书开放平台SDK |
| langfuse 4.5.1 | LLM应用监控/opentelemetry |
| opentelemetry-api 1.41.1 | 分布式追踪 |
| PyPDF2 3.0.1 | PDF读写 |
| pytesseract 0.3.13 | OCR（需要tesseract引擎） |
| openpyxl 3.1.5 | Excel读写 |
| xlrd 2.0.2 | Excel读取（旧版.xls） |
| PyYAML 6.0.3 | YAML解析 |
| python-dotenv 1.1.1 | .env环境变量加载 |
| tenacity 9.1.2 | 重试装饰器 |
| tiktoken 0.12.0 | OpenAI tokenizer |
| tabulate 0.9.0 | 表格格式化输出 |
| Pygments 2.19.0 | 代码高亮 |
| shapely 2.1.2 | 几何图形处理 |

---

## 三、用户技术画像推断

1. **AI/ML方向**: ultralytics/YOLO、onnxruntime、paddleocr、rapidocr、numpy、scipy、matplotlib、torchrun、polars
2. **Web开发**: streamlit、uvicorn、fastapi(通过Werkzeug/Jinja2推断)、aiohttp、requests、httpx
3. **DevOps**: Docker、ngrok、pre-commit、APScheduler、watchdog、opentelemetry
4. **数据**: polars、pandas、openpyxl、xlrd、altair、matplotlib、streamlit
5. **IM集成**: dingtalk-stream、discord.py、lark-oapi（钉钉/Discord/飞书机器人）
6. **效率工具**: ruff、uv、tig、yt-dlp

---

## 四、建议

1. **立即可用**: ruff替代pylint、uv替代pip、tig替代git log
2. **按需启用**: ngrok(需要token)、Docker(需要daemon)、psql/redis-cli(需要服务)
3. **值得学习**: polars(比pandas快很多)、streamlit(快速搭建数据应用)
