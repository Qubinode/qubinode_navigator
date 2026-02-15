---
name: github-issue-resolver
description: Strategically resolves GitHub Actions failures, failed pull requests, and Dependabot issues using the gh CLI. Use when asked to fix CI failures, triage GitHub Actions errors, manage failed PRs, handle Dependabot updates, or perform repository maintenance.
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Grep
  - Glob
  - Task
---

# GitHub Issue Resolver

Automates GitHub repository maintenance: diagnosing and fixing CI failures, managing failed PRs, and handling Dependabot updates using the `gh` CLI.

## Prerequisites

Before starting, verify the environment:

```bash
gh auth status
gh repo view --json nameWithOwner -q .nameWithOwner
```

If `gh` is not authenticated, stop and ask the user to run `gh auth login`.

## Priority Triage Order

Always process issues in this order:

1. **Security vulnerabilities** - Dependabot security alerts and CVE-related PRs
2. **Broken main/master branch** - Failures on the default branch
3. **Blocking PR failures** - PRs with failed required checks
4. **Dependabot updates** - Dependency version bumps
5. **Flaky tests / intermittent failures** - Non-deterministic issues

## Workflow 1: GitHub Actions Failure Resolution

### Step 1: Identify failed runs

```bash
gh run list --status failure --limit 20 --json databaseId,displayTitle,headBranch,conclusion,createdAt,workflowName
```

### Step 2: Analyze failure logs

For each failed run:

```bash
gh run view <run-id> --log-failed 2>&1 | tail -200
```

If logs are truncated, download the full log:

```bash
gh run view <run-id> --log-failed > /tmp/gh-run-<run-id>.log
```

### Step 3: Diagnose the root cause

Classify the failure into one of these categories:

| Category | Indicators | Action |
|----------|-----------|--------|
| Test failure | `FAILED`, `AssertionError`, `pytest` exit code | Read test file, understand assertion, fix code or test |
| Build error | `ModuleNotFoundError`, `SyntaxError`, compilation errors | Fix imports, syntax, or dependency declarations |
| Lint/format | `ruff`, `black`, `flake8`, `shellcheck` violations | Run formatter locally, commit fixes |
| Dependency | `pip install` failures, version conflicts | Update requirements, pin versions |
| Infrastructure | Timeout, runner error, service unavailable | Rerun the workflow - do not change code |
| Permissions | `Permission denied`, token errors | Flag for manual intervention |

### Step 4: Implement fixes

1. Checkout the failing branch: `git checkout <branch>`
2. Make targeted fixes based on diagnosis
3. Run local verification when possible (e.g., `python3 -m pytest`)
4. Commit with message: `fix(ci): <description of fix>`
5. Push and verify: `git push`

### Step 5: Rerun and verify

```bash
gh run rerun <run-id> --failed
gh run watch <run-id>
```

If the rerun fails with the same error, investigate deeper. If it fails with a different error, treat it as a new failure.

## Workflow 2: Failed Pull Request Management

### Step 1: List PRs with failed checks

```bash
gh pr list --state open --json number,title,author,headRefName,statusCheckRollup --jq '.[] | select(.statusCheckRollup != null) | select([.statusCheckRollup[] | select(.conclusion == "FAILURE")] | length > 0) | {number, title, author: .author.login, branch: .headRefName}'
```

### Step 2: Inspect a specific PR

```bash
gh pr checks <pr-number>
gh pr view <pr-number> --json title,body,headRefName,baseRefName,mergeable,mergeStateStatus
gh pr diff <pr-number>
```

### Step 3: Fix the PR

1. Checkout: `gh pr checkout <pr-number>`
2. Analyze failures using `gh pr checks <pr-number> --json` and `gh run view`
3. If the branch is behind base, update it:
   ```bash
   gh pr update-branch <pr-number>
   ```
4. Implement fixes, commit, and push
5. Comment on the PR explaining the fix:
   ```bash
   gh pr comment <pr-number> --body "Fixed CI failure: <explanation>"
   ```

