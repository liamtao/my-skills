---
name: a2b2-pr-to-linear
description: "Record features and fixes from an A2B2 pull request in Linear: inspect the full PR, group related changes, find existing tickets, preview complete drafts, then create or update approved records. Use when Ben asks to turn a submitted PR into Linear tickets or subissues."
---

# Record PR features in Linear

Produce a traceable record of the requested PR scope. Talk with Ben in Chinese; write ticket titles and bodies in English unless he requests otherwise.

For ticket wording, Bug sections and media placement, read the installed [linear-create-issue skill](../../../.agents/skills/linear-create-issue/SKILL.md). This skill owns PR scope, batch grouping and execution. Reuse the user's existing choices and confirmation instead of asking for them again.

## Ben's defaults

Use these defaults unless Ben explicitly overrides them for the current batch or ticket:

| Field | Default |
| --- | --- |
| Parent for iOS or Portal Mobile work | ENG-660. Include a shared Web/Mobile change here when its grouped outcome includes iOS or Portal Mobile. Resolve a suitable parent separately for other work. |
| Assignee for all records | Ben, verified through ben@a2b2.ai. |
| Sprint for all records | Proactively ask Ben to choose the current or next sprint for each batch, showing the owning team's live cycle names and dates. Reuse an explicit choice already given for that batch. |
| State | Preserve existing ticket status. For new tickets, omit the state field and use the team's creation default unless Ben explicitly requests a state. |

Keep the parent and assignee defaults without asking again; obtain the sprint choice for the batch. A sprint choice does not authorize a status change. Change Linear status only when Ben explicitly requests the status change for the named ticket(s), including any parent tickets or subtickets. Permission to implement, test, commit, push, upload, create a PR, deploy, invoke this skill or approve ticket content does not authorize a status change. These defaults do not authorize changes to the parent itself or other tickets, bypass batch confirmation or establish that testing has passed.

## 1. Resolve the PR and batch settings

- Use a supplied PR URL or number. For “this PR”, use the PR established in the current chat and verify it through GitHub. Ask only if multiple PRs remain plausible.
- Discover the available GitHub and Linear tools and their current schemas. Prefer connectors; local Git can supplement missing diff/history context when the checkout matches the PR revision. Report unavailable capabilities without treating a tool failure as an empty result.
- Read the PR title, description, current base/head SHA, all changed-file pages and complete patches. Use the actual PR base, including a stacked PR's parent branch, rather than the whole local branch or an assumed main base. Inspect commit history to explain iterations; describe the resulting PR behavior, not reverted experiments as delivered features. Account for fixes, shared cross-app changes and supporting configuration. Flag unavailable or truncated evidence before claiming full coverage.
- Resolve parent, team, assignee and cycle using explicit instructions for this batch first, then Ben's defaults. Resolve a state only if Ben explicitly requested it. Read the parent and its children. Keep parent and project separate.
- Resolve people through Linear. “Me” in Ben's request means Ben, not necessarily the connector's authenticated user; verify the account, using ben@a2b2.ai when appropriate.
- Query the owning team's current and next cycles, verify their dates and ask: “这批 ticket 放在当前 Sprint（名称、日期），还是下个 Sprint（名称、日期）？” Ask early while continuing independent PR analysis. If Ben already chose for this batch, use that answer without asking again. Keep the cycle decision pending until answered; do not select an option after a timeout. If either cycle cannot be established uniquely, report the gap instead of guessing. Resolve the chosen cycle by UUID, not internal number; displayed sprint names can differ from cycle numbers.
- Ask together for essential missing settings while continuing independent PR analysis. Offer Engineering as the team for A2B2 engineering work. Present optional unset fields as unset; avoid inventing priority or due dates.
- Preserve ticket status unless Ben explicitly requests a change. A PR's draft, merged or deployed state and a chosen sprint do not authorize a status transition. Show parent changes for reused tickets in the proposal.

Completion: the PR revision and effective batch settings are resolved or their specific gaps are visible. Resolve IDs from live Linear data rather than caching values from a previous run.

## 2. Group changes and check existing records

Group by user-facing outcome and acceptance, not by file count or commit count. Combine related iterations and follow-up fixes into one coherent record. Keep unrelated deliverables separate. Shared Web/Mobile work may belong in one record when it represents the same outcome. Treat naming corrections, such as “Ask dock” to “chatbot dock”, as ticket terminology unless Ben also requests product changes.

Build a coverage map:

