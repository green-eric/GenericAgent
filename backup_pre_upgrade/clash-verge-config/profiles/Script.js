// Clash Verge Script - 每次配置更新后自动关闭 TUN 模式
// 不管订阅怎么更新，TUN 始终为 false

function main(config) {
  // 强制关闭 TUN 模式
  if (config.tun) {
    config.tun.enable = false;
  }
  return config;
}
