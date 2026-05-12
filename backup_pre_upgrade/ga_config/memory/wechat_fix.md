# 微信 App DNS 修复记录

## 问题
微信 App (wechatapp) 后台进程因 DNS 解析 `ilinkai.weixin.qq.com` 失败而退出/断连。

## 根因
- 系统代理（127.0.0.1:7897）干扰了微信的 DNS 解析
- DNS 解析失败导致微信无法连接服务器

## 修复步骤
1. **清除代理设置** — 确保系统/应用代理不干扰微信进程
2. **修改 hosts 文件** — 手动绑定域名：
   ```
   36.155.182.76  ilinkai.weixin.qq.com
   ```
3. **重启微信进程** — 后台进程成功启动

## 修复结果
- ✅ hosts 绑定生效：`36.155.182.76 ilinkai.weixin.qq.com`
- ✅ 后台进程 PID 19448 运行中
- ✅ 收到微信消息并成功回复（send ok len=13 dt=0.7s）
- ✅ DNS 错误已修复

## 注意事项
- 如果 IP `36.155.182.76` 失效，需重新解析 `ilinkai.weixin.qq.com` 并更新 hosts
- nssm 服务名可能未正确注册（`nssm stop wechatapp` 报错"指定的服务未安装"），直接用进程方式管理
