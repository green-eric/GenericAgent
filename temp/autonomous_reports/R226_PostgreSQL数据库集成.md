# R226 | PostgreSQL数据库集成

## 目标
利用已安装的 PostgreSQL 18 搭建本地数据库，替代 SQLite 做大规模数据存储

## 诊断过程
1. PG18 服务注册为停止状态，但 postmaster.pid 残留
2. 清理 pid 文件后启动失败 - pg_hba.conf 中 IPv6 (::1) 仍为 scram-sha-256
3. 修改全部认证为 trust 后连接成功
4. 恢复 host 行为 scram-sha-256，保留 local 为 trust

## 产出
- 数据库: ga_db
- 表: ga_tasks (id, task_name, status, created_at, completed_at, metadata)
- 测试数据: 1行验证通过

## 连接信息
- Host: localhost
- Port: 5433
- Database: ga_db
- User: postgres
- 驱动: psycopg2-binary (已安装)

## pg_hba.conf 最终配置
- local all all trust
- host all all 127.0.0.1/32 scram-sha-256
- host all all ::1/128 scram-sha-256

## 注意事项
- PG18 端口 5433 (非默认 5432)
- 需要设置 postgres 用户密码后才能用 scram-sha-256 远程连接
- 当前 local 连接用 trust，host 连接需密码
