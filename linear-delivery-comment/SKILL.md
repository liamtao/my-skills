---
name: linear-delivery-comment
description: >-
  Use whenever Ben (the designer) has finished a prototype/design change and wants to record it on
  the matching Linear ticket. Trigger on phrases like "这个 ticket 交付了", "把改动写进 A2B-271 / ENG-166",
  "记录到 Linear", "写个交付 comment", "同步进展到 Linear", "交付了跟我过一遍 comment", or any time Ben
  references pushing a design change and a Linear ticket in the same breath. Drafts a structured
  bilingual delivery comment (改动点 / 交互逻辑 / Commit / 状态·抄送), confirms it with Ben,
  then posts it via the Linear MCP with the chosen reviewers or cc recipients. Ticket status stays
  unchanged unless Ben explicitly requests a status change. Also handles buffering: when Ben says "存草稿别发 / 先存着", save the comment to a
  local draft file instead of posting; when he says "发 XXX 的草稿", publish a held draft.
  Also publishes verified PR delivery on a known originating ticket when called by
  ben-a2b2-submit-pr. Do NOT default to @-mentioning Trista.
---

# Linear Delivery Comment

Ben is the designer on A2B2. When he finishes a prototype change and pushes it, he needs to record
the work on the matching Linear ticket. The comment is read by **two audiences at once**: his manager
(who sees what shipped from the delivery trail, not from status churn) and the **engineering team**
(who need enough interaction detail to build it). This skill produces one comment that serves both,
then posts it and moves the ticket per Ben's instruction.

## Status authorization

Keep Linear status unchanged unless Ben explicitly requests the status change for the named ticket(s). This includes parent tickets and subtickets. Approval to implement, test, commit, push, upload, open a PR, deploy, publish a comment, invoke this skill or request review does not authorize a status change.

## PR 来源工单

从 `ben-a2b2-submit-pr` 接收已核验的 PR、来源工单 ID、base/head、验收结果和可分享的图片。此流程沿用 Ben 对来源票交付评论的授权。Ben 要求暂缓或跳过 Linear 时，按本次要求处理。独立的设计交付仍走下方 Workflow。

1. 读原工单和评论，用 PR 链接查重。已有同一 PR 的交付评论且内容有效时，复用其链接。若 PR 更新导致交付内容实质改变，在有权限时更新自己发布的原交付评论。写入结果不明时按工具提示读回或恢复，确认未落地后再重试。
2. 复用 Linear 草稿的交付正文。手头没有草稿时，从已核验的 PR 和验收证据起草。保留用户可感知的变更、验收结果和 PR 链接，并标明未测范围。移除仅用于草稿审批的字段计划和内部说明。默认省略审阅者和抄送。
3. 有 Before / After 图时，读取 `linear-create-issue` 的 Step 3.5，在评论中嵌入上传至 Linear 的对比图。只使用获准分享的截图，保留场景及平台图注。
4. 通过当前获授权的 Linear 工具发布为原工单的一条评论。从 Orca Chat 工作时用 `orca linear comment add <issue-id> --body-file <path>`。若由该工单线程唤醒，按 Orca 规则用 `orca bot reply`。写入范围仅限交付评论。读回正文和内嵌图片，确认图片可加载后报告评论链接。

## Why the comment looks the way it does

- **Engineering has to build from it.** A pretty description of "what changed" is not enough for a
  developer. They need the concrete behaviour: what triggers it, how it responds, which states exist,
  the edge cases. That is why the 交互逻辑 section exists and is written 中英混排 — Chinese prose so the
  Chinese-reading team follows it, English for the technical terms / state names so it maps cleanly
  onto code.
- **Keep it lean — no 设计理由, no 备选方案.** Ben found that a design-rationale block and an
  alternatives-considered block both added noise without helping either audience: 改动点 already shows
  the manager what shipped, and 交互逻辑 gives engineering what they need. Omit both. Source everything
  from real work (git diff + `docs/decisions/`) and never pad.

## Workflow

