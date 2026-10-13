---
name: linear-create-issue
description: Create a well-structured A2B2 Linear issue with full background — English by default, the standard Background/Current-Behavior/Acceptance three-part body, an automatic Bug flow (extra bug sections + Bug label), a Stakeholders block that also auto-subscribes those people, and an ask-first assignee rule. Always drafts first and creates in Linear only after Ben confirms. Trigger when the user says "linear ticket", "create/raise a ticket", "new linear issue", "開票", "建票", "開一張 linear", or runs /linear-ticket.
---

# A2B2 Linear Ticket Builder

Turn a rough request into a clean, self-contained Linear issue that follows A2B2's team conventions. The person you are talking to is **Ben** (`ben@a2b2.ai` / Tao Ziliang) — **talk to him in Simplified Chinese** while gathering info and confirming, but **write the ticket content in English by default** (see language rule).

Core promises of this skill:
1. Every ticket carries **full background** — never a one-line title with no body.
2. Standard three-part body: **Background / Why → Current Behavior → Expected Behavior & Acceptance Criteria**.
3. If it's a **bug**, the bug flow triggers automatically (extra sections + `Bug` label).
4. **Stakeholders** (people who may be responsible) are listed in the body *and* auto-subscribed.
5. **Assignee is decided by asking Ben**; if he names no one, assign to whoever raised the ticket.
6. **Draft first, create only after Ben confirms.** Never create silently.
7. **Written for a mixed audience — engineers AND the product/requirements team.** Plain language, jargon explained. (See the Audience rule; this applies to *every* ticket, engineering or product-requirement.)
8. **One ticket = one thing.** Never bundle multiple features/requirements/fixes into one issue — detect and split. (See the One-ticket-one-thing rule.)
9. **Check for duplicates first.** Search existing issues (incl. closed/archived) and existing parents before drafting anything. (See the Dedup-and-parent-check step.)
10. **No local file paths or repo-internal references in the body.** Ticket readers have no filesystem access. (See the No-local-paths rule.)
11. **Media files (images/videos) provided by the user MUST be embedded for inline preview**, rendering directly inside the body rather than as a downloadable file link. New design media must be attached under the **Expected Behavior & Acceptance Criteria** section. (See the Media-embedding workflow.)
12. **Ask to backlink to Notion if a Notion URL was referenced.** If Ben provided a Notion link, ask after creation whether to add the created Linear link back into Notion (below the block if block-level, at page top if page-level). (See the Notion backlink workflow.)

## Dedup-and-parent-check step (run BEFORE drafting — every ticket, and every parent)

Never open a ticket or an umbrella parent blind. First search Linear for what may already exist:

1. **Search by keywords + module**, both for the child and for any parent you're about to create:
   - `list_issues` with `query: "<key nouns>"` (searches title + description), e.g. `query: "memory"`.
   - Narrow with `label: "<Module>"` (e.g. `Research`) and/or `team`, and keep `includeArchived: true` so you also catch **closed/duplicate** tickets.
   - Also look for an **existing umbrella parent** for this module (e.g. ENG-153 "Research Update") via `list_issues` (parent-type) or by inspecting a related issue's `parentId`.
2. **Show Ben the candidates** — identifier, title, status — and classify each:
   - **Exact / near-duplicate** → don't open a new one. Offer instead to **update it, add a comment, or reopen** it.
   - **Related but distinct** → proceed, and propose **linking** (relatedTo) and/or attaching to the same **parent**.
   - **A suitable existing parent** → attach the new ticket to it instead of creating a new umbrella.
3. **Only after this check** proceed to drafting. If nothing relevant exists, say so ("查无重复票，开新的") and continue.

### Parent policy (default — conditional, not "always")

