---
name: a2b2-daily-changes
description: "Save local daily change records and consolidate all unconsumed records into periodic version notes, with selective screenshots and source archiving. Use for daily or periodic change summaries; excludes implementation and release publication."
---

# Summarize final project changes

Produce a Chinese change record suitable for later version notes. Summarize the resulting behavior, not the sequence of attempts, conversations, or commits.

## Writing standard

Before drafting or revising either a daily record or a periodic summary, read and apply [asd-ste100](/Users/ben/.skills-manager/skills/asd-ste100/SKILL.md). If that path moves, locate the same skill in the available skill catalog. Apply its 18 principles to prose, headings, captions, and draft version notes. Preserve facts, conditions, uncertainty, and exact interface labels. Check terminology, references, sentence structure, and information order before saving. These adapted principles do not establish formal ASD-STE100 compliance.

## Scope and local storage

- For a daily request without a date, resolve the current invocation time in `Asia/Singapore`: before 12:00, summarize the previous calendar day; from 12:00 onward, summarize the current calendar day. This covers morning and evening calls and defines the afternoon default. Use an explicit requested day, inclusive date range, or timezone in preference to these defaults. Resolve the date once at invocation, including across month and year boundaries. State the selected date and the time-based reason in the response.
- For a periodic request without dates, select all daily records not yet consumed by a completed summary. The daily time-of-day rule does not restrict periodic selection. State the resolved dates, timezone, cutoff, repository root, branch, and inspected HEAD.
- Daily inspection uses the current checkout and branch. Periodic selection includes all unconsumed saved daily records for this project, preserving their branch and checkout labels. Inspect another working tree only when explicitly requested.
- Use one fixed local root: `~/agent-docs/a2b2/daily-changes/`. Create these directories when needed:
  - `daily/<daily-id>/report.md` and optional `screenshots/` hold each active daily record. Use `YYYY-MM-DD` as the daily ID; add a branch or checkout suffix to avoid scope collisions.
  - `summaries/<summary-id>/report.md` and optional `screenshots/` hold periodic summaries. Use the covered start date, end date, and creation timestamp as the summary ID to avoid overwriting earlier summaries.
  - `archive/<summary-id>/<daily-id>/` holds consumed daily bundles, including their screenshots.
- Refresh the same scope's active daily record on repeated runs, replacing stale or superseded claims. Preserve records from other branches and checkouts. If the same day was already archived, create an active revision, identify the earlier summary, and distinguish new or corrected outcomes from outcomes already summarized.
- If legacy day files exist directly under the local root, include eligible files during discovery. Migrate each to a daily bundle while preserving its date, scope, content, and image links.
- Keep this skill in `.agents/skills/a2b2-daily-changes/`, its Claude adapter in `.claude/skills/a2b2-daily-changes`, and their exclusion rules in Git's local `info/exclude`. Reports stay outside the repository. Do not add these paths to tracked routers, stage them, or publish them.
- Keep daily records, periodic summaries, screenshots, and archives within the local root. Verify that this root is outside the project's Git worktree. If the user later places it inside the repository, add its exact path to local `info/exclude` and verify exclusion before writing.
- A daily default is a reporting window, not a schedule. Create automation only if separately requested.

## Gather final-state evidence

1. Read the repository guidance. Confirm Git root, branch, HEAD, and working-tree status. Resolve the reporting interval as local midnight at the start through midnight after the final day, with an exclusive upper bound. For today, the cutoff is the inspection time; label the report as current through that time.
2. Inspect local Git history and actual diffs. Use committer timestamps for the time window and the current branch's first-parent history for integration boundaries. Identify the baseline before the interval and the final revision at the cutoff. Compare these revisions to establish the net committed result. Inspect contributing commits when needed to understand intent, renames, merges, and affected behavior. A commit subject alone is insufficient evidence.
3. Check timestamp anomalies or missing history before treating a boundary as exact. A contiguous revision diff can include work outside the date window after a rebase or unusual commit ordering. Describe such limitations, or use explicit user-provided revisions. With no earlier revision, compare against the empty tree. With no net changes, say so rather than listing reverted work as delivered.
4. Inspect staged and unstaged diffs separately from committed history, plus relevant untracked source files after checking their paths. Treat them as a current working-tree snapshot: Git cannot prove when an uncommitted edit was made. Include that snapshot as a separate section for today; do not attribute it to earlier dates. Skip secrets, private client data, generated output, dependencies, and unrelated media. State material inspection gaps, including binary changes that cannot be assessed.
5. Resolve repeated edits, partial reversions, and replacements against the final state. Group one outcome once, even when it spans commits or apps. If pending work changes a committed outcome, explain the current result and its pending portion without counting two improvements. Fully reverted attempts do not become release-note bullets.

Keep repository inspection read-only. Local reports, eligible screenshots, and reversible source archiving belong to this workflow. Code changes, commits, pushes, ticket status changes, external messages, and publication are separate actions.

## Use screenshots selectively

Capture a screenshot only when a new feature or a major modification is difficult to explain clearly with text alone. Bug fixes do not qualify. A mixed daily record may illustrate its qualifying feature, but not its bug-fix entries. Text-only records are the default.