1. **Identify the ticket.** If Ben gave an identifier (e.g. `A2B-271`, `ENG-166`), use it. If not, ask
   or offer to pick from his In Progress / recently-touched issues (`list_issues assignee:me`).
   Read the ticket with `get_issue` so the comment answers the *original* request, and to learn its
   team (the A2B- prefix is team **A2b2**; ENG- is team **Engineering** — this matters for status, see
   step 5).

2. **Gather the real change.** Read the relevant `git log` / `git diff` since the last delivery and
   skim `docs/decisions/` for the module in question. The comment must describe what was actually
   built, not a guess. Get the commit/PR URL for the Commit line.

3. **Draft the comment** using the exact template below. Keep 改动点 to user-perceivable changes (this
   project is UI/UX only — no implementation detail there); put the build-facing behaviour in 交互逻辑.

4. **Ask Ben whether this needs review by others**, and who — this determines the @mentions only.
   Use one AskUserQuestion with the two rosters:
   - **需要 review** → reviewers chosen from **Teresa / Danny / Ashok** (multi-select).
   - **不需要 review**（只抄送知悉）→ recipients chosen from **Zyron / Rex / Jon / Neo** (multi-select).
   Let Ben pick "不@任何人" too. **Never auto-mention Trista.**

5. **Show the finished comment and wait for Ben's explicit go** before
   writing anything to Linear. This is a shared team tracker — nothing posts without confirmation, and
   Ben may be buffering (he sometimes finishes early and reveals later). If he says "存草稿别发 / 先存着",
   do NOT post — switch to **Draft-and-hold mode** (see the section below) and stop.
   Include a proposed status change only when Ben explicitly requested it. Approval to post the comment alone leaves status unchanged.

6. **On confirmation, post:**
   - For approved screenshots or recordings, follow `linear-create-issue` Step 3.5 to embed and verify inline media in the comment.
   - Post the comment: `save_comment` with `issueId:"<A2B-xxx>"` and `body:<comment>`.
   - Leave status unchanged for both review and cc branches unless Ben explicitly requested a status change.
   - For an explicitly requested change, resolve the target status for the owning team, change only the named ticket(s), then read back the result. If the requested status is unavailable, report that and preserve the current status; do not substitute another status.

7. **Provide issue URL:** Always output the clickable URL of the target Linear issue (e.g. `https://linear.app/.../issue/<TICKET>` or the `url` field returned by Linear MCP) in your final response to Ben so he can easily click and jump to it in the browser.

## Comment template

Fill this exactly. Use literal newlines (the Linear MCP wants real markdown, not escaped strings).
`@displayName` mentions notify the person — the display names are lowercase (see roster).

```markdown
**设计交付如下（给AI作为context）**

**改动点**
- <用户能感知的变化，一到三条；不写实现细节>

**交互逻辑 / Interaction logic**
- 触发 (Trigger): <什么操作/场景触发>
- 行为 (Behavior): <触发后界面怎么响应>
- 状态 (States): <涉及的状态，用英文状态名，如 empty / loading / success / error / disabled>
- 边界 (Edge cases): <异常、空、超长、离线等，没有就写"无">

**Commit / PR**
- <GitHub 链接>

**状态·抄送**
- <见下方"状态·抄送行">
```

**状态·抄送行：**

- 需要 review：`状态不变，请 @teresa @danny review。`（只列 Ben 选中的 reviewer）
- 不需要 review：`状态不变，@zyron @rex 知悉。`（只列 Ben 选中的抄送人）
- 仅当 Ben 明确要求变更状态时：预览写 `按要求转为 <状态>，请 @<reviewer> review。`，执行后核验该状态；未成功时不得报告已变更。

## People roster

Mention with `@displayName`. The two groups map to the two branches in step 4.

| 名字 | @displayName | email | 组 |
|---|---|---|---|
| Teresa | `@teresa` | teresa@a2b2.ai | Review（状态不变）|
| Danny | `@danny` | danny@a2b2.ai | Review（状态不变）|
| Ashok | `@ashok` | ashok@a2b2.ai | Review（状态不变）|
| Zyron | `@zyron` | zyron@a2b2.ai | 抄送（状态不变）|
| Rex | `@rex` | rex@a2b2.ai | 抄送（状态不变）|
| Jon | `@jon` | jon@a2b2.ai | 抄送（状态不变）|
| Neo | `@neo` | neo@a2b2.ai | 抄送（状态不变）|

