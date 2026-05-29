# Windows系统工具链扫描报告

> 2026-05-20 | 注册表软件: 51 | 运行服务: 104 | PATH工具: 951

## 📦 已安装软件分类

### 开发工具 (24)

  - Git
  - Microsoft Visual C++ 2022 X64 Additional Runtime - 14.50.35719
  - Microsoft Visual C++ 2022 X64 Minimum Runtime - 14.50.35719
  - Microsoft Visual C++ 2022 X86 Additional Runtime - 14.50.35719
  - Microsoft Visual C++ 2022 X86 Minimum Runtime - 14.50.35719
  - Microsoft Visual C++ v14 Redistributable (x64) - 14.50.35719
  - Microsoft Visual C++ v14 Redistributable (x86) - 14.50.35719
  - Node.js
  - Notepad++ (64-bit x64)
  - PostgreSQL 17
  - PostgreSQL 18
  - Python 3.12.10 (64-bit)
  - Python 3.12.10 Add to Path (64-bit)
  - Python 3.12.10 Core Interpreter (64-bit)
  - Python 3.12.10 Development Libraries (64-bit)
  - Python 3.12.10 Documentation (64-bit)
  - Python 3.12.10 Executables (64-bit)
  - Python 3.12.10 Standard Library (64-bit)
  - Python 3.12.10 Tcl/Tk Support (64-bit)
  - Python 3.12.10 Test Suite (64-bit)
  - Python 3.12.10 pip Bootstrap (64-bit)
  - Python 3.14.5
  - Python Launcher
  - Python Launcher
### 浏览器 (5)

  - Brave
  - Google Chrome
  - Microsoft Edge WebView2 Runtime
  - Microsoft Edge
  - Mozilla Firefox (x64 zh-CN)
### 通讯 (2)

  - CC Switch
  - Clash Verge
### 办公 (5)

  - Microsoft Office Home and Student 2019 - zh-cn
  - Microsoft OneDrive
  - Office 16 Click-to-Run Extensibility Component
  - Office 16 Click-to-Run Localization Component
  - 微软OfficePLUS
### 系统工具 (2)

  - 7-Zip 26.00 (x64)
  - Everything 1.4.1.1032 (x64)
### AI/ML (1)

  - LM Studio 0.4.13+1
### 其他 (12)

  - Lenovo Service Bridge
  - Microsoft Update Health Tools
  - Mozilla Maintenance Service
  - Redis on Windows
  - Trae CN (User)
  - Update for Windows 10 for x64-based Systems (KB5001716)
  - WinRAR 7.22 (64-位)
  - Windows Subsystem for Linux
  - WorkBuddy 4.22.14
  - 国元领航金融终端
  - 微信
  - 微信输入法

## 🔍 未利用的高价值工具

| 工具 | 用途 | 集成建议 |
|------|------|----------|
| PostgreSQL 17/18 | 关系型数据库 | 可替代SQLite做大规模数据存储 |
| Node.js 26.1.0 | JS运行时 | BfM前端已用，可扩展到自动化脚本 |
| LM Studio 0.4.13 | 本地LLM推理 | 可测试本地模型作为API补充 |
| Everything 1.4.1 | 文件搜索 | 已集成到search_tool.py |
| 7-Zip 26.00 | 压缩解压 | 可用于自动化打包场景 |
| Git 2.54.0 | 版本控制 | 已用于auto_git_commit |
| Notepad++ 8.9.5 | 文本编辑 | 已集成到GA工具链 |

## 💡 洞察

1. **PostgreSQL 17+18同时安装** — 两个大版本共存，可能浪费空间，建议确认是否需要
2. **LM Studio已安装但未集成** — 本地LLM能力可作为云端API的补充/备份
3. **51个软件+104个服务** — 系统较为精简，无大量冗余
4. **PATH中951个可执行文件** — 系统级工具丰富，可直接调用的很多