- **Split into 2+ tickets** → a shared parent is **required**: reuse an existing umbrella if one fits, else create a new one.
- **Single deliverable + a relevant parent already exists** (e.g. ENG-153 for Research) → **attach to it**; don't create a new parent.
- **Single deliverable + no relevant parent** → open **one standalone ticket**; do **not** manufacture an empty umbrella.
- Rule of thumb: **"Split earns a parent; reuse an existing one before making a new one; never a one-child umbrella."**
  *(If Ben prefers the simpler "every new feature always gets a parent + ≥1 sub", switch this section to that — it's the one knob here.)*

## One-ticket-one-thing rule (non-negotiable)

Each ticket must cover **exactly one independently-shippable, independently-verifiable feature / requirement / fix**. Do **not** combine several into one issue.

**How to detect a bundle** — before drafting, scan the request for splitting signals:
- The word "and", commas, or bullet lists chaining distinct deliverables ("set default model **and** add gating **and** two upgrade entry points").
- Multiple verbs on unrelated objects ("change the copy, move the button, sync the selector").
- Acceptance criteria that would need to be verified/released **separately**, or that touch unrelated modules.

**What to do when you detect a bundle:**
1. **Stop and split.** Propose one ticket per distinct deliverable, each with its own title + full body + acceptance criteria.
2. **Tell Ben in the draft** how you split it and why, e.g. "我把这拆成 3 张：(a)… (b)… (c)…，因为它们可以各自验收/上线。"
3. **Offer a shared parent** so the group stays linked — either an existing parent (like ENG-153) or a new umbrella issue — and set `parentId` on each child. (Local precedent: ENG-153 as parent with ENG-319/320/322… as separate children — imitate that shape.)
4. Only keep things in one ticket when they are **truly inseparable** (cannot be shipped or verified apart). When in doubt, split and ask.

**Legit exception:** small, tightly-coupled changes that must ship together as one atomic unit (e.g. renaming a field and its single call-site). Even then, prefer sub-tasks/checklist over merging unrelated scope.

## Audience & plain-language rule (non-negotiable — applies to every ticket)

A ticket's readers are **not only programmers**. The product/requirements team (Danny, Teresa, Trista, and other non-engineers) read and act on the same ticket. So:

1. **Lead with plain language.** State what's happening and what should happen in terms a non-engineer understands before any implementation detail.
2. **Avoid technical terms where a plain word works.** Prefer "the sign-up page" over "the onboarding route", "the payment didn't go through" over "the Stripe webhook 4xx'd".
3. **When a technical term is genuinely needed, explain it inline the first time** — e.g. "the webhook (the automatic message Stripe sends us when a payment succeeds)". One short parenthetical is enough.
4. **Keep code/log/stack-trace detail in a clearly-labelled section** (e.g. under *Root Cause* or a *Technical Notes* block) so product readers can skip it and engineers can still find it.
5. This holds **both directions**: engineering-filed tickets must stay readable for product, and product-requirement tickets must be concrete enough for engineers — never assume the reader shares your side's vocabulary.

Good local example to imitate: ENG-347's "What happens (plain language)" opener. Bad pattern to avoid: a body that's only a stack trace or only internal module names.

If any required information below is missing, **ask Ben for it** — do not invent background, acceptance criteria, or repro steps.

## No-local-paths rule (non-negotiable)

The ticket body is read by people with **no access to Ben's filesystem or this repo's internal docs** — engineers on other machines, product/requirements people, future readers in Linear. So:

1. **Never cite a local file path** (`docs/decisions/messages.md`, `brainstorms/...`, `src/components/...`) as the source of a decision or spec. Describe *what was decided*, not *where it's written down locally*.
2. **Never reference "today's conversation," "the transcript," or "what we discussed"** as if the reader was there. State the decision/behavior directly.
3. Paraphrase what a decision doc says into plain prose for the ticket body — don't make the reader go find the file. If a durable link is genuinely useful (a Notion page, a Linear issue, a public URL), that's fine; a path on Ben's laptop is not.
4. This applies to every section, but especially **Background / Why** and **Root Cause**, where citing "see the decision record" is the easy trap.

---

## Step 0 — Load tools

```
ToolSearch → select:mcp__claude_ai_Linear__save_issue,mcp__claude_ai_Linear__list_users,mcp__claude_ai_Linear__list_issue_labels,mcp__claude_ai_Linear__list_projects,mcp__claude_ai_Linear__list_issues,mcp__claude_ai_Linear__get_issue
```

`save_issue` (no `id`) creates the issue. `get_issue`/`list_issues` help resolve a parent. `list_projects` resolves a project by name.

---

## Step 1 — Collect the inputs (ask if missing)

Gather these. Anything not provided and not safely inferable → **ask Ben** (batch the questions; don't interrogate one at a time).

**Always required**
- **Type** — `Bug` | `Feature` | `Improvement`. If unclear, infer from wording ("broken / error / fails / stuck / 报错" → Bug) and confirm.
- **Title** — see Step 2 rules.
- **Background / Why** — why this matters, the context, who asked, links.
- **Current Behavior (现象)** — what happens today (for a feature: the gap / current state).
- **Expected Behavior & Acceptance Criteria** — what "done" looks like, as checkable bullets.
- **Team** — `Engineering` (ENG) or `A2b2` (A2B). Default `Engineering` unless it's clearly GTM/business.
- **Stakeholders** — people who may be responsible / need to know. Default to including **@ben**. Ask "还有谁相关？(e.g. @alex, @jon…)".
- **Assignee** — **always ask** "这张要指派给谁？". If Ben names no one → assign to the **raiser** (the person who reported/requested it; if that's Ben himself running the skill, assign `me`).

**If Type = Bug, also required (the Bug flow)**
- **Steps to Reproduce** — numbered.
- **Actual Result** vs **Expected Result**.
- **Root Cause** — if known; otherwise write `Unknown — needs investigation`.
- **Environment** — SIT/luma vs prod, tier, model, browser/OS, affected user/account if any.
- **Severity / Impact** — who is blocked and how badly.

**Optional (set if known, else omit — don't block on these)**
- Priority (`0` None … `1` Urgent), Due date (ISO, convert relative dates to absolute), Project, Parent issue, Module label (Step 4).

> ⚠️ Don't over-default Priority. Not everything is Urgent. If unsure, leave Priority unset or ask.

---

## Step 2 — Title rules (English by default)

A good title is one scannable line stating the outcome. Enforce:

1. **Imperative or problem-statement, verb-first**: `Fix…`, `Add…`, `Move…`, `Sync…`, `Reduce…`, or for bugs a crisp symptom: `Research: Skip on clarifying question errors and blocks the user`.
2. **Module prefix when it helps**: `Research:`, `Billing:`, `Infra:`, `Onboarding:` …
3. **NO @names in the title.** People go in the Stakeholders block and Assignee, never the title. (This is the #1 local anti-pattern — title @mentions make tickets invisible in everyone's "My Issues".)
4. **One line, no background dumped into it.** Detail lives in the body.
5. English by default (see language rule).

---

## Step 3 — Body template

Write as Markdown. Use **literal newlines**, not `\n`. Mention users as `@displayName`.

Write every section for the **mixed audience** (see the Audience rule): plain language first, jargon explained inline, deep technical detail confined to *Root Cause* / *Technical Notes*.

### Standard (Feature / Improvement)

```markdown
## Background / Why
<context, motivation, who asked, links to threads/docs/prior issues>

## Current Behavior
<what happens today / the gap>

## Expected Behavior & Acceptance Criteria
<If new design screenshots/videos are provided, attach/embed them right here under this section>
- [ ] <checkable outcome 1>
- [ ] <checkable outcome 2>

## Stakeholders
- @ben
- @alex
<people who may be responsible or need to follow — @mention auto-subscribes them>
```

### Bug (append the standard sections' Background + then the bug block)

```markdown
## Background / Why
<what area, why it matters, who reported, links>

## Current Behavior
<the broken behavior, user-visible>

## Steps to Reproduce
1. …
2. …

## Actual vs Expected
- **Actual:** …
- **Expected:** …

## Root Cause
<plain-language summary first; put logs / stack traces / module names under a **Technical Notes** sub-heading here so product readers can skip them>

## Environment
<SIT/luma vs prod, tier, model, browser/OS, affected account>

## Severity / Impact
<who is blocked and how badly>

## Acceptance Criteria
<If new design screenshots/videos are provided, attach/embed them right here under this section>
- [ ] <fix verified by …>
- [ ] <regression / repro no longer occurs>

## Stakeholders
- @ben
<@mention auto-subscribes>
```

---

## Step 3.5 — Media-embedding workflow (inline preview non-negotiable)

All media files (images, design mockups, screen recordings, videos) MUST be embedded into the issue body in a format that **previews and renders directly inside Linear**. **NEVER output media as a plain downloadable file link (e.g. `[file.mp4](url)`) or unrendered attachment that forces the reader to download.**

1. **Section placement rules (Strict):**
   - **New design screenshots / mockups / videos** → MUST be placed directly under `## Expected Behavior & Acceptance Criteria` (or `## Acceptance Criteria`).
   - **Current state / bug / error screenshots or videos** → place directly under `## Current Behavior` or `## Steps to Reproduce`.
2. **Create the issue first** (Step 7) so an issue ID exists — attachments upload against an existing issue.
3. **For each media file (image or video)**, run the upload sequence one file at a time (don't batch prepares — signed URLs expire in 60s):
   - `prepare_attachment_upload` with `issue`, `filename`, `contentType` (e.g. `image/png`, `video/mp4`), exact `size` in bytes (check with `ls -la` or equivalent), and a descriptive `title` (e.g. "New design prototype", "Current behavior recording").
   - `curl -X PUT --data-binary @<path>` to `uploadRequest.url` with **every header in `uploadRequest.headers` sent verbatim** (casing included).
   - `create_attachment_from_upload` with the returned `assetUrl` to finalize it as a Linear attachment.
4. **Must-be-previewable embedding syntax**:
   - **Images:** Use image markdown `![<title>](<assetUrl>)` so Linear renders the image preview inline.
   - **Videos:** Use Linear inline video player syntax or embed markdown `![<title>](<assetUrl>)` (or HTML `<video src="<assetUrl>" controls></video>`), ensuring the media player or preview renders directly in the body. Do NOT use `[title](url)` link syntax which renders as a plain download hyperlink.
   - Use `save_issue`'s `patch` with `insert_after`/`insert_before` anchors or update description to ensure new design media is placed right under `## Expected Behavior & Acceptance Criteria`.
5. Don't dump all media at the top or bottom of the body as an afterthought — match each one to the section it's evidence for.

---

## Step 4 — Labels

Pass via `labels: [...]` (names are fine).

**Type label (always):** `Bug` | `Feature` | `Improvement`.

**Module label (add when clear)** — helps routing. Common ones:
`Research`, `Billing`, `Identity & Access`, `Onboarding`, `Infra`, `Frontend Experience`, `Agentic Office`, `Own`, `Connect`, `Scour/Explore`, `Client Vault`, `Compliance & Legal`, `Ops Console`, `Associate`, `Website`, `GTM`.

**Team label (optional):** `Platform` (Rex side), `AI-team` (Jon/Brock side), `GTM/Business`, `Ops`, `Product/Design`.

If unsure which module, pick the closest and mention it in the draft so Ben can correct.

---

## Step 5 — Stakeholders & subscribers (important limitation)

`save_issue` has **no subscriber parameter**. The way to subscribe someone is to **@mention them in the description**, which auto-subscribes them in Linear. So:

- Put each stakeholder as `@displayName` in the **Stakeholders** block. That single mechanism satisfies both "list in content" and "add as subscriber."
- Use the **exact `displayName`** from the roster below, or the mention won't resolve.
- Always include `@ben` unless Ben says otherwise.

---

## Step 6 — Assignee policy

- **Always ask** Ben who to assign. Present it plainly: "指派给谁？(不指定的话我会派给提出这张票的人)".
- If he names someone → use it.
- If he names **no one** → assign to the **raiser** (the person who requested/reported it). If Ben is the raiser, use `me`.
- Never leave it on the creator by accident when a different raiser exists, and never rely on a title @mention as a substitute for assignee.

---

## Step 7 — Draft → confirm → create

0a. **Dedup-and-parent-check first.** Search existing issues (incl. closed/archived) and existing parents; surface candidates to Ben and handle duplicates before anything else.
0b. **Split (One-ticket-one-thing rule).** If the request bundles multiple deliverables, split into N drafts and decide the shared parent (reuse before new) per the Parent policy.
1. **Assemble the draft(s)** and show Ben the full ticket in Simplified-Chinese-framed preview: Title, Type/Labels, Team, Project/Parent (if any), Priority/Due (if any), **Assignee**, **Stakeholders/subscribers**, and the full English body. If you split, present all drafts together with a one-line note on how/why you split and the proposed parent.
2. **Wait for explicit confirmation.** Offer quick edits (title wording, assignee, stakeholders, priority, and the split itself — merge/split further).
3. **On confirm**, create each ticket via `save_issue` (no `id`) with: `title`, `team`, `description`, `labels`, `assignee`, plus any of `priority`/`dueDate`/`project`/`parentId` that were set. When you split, set the same `parentId` on every child (create the umbrella parent first if it's new). Stakeholder subscriptions ride along via the `@displayName` mentions in `description`.
3a. **If Ben provided design images/videos**, run the Media-embedding workflow (Step 3.5) against the now-existing issue(s) and attach/embed them under **Expected Behavior & Acceptance Criteria** (or under Current Behavior for bug evidence).
4. **Report back** every created issue's identifier + URL (and the parent, if new). If a bug, remind Ben the `Bug` label is set and to move the status as work starts (Todo → In Progress → In Review → Done).
5. **If a Notion URL was referenced during the request**, proceed to Step 8 (Notion backlink workflow).

---

## Step 8 — Notion backlink workflow (when a Notion URL is referenced)

If Ben cited or referenced a Notion URL during the issue creation process (in context, background, or links):

1. **Ask Ben after issue creation**:
   "检测到此 Ticket 引用了 Notion 链接，是否需要把新建的 Linear Issue 链接（`<Identifier>` / `<URL>`）加到该 Notion 中？"
2. **On Ben's confirmation**, determine placement based on the Notion URL type:
   - **Block-level reference** (URL contains `#<block_id>` or a block anchor): Insert/append the Linear issue link **directly below the referenced block**.
   - **Page-level reference** (standard Notion page URL without a block anchor): Insert the Linear issue link **at the very top of the Notion page**.
3. Confirm completion once the backlink is added.

---

## Language rule

- **Ticket content (title + body): English by default.** Keep model names, `$` amounts, %, credit counts, and proper nouns verbatim. If Ben explicitly asks for Chinese, mirror the local convention (Simplified Chinese for team-facing docs).
- **Conversation with Ben (questions, draft framing, confirmation): Simplified Chinese.**

---

## Team roster (displayName → who)

Use `displayName` for @mentions and for the `assignee` field (name/email/id all accepted).

| displayName              | name / email                   | notes                                    |
| ------------------------ | ------------------------------ | ---------------------------------------- |
| `ben`                    | Tao Ziliang · ben@a2b2.ai      | you (the user); prototypes (Arcus)       |
| `zyron`                  | Zyron · zyron@a2b2.ai          | ENG + A2B                                |
| `alex`                   | alex@a2b2.ai                   |                                          |
| `jon`                    | jon@a2b2.ai                    | AI-team (model orchestration/validation) |
| `wenzhe`                 | brock · wenzhe@a2b2.ai         | AI-team                                  |
| `danny`                  | danny@a2b2.ai                  | product/PM — files most eng tickets      |
| `teresa`                 | teresa@a2b2.ai                 | product                                  |
| `trista`                 | Trista Sun · trista@a2b2.ai    |                                          |
| `ashok`                  | Ashok Karwasra · ashok@a2b2.ai | admin, ops/business                      |
| `rex`                    | rex@a2b2.ai                    | platform — offboarding, email will lapse |
| `ruyuzhu`                | Ruyu (Judy) · ruyuzhu@a2b2.ai  |                                          |
| `neo` / `peng` / `terry` | admins                         |                                          |

Teams: **Engineering** (`ENG`) · **A2b2** (`A2B`). Default new eng work to `Engineering`.

If a name you're given isn't here, resolve it with `list_users` (query by name/email) rather than guessing.

---

## Compliance note

A2B2 is a wealth-intelligence information platform — nothing on it is investment advice. Keep that framing out of ticket bodies unless the ticket is specifically about compliance copy; just don't introduce advice-like language.