Use an available browser or simulator screenshot tool to capture the relevant implemented state. Existing relevant screenshots may be reused after inspection. Use authorized fixtures and exclude private client data, credentials, and unrelated content. This skill does not authorize starting services, changing live data, or performing account mutations to stage a screenshot. If the state cannot be captured within the authorized environment, describe the limitation in text.

Save images to the owning report bundle's `screenshots/` directory. Inspect each image before including it. Use a descriptive filename, relative Markdown image link, and short caption that names the feature and explains what the image shows. Record the screen, captured state, capture time, and implementation or verification status. A screenshot is visual evidence, not proof that a feature passed tests or shipped.

During consolidation, retain only images needed to explain final new features or major modifications. Copy those images into the summary's own `screenshots/` directory and update its links before archiving source bundles. Keep each report's image links valid after the move.

## Write the record

Use this compact structure, omitting empty optional sections:

```markdown
# Project changes | YYYY-MM-DD

Scope: dates and timezone; cutoff; repository; branch; baseline → final SHA.

## Final committed changes
- [Area] Resulting behavior and its user or operational effect.
  Evidence: relevant file paths and short commit SHAs.

## Current uncommitted changes
- [Area] Current result; staged / unstaged / untracked. Date of change unverified.

## Verification and release state
- Record only checks supported by inspected evidence, with their scope and time.
- State material gaps. Separate implementation, tests, CI, and deployment.

## Draft version notes
- Concise user-facing outcomes supported by the sections above.
```

Write effects in plain Chinese under the writing standard above; keep identifiers in their original language. Render the template headings and field labels in Chinese. Group by feature or app, using added / improved / fixed / removed labels only where useful. Place eligible screenshots next to the outcome they explain. Internal maintenance can remain in the evidence sections unless it has a meaningful release-note effect. Do not infer ticket acceptance, successful tests, CI, deployment, or a version number from a commit. Mark unknown release state as unverified. Label draft bullets based on pending work as uncommitted.

Every substantive outcome needs traceable evidence. A file list or line count does not explain behavior. Avoid sensitive payloads and long raw diffs. If a test is not evidenced, state that verification was not observed; generating this report does not require running application tests.

## Consolidate for version notes

1. Discover active daily records for the current project across recorded branches. By default, select every record not yet consumed by a completed periodic summary, including older unconsumed records. Use each record's content metadata, not its modification time or only the latest summary's date. An explicit date range or branch restriction limits selection; an explicit historical request may also read archived records. If no unconsumed records exist, report that result without creating an empty summary or moving files.
2. Read completed summaries' source lists to detect records already consumed but left in `daily/` after an interrupted archive. Match the daily ID, scope, and SHA-256 of the report bytes. Skip identical consumed records; a changed record is a correction or addition that must be reconciled with the earlier summary. Finish any pending archive of unchanged consumed records only after confirming the completed summary still exists and its links work.
3. Read every selected daily record. Reconcile its claims with the covered period's final Git state. Use a combined net diff only for compatible ancestry. For changes from another branch, check available revisions and whether the changes reached the inspected target branch; preserve the branch-specific status when they did not. Deduplicate repeated outcomes and remove changes later reverted or superseded. For a revised day, include only new outcomes or explicit corrections to the earlier summary. Historical pending snapshots establish only what was observed then; confirm that they landed before describing them as committed. State missing daily coverage, branch divergence, or unavailable Git evidence as limitations. Available Git history may fill evidence gaps, but it does not fabricate a missing daily record.
4. Write a periodic summary using the writing standard and the same evidence and status distinctions as daily records. State the actual source dates, gaps, baseline and final revisions, and cutoff. Use a supplied version label; otherwise call it draft version notes. Preserve unresolved or pending outcomes with their actual status. Include a source list recording each daily ID, scope, SHA-256, and intended archive path. This list is the consumption record for later runs.
5. Copy selected images into the summary bundle. Verify every reported outcome, image, and local link. Link sources at their existing locations; keep intended archive destinations as metadata until moves succeed. Save the complete summary with its completion timestamp and source list before moving any source record. A partial or failed summary does not consume or archive daily records.
6. After successful completion, archive the selected daily bundles by moving them to `archive/<summary-id>/`. Preserve their reports and images; archive is reversible storage, not deletion. Update links in the summary to the archive paths and verify them. Archive only source reports whose bytes still match the recorded hashes. Preserve a source that changed during the run as unconsumed and report the discrepancy. Preserve existing archive destinations instead of overwriting them.

After archiving, `daily/` contains only unconsumed records; completed periodic summaries remain under `summaries/`, and source history remains under `archive/`. If the user requests keeping daily records active, leave them in place while marking their exact revisions consumed in the completed summary. Report archive failures without discarding the completed summary; its source list prevents duplicate consumption on the next run.

Finish when the requested report is saved, every outcome is supported, pending work is separated, image and source links work, and the user has the report's absolute local link. For periodic work, also state the covered dates, source count, and archive result.
