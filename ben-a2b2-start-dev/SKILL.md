---
name: ben-a2b2-start-dev
description: "在 Ben 本机启动或复用 A2B2 开发环境、Portal、Metro、iOS 或 Marketing 时使用。为团队 a2b2-start-dev 补充仓库外的预检与启动入口；同时适用于 Alfred a2b2 入口维护。"
---

# Ben 的本机开发启动入口

先读取当前 checkout 的 `.agents/skills/a2b2-start-dev/SKILL.md`，沿用团队的目标选择、服务归属、环境配置与验收规则。本技能覆盖 Ben 本机的入口选择与 iOS 构建命令；具体工具行为见 [本地说明](/Users/ben/.config/a2b2/dev-tools/README.md)。团队技能和仓库工具保持原样。

## 按请求选择入口

确认目标 checkout 后，始终显式传入 `A2B2_CHECKOUT`；下面的 `$PWD` 必须是已确认的仓库根目录。

| 请求范围 | 执行方式 |
| --- | --- |
| 未指定目标，或同时请求 Portal 与 iOS | 在前台运行下方本地 `dev` 入口，保留对应终端；已有同 checkout 守护时复用它并核对实际脚本路径。 |
| 只请求 Portal、Marketing 或 Metro | 使用团队技能对应的单目标命令与验收。完整 `dev` 会同时启动 Portal、Metro 和 iOS，不用于单目标请求。 |
| 只请求 iOS / Mobile | 按团队技能复用或启动 Metro、选择并启动模拟器；打开 App 前执行下方本地预检及真实 bundle 检查，再执行团队的原生启动与 Maestro 验收。 |

```sh
A2B2_CHECKOUT="$PWD" /Users/ben/.config/a2b2/dev-tools/dev
```

Alfred 输入 `a2b2` 调用同一个本地入口，默认 checkout 为 `/Users/ben/Project/A2B2/a2b2`。其他 checkout 用显式环境变量；不同 checkout 仍共享端口，先按团队规则检查归属。

Ben 本机增强流程使用这个仓库外入口，不执行仓库的 `pnpm dev:local` 或直接运行 `tools/dev/guard.mjs`。本地工具缺失时报告入口缺失，依据本地说明恢复；不要悄悄回退旧脚本。

## iOS 预检与构建

模拟器启动后，检查依赖与已安装 App 的构建记录：

```sh
A2B2_CHECKOUT="$PWD" /Users/ben/.config/a2b2/dev-tools/dev check
```

对于 iOS 单目标启动，Metro 就绪后、打开 App 前，通过本地模块检查真实 bundle；HTTP 失败时保留日志并修复后重试：

```sh
A2B2_CHECKOUT="$PWD" node --input-type=module -e 'const { checkIOSBundle } = await import("/Users/ben/.config/a2b2/dev-tools/preflight.mjs"); await checkIOSBundle("http://localhost:8081");'
```

缺少匹配的 App、构建记录或原生输入发生变化时，按预检输出对本轮发现的设备构建；保持既有签名、bundle ID、App 数据和 Metro：

```sh
A2B2_CHECKOUT="$PWD" /Users/ben/.config/a2b2/dev-tools/dev ios --device <本轮发现的UDID>
```

构建成功后重跑预检，再恢复请求范围内的启动。JavaScript 页面修改不单独触发原生重建。工具及 `yaml` 依赖保留在本地目录，构建记录保留在对应 checkout 的忽略缓存；不向仓库添加脚本、根依赖或锁文件改动。

## 验收

沿用团队的页面渲染与 Maestro 规则；依赖通过、端口可达或构建记录匹配都不代替画面验收。报告守护脚本是否来自 `/Users/ben/.config/a2b2/dev-tools/guard.mjs`，并分别报告请求范围内的服务与界面状态。显式 HTTPS 请求另读个人 `ben-a2b2-portal-https`，普通启动不启动 HTTPS 代理。
