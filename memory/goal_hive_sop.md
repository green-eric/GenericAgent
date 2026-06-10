# Goal Hive Mode SOP

> 作者: GA | 版本: 2.0 | 更新: 2026-06-10

## 目的

Goal Hive = Goal Mode 的多 worker 协作协议，通过 BBS 公告板实现主从式任务分发。

## 适用范围

- 适用：需要多 worker 并行协作的复杂任务
- 不适用：简单单步任务、需要实时交互的任务

## 前置条件

- Python 3.x 环境
- `requests` 库已安装
- CodeRoot 路径正确配置
- 端口未被占用

## 步骤

### 1. 初始化 Hive

1. 选一个空闲端口 `PORT` 和本次协作 key `BOARD_KEY`
2. 创建 Hive 数据目录：`BBS_CWD=<CodeRoot>/temp/hive_<目标短名>`
3. 启动 BBS：`start /b python <CodeRoot>/assets/agent_bbs.py --cwd <BBS_CWD> --port <PORT> --key <BOARD_KEY>`
4. 验证：`requests.get(http://127.0.0.1:<PORT>/readme?key=<BOARD_KEY>)` 返回 200

### 2. 发布第一帖

BBS 第一帖必须包含：
1. 任务目标
2. Hive Master 职责（全文4点，一字不改）
3. 工作目录说明：优先使用 `<BBS_CWD>` 进行文件传输
4. 附加说明：`此为最终目标，worker不要接单，先等hive master拆分子任务。`

### 3. 启动 Worker

```bash
start /b python <CodeRoot>/agent/main.py --reflect <CodeRoot>/reflect/agent_team_worker.py --base_url http://127.0.0.1:<PORT> --board_key <BOARD_KEY> --name hive-worker-1
```

### 4. 启动 Hive Master

- 询问用户时间预算
- 按 `goal_mode_sop.md` 启动 hive master
- master 阅读 `goal_hive_master_duty.md` 了解职责

### 5. goal_state.json 规范

`objective` 必须包含：
1. 用户目标（简明描述任务与交付物）
2. BBS 地址
3. Hive Master 职责全文
4. 阅读 `goal_hive_master_duty.md`

`done_prompt` 固定文本：
`关闭所有你拉起的worker，并在BBS发一条帖子宣告你管理的任务结束，worker除了明确追加任务外，不应再回应。`

## 验证

- [ ] BBS 启动后可访问 `/readme`
- [ ] 第一帖包含全部4项内容
- [ ] goal_state.json 的 objective 完整
- [ ] done_prompt 原文匹配
- [ ] worker 数量不超过5个

## 坑点

- ⚠️ Hive 模式单独运行，不要和 plan/supervisor/subagent 混杂
- ⚠️ 启动 master 前必须回读 goal_state.json 逐项确认
- ⚠️ master 不允许亲自干活导致 worker 空转
- ⚠️ 文件传输优先用 BBS_CWD 而非 BBS 文件功能
- ⚠️ worker 由 master 按需要增加，一般任务 2-4 个足够

## 参考资料

- `goal_mode_sop.md` — Goal Mode 单 worker 版
- `goal_hive_master_duty.md` — Hive Master 详细职责
- `supervisor_sop.md` — 监督者模式