**Trista (`@trista`) is intentionally not in either group — do not mention her unless Ben names her explicitly.**

## Status reference

Team is inferred from the identifier prefix; verify with `get_issue` if unsure.

- **A2b2** (A2B- prefix) statuses: Backlog, Todo, In Progress, **In Review**, Ready for Testing,
  Closed after Testing, Done, Canceled, Duplicate.
- **Engineering** (ENG- prefix) statuses: Backlog, Todo, In Progress, Ready for Testing,
  Closed after Testing, Done, Canceled, Duplicate — **no In Review**.

## Example (filled)

For `A2B-268` "[设计·Ben] Own 连接状态与重认证反馈", review by Teresa + Danny:

```markdown
**设计交付如下（给AI作为context）**

**改动点**
- Own 账户连接新增「连接中 / 成功 / 失败 / 需重认证」四种状态反馈，用户随时能看到连接进展。

**交互逻辑 / Interaction logic**
- 触发 (Trigger): 用户在 Own 点「连接账户」发起 Plaid 连接。
- 行为 (Behavior): 连接过程展示 loading 态；成功后收起弹窗并在账户行显示绿色已连接标记；失败弹出可重试的 error 态。
- 状态 (States): connecting / connected / failed / needs-reauth (MFA)。
- 边界 (Edge cases): MFA 过期时进入 needs-reauth，提供「重新认证」入口，不清空已导入持仓。

**Commit / PR**
- https://github.com/.../commit/xxxxxxx

**状态·抄送**
- 状态不变，请 @teresa @danny review。
```

Post the approved comment only. This review request does not authorize a `save_issue` status update.

## Draft-and-hold mode (buffer)

The Linear MCP has **no draft comment** — `save_comment` publishes immediately and notifies subscribers.
So when Ben wants to finish the writeup now but reveal it later (his buffer), the draft lives **outside
Linear**, as a local file in `.linear-drafts/` (git-ignored, never committed, never posted).

**Saving a draft** — triggered by "存草稿别发 / 先存着 / 存下来 / 先不发":
- Do steps 1–3 as normal (identify ticket, gather the real change, draft the comment).
- **Skip the review/@mention questions** — recipients are chosen when the draft is published, not now.
  Status stays unchanged unless Ben explicitly requests otherwise.
- Write the comment body to `.linear-drafts/<TICKET>.md` (e.g. `.linear-drafts/ENG-287.md`). Leave the
  状态·抄送 line as a placeholder: `- <发布时确定：review / 抄送 / 状态>`.
- Keep the `**设计交付如下（给AI作为context）**` header.
- Confirm to Ben with the file path. Do not touch Linear at all.

**Publishing a held draft** — triggered by "发 <TICKET> 的草稿 / 把 ENG-287 的草稿发了":
- Read `.linear-drafts/<TICKET>.md`, show it to Ben.
- Now run the normal **step 4** review branch question and fill the 状态·抄送 line.
- On his go: `save_comment`. Change status only if Ben explicitly requested it, following step 6.
- **Delete the draft file** after a successful post, so it can't be double-published.

**Listing drafts** — if Ben asks "有哪些草稿 / 还有什么没发", list the files in `.linear-drafts/`.

Drafts are plain markdown — Ben can hand-edit them before publishing.

## Guardrails

- **Use the applicable authorization.** The PR 来源工单 flow uses Ben's standing delivery-comment authorization. For an independent design delivery, draft first and post on Ben's word.
- **Source the content from real work** (git diff + decision docs). Do not invent changes or rationale.
- **Never pad.** No alternatives section; if edge cases are genuinely none, write "无".
- **Respect buffering.** If Ben wants to hold, keep the draft ready and don't post or move status.
- **Never mention Trista by default.**