### Step 4: Handle merge conflicts

```bash
gh pr view <pr-number> --json mergeable -q .mergeable
```

If `CONFLICTING`:
1. Checkout the PR branch
2. Merge or rebase the base branch
3. Resolve conflicts
4. Push the resolution
5. Comment explaining the resolution

## Workflow 3: Dependabot Issue Handling

### Step 1: List Dependabot PRs

```bash
gh pr list --author "app/dependabot" --json number,title,labels,createdAt,headRefName --jq 'sort_by(.createdAt)'
```

### Step 2: Categorize updates

Classify each PR by update type:

| Type | Risk | Strategy |
|------|------|----------|
| Security patch (any version) | High priority | Merge immediately after checks pass |
| Patch version (x.y.Z) | Low | Batch and merge |
| Minor version (x.Y.0) | Medium | Review changelog, merge if checks pass |
| Major version (X.0.0) | High | Review breaking changes, test thoroughly |

### Step 3: Check for conflicts and failures

For each Dependabot PR:

```bash
gh pr checks <pr-number>
gh pr view <pr-number> --json mergeable -q .mergeable
```

### Step 4: Handle common Dependabot scenarios

**Checks pass, no conflicts** - Merge:
```bash
gh pr merge <pr-number> --squash --auto
```

**Needs rebase** - Use Dependabot command:
```bash
gh pr comment <pr-number> --body "@dependabot rebase"
```

**Merge conflicts Dependabot cannot resolve**:
1. Checkout the PR branch
2. Resolve conflicts manually
3. Push resolution
4. Let checks run, then merge

**Failed checks on Dependabot PR**:
1. Analyze what broke (API changes, deprecated features)
2. If trivial (import path changes, minor API tweaks): fix in-place
3. If complex (major version breaking changes): comment findings and leave for human review

### Step 5: Batch compatible updates

Group related dependency updates (e.g., multiple `@types/*` packages) and merge them together when possible.

## Workflow 4: Summary and Reporting

After processing, provide a structured report:

```
## Repository Maintenance Report

### Resolved
- [#PR] Description - fix applied

### Merged
- [#PR] Dependabot: package x.y.z -> x.y.w

### Needs Manual Attention
- [#PR] Reason it cannot be auto-resolved

### Rerun (Infrastructure Failures)
- [Run ID] Workflow name - rerun triggered
```

## Safety Guidelines

### Always confirm before:
- Force-pushing any branch
- Closing or merging PRs
- Deleting branches
- Making changes to workflow files (`.github/workflows/`)
- Merging major version Dependabot updates

### Never:
- Force-push to main/master
- Merge PRs with failing required checks without user approval
- Modify secrets or environment variables
- Skip CI checks with `[skip ci]` commits
- Dismiss reviews without user approval

### When to escalate to the user:
- Security-related failures requiring credential rotation
- Persistent failures after 2 fix attempts
- Major version dependency updates with breaking changes
- Workflow file modifications needed
- Merge conflicts in generated files (lockfiles, compiled assets)

## Error Handling

| Error | Recovery |
|-------|----------|
| `gh: Not Found` | Verify repo permissions: `gh repo view` |
| `gh: HTTP 403` | Token lacks required scopes: `gh auth status` |
| Rate limited | Wait and retry: `gh api rate_limit` |
| Rerun fails | Download full logs, analyze offline |
| Branch protected | Cannot push directly - create a new PR with fix |

## Decision Tree: Should I Auto-Fix?

```
Is it a test failure?
├─ Yes: Is the fix obvious (typo, import, assertion update)?
│  ├─ Yes → Fix it
│  └─ No → Report to user
└─ No: Is it a lint/format issue?
   ├─ Yes → Run formatter, commit
   └─ No: Is it a dependency issue?
      ├─ Yes: Is it a patch/minor?
      │  ├─ Yes → Update and test
      │  └─ No → Report to user
      └─ No: Is it infrastructure?
         ├─ Yes → Rerun workflow
         └─ No → Report to user
```
