---
name: a2b2-create-test-account
description: 通过 ego-browser 创建 A2B2 SIT 测试账号，使用 Work space 完成邮箱验证，再选择套餐并完成 Stripe 沙盒订阅。用于单个或批量测试账号注册。
---

# A2B2 SIT 测试账号

按用户提供的邮箱创建账号，最终分别核实邮箱已验证、测试支付成功、套餐已启用。只处理用户指定的账号。

## 输入与默认值

- 注册入口：`https://app-sit.a2b2.ai/login`。
- 邮箱及密码：使用当前会话中用户提供的值；缺少时询问。密码不写入 skill、日志或结果报告。
- 用户未另行指定时：名字 Ben、姓氏 Tao；Cypher 年付；账单国家 United States。
- Stripe 测试资料：卡号 `4242424242424242`，到期日使用未来日期（如 12/30），CVC 123；持卡人 Ben Tao；地址第 1 行 `123 Oakridge Ave`，第 2 行 `Apt 4B`，城市 San Jose，州 California（CA），邮编 95112，美国（US）。这些仅用于明确标示 sandbox / 测试模式的 Checkout。
- 注册默认使用 ego lite 名为 `Private` 的 profile；邮箱验证仍使用 `Work` space。
- 邮箱位于 ego lite 的 `Work` space，通常为 `ben@a2b2.ai` 的 Gmail；按当前浏览器清单确认，space ID、标签和元素 ref 每次重新发现。

## 浏览器与注册

1. 读取当前可用的 ego-browser skill，执行 `ego-browser skill` 并遵循完整输出。调用 `profiles()` 找到名称为 `Private` 的 profile（按当前清单确认 ID），再用 `taskSpace(任务名, { profileId: 已确认的ID })` 新建一个注册 TaskSpace。`profileId` 仅在创建 space 时生效；复用 space 前确认其 profile 是 Private。若 Private 缺失或有重名，先向用户澄清。仅为了用户指定的邮箱验证使用现有 Work space。复用同一注册页面逐个处理账号。
2. 打开注册入口。若已有账号登录，使用页面的登出操作，然后进入注册；保留用户原有标签。填写姓名、指定邮箱和密码，提交一次。成功标准是验证页显示当前目标邮箱。
3. 若提示账号已存在，使用给定凭据登录以核实并继续未完成的步骤；不自动重置密码或创建其他邮箱。

## 邮箱验证

1. 根据用户的 Work space 授权，在 `listTaskSpaces()` 中确认其 ID 后 claim；发现 Gmail 标签并 adopt。仅查看目标注册邮件。
2. Gmail 搜索可用 `to:<目标邮箱> subject:Verify your A2B2 email`。同主题可能合并多个收件人的邮件：展开最新邮件，核对“发送至”是目标邮箱，避免打开其他账号的旧链接。
3. 点击该邮件的 Verify email 链接并处理 popup；也可在 Work 的代理创建页面中打开从该邮件读到的完整验证 URL。确认页面显示邮箱已验证，再返回注册 TaskSpace 点“我已完成验证”。以实际进入套餐选择页为通过标准。
4. 完成后归还用户原有 Gmail 标签，按 ego-browser 的 finish 规则清理仅为本任务创建的标签。

## 套餐与沙盒支付

1. 核对当前选择为 Cypher、年付。页面可能默认年付，仍需根据当前文案确认；价格以当前页面为准，不把旧金额作为要求。
2. “购买 Cypher”可能位于长页面下部。优先语义操作；若自动滚动后仍不可见，观察当前页面并在实际滚动区滚动，再使用新的 snapshot ref。
3. 账单国家弹窗选择美国，再点前往付款。等待 Stripe Checkout 明确显示 sandbox / 沙盒后填写测试卡。
4. Stripe 自己的账单国家可能仍默认新加坡；独立改为美国。必要时点“手动输入地址”，填完整城市、州及邮编。California 的 option label 可能是英文，选择 value `CA`；国家 value 为 `US`。
5. 核对目标邮箱、Cypher 和按年计费后提交订阅。提交后等待可观察的成功或失败结果；若页面仍在处理，继续等待。只有确认页面回到可提交状态且上次未成功，才考虑重试。

## 结果与异常

- 注册成功：目标邮箱账号已创建。
- 验证成功：验证链接和注册页确认已验证。
- 支付成功：Stripe 返回成功或 A2B2 显示付款成功；单独记录。
- 套餐启用：账号的办公室明确显示 A2B2 Cypher，或“方案与账单”显示当前 Cypher 订阅及年付信息；单独记录。
- 曾出现 Stripe 成功但 A2B2 仍显示 unpaid／等待付款。遇到此情况，短暂等待并刷新账单页或重新登录核实；仍不一致则报告为“已支付、启用未确认”，保留相关页面给用户。不要以再次购买解决已成功付款后的状态差异，也不要擅自修改后台数据。
- 页面无响应时遵循 ego-browser 的错误恢复指引，在同一 TaskSpace 内恢复；新建页面只用于确认挂起的 renderer 等实际需要。清理 cookies/storage 前先读 ego-browser 对应指引。
- 批量任务逐个记录结果；一个账号遇到启用问题时仍可继续其余已授权账号。用简洁表格列出邮箱、邮箱验证、套餐/周期、支付和启用状态，不回显密码或验证 token。
- 本 skill 不授权发送邮件、改变 Linear 状态或修改产品代码。