| PR change group | Proposed ticket | Action | Evidence or exclusion reason |
| --- | --- | --- | --- |
| User-visible outcome or supporting fix | Title or existing issue | Create / update / link / exclude | PR diff and available verification |

Search Linear, including closed/archived records, using module and outcome keywords, existing child tickets and existing PR links. Follow pagination when needed for the search scope; qualify partial searches. Read promising matches fully.

- Exact or near duplicate: propose reusing the existing ticket and show its identifier, title, current state and intended edits.
- Related but distinct: explain the boundary and propose a related link only when useful.
- No relevant match in the searched scope: propose a new ticket.
- A supporting configuration fix outside the main feature area: list it separately so Ben can include or exclude it.

Use the resolved parent, including ENG-660 for iOS or Portal Mobile by default. For work outside that scope, if several records need a parent and none was supplied, propose a suitable existing parent or a new umbrella in the preview. Moving an existing ticket under a new parent or cycle must be visible in the proposal.

Completion: every PR change group maps to a proposed record or an explicit exclusion, with duplicates resolved at proposal level.

## 3. Preview the complete batch

Show the create/update counts, common metadata and every proposed English title and full body. For existing tickets, show exactly what will be appended or changed, including parent, cycle, assignee and state. Keep the coverage map compact when several groups share a ticket.

Use the ticket-writing skill's Background / Why, Current Behavior, acceptance criteria and Stakeholders structure. Add PR-specific evidence:

- Describe Current Behavior explicitly as the pre-PR baseline when recording work already implemented.
- Explain the resulting behavior in product language. Put technical diagnosis in the Bug or technical section when needed.
- Link the PR and summarize relevant checks and material gaps. Distinguish code implemented, local/static checks, runtime acceptance, CI, merge and deployment. Leave acceptance boxes unchecked unless the supporting result establishes that criterion.
- Use confirmed requirements or reported behavior to define acceptance. Mark inferred criteria for confirmation rather than extending product scope from code alone.
- Include the resolved stakeholders using supported mentions; only claim subscriptions if the tool or read-back confirms them.
- Keep ticket descriptions self-contained for people without the local checkout. Link durable sources instead of local paths, raw logs, private customer data or chat-dependent references.
- Keep original text, media and attachments when extending an existing issue. Place authorized new evidence using the ticket-writing skill's media guidance; explain unavailable evidence instead of claiming an upload.

Wait for confirmation of this concrete batch before writes. A request to create the skill, inspect a PR or draft tickets is not approval to create tickets. If Ben already approved the displayed batch, incorporate his exclusions and wording edits and execute that scope without another approval round. Seek renewed confirmation only for a material addition or conflicting concurrent edit.

## 4. Apply the approved plan

Re-read existing tickets immediately before updating and check for overlapping edits. Recheck the chosen cycle's dates before writes. If a cycle boundary changed its current/next relationship since approval, reconfirm the concrete cycle instead of silently moving tickets. Preserve status unless Ben explicitly requested a change. If the PR head changed since preview, inspect the delta; obtain confirmation for added or materially changed scope.

- Use Linear's current create/update operation and explicit resolved IDs. Attach a link to the PR on each record. Use real newlines in Markdown.
- Create only approved new records. For reuse, prefer a narrow append or anchored patch and apply only the approved metadata changes. Preserve unrelated fields and media.
- Omit state from create/update requests unless Ben explicitly requested it. Apply an authorized status change only to the named records; preserve other children and the parent's status.
- Process writes sequentially and record each returned issue ID, action and PR association in the available work-state tracker before continuing.
- After a timeout or ambiguous failure, search/read the affected record and PR association before retrying. Resume from confirmed successes. If the outcome is still ambiguous, stop that write and report it; do not retry a create blindly.

Completion: each approved action has a known saved record or a specific unresolved outcome. Excluded groups remain excluded on retries and continuations.

## 5. Read back and report

Independently read every saved ticket. Verify title and requested terminology, body, labels, assignee, parent, cycle, effective state and PR link. For reused tickets, verify the original content and media remain. Compare media asset identity and metadata rather than temporary signed URL query strings.

Correct mismatches within the approved scope and re-read them. Report created and updated records with identifiers and links, common metadata, exclusions and any unresolved verification. Close the batch's work-state item only after all approved writes and checks are accounted for.

This workflow records PR work in Linear. Changes to product code, PR content, merge/deployment actions or unrelated ticket statuses need their own requested scope.
