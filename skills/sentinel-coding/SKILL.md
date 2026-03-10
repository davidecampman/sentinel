---
name: "sentinel-coding"
description: "Coding workflow skill for the Sentinel project. Provides project conventions, test commands, git workflow, and file locations for the Agent Zero Corporate Edition codebase. Load this when working on Sentinel development tasks."
version: "1.0.0"
author: "David Campman"
tags: ["coding", "workflow", "sentinel", "git", "testing", "python"]
trigger_patterns:
  - "sentinel"
  - "coding workflow"
  - "run tests"
  - "commit changes"
  - "project conventions"
---

# Sentinel Coding Workflow

## Project Location
```
/a0/usr/projects/agent_zero_corporate_edition/agentzero/
```
Always `cd` here before running any project commands.

## Key File Locations

| Path | Purpose |
|------|---------|
| `python/helpers/` | Core Python utilities (settings, tls, agent config) |
| `python/tools/` | Agent tools (browser_agent, code_execution, etc.) |
| `python/extensions/` | Extension hooks |
| `python/api/` | Flask API endpoints |
| `webui/components/` | Frontend Vue/Alpine components |
| `agents/*/` | Agent profile context files |
| `tests/` | All test files |
| `skills/` | Project-level skills |
| `docker/` | Dockerfile and Docker configs |
| `usr/.env` | Runtime environment (gitignored) |
| `.env.example` | Environment variable template |

## Running Tests
```bash
cd /a0/usr/projects/agent_zero_corporate_edition/agentzero
./run_tests.sh           # run all security/unit tests
./run_tests.sh -v        # verbose output
./run_tests.sh -k tls    # run specific tests by keyword
pytest tests/ -v         # run full test suite (may need stubs)
```

## Build & Deploy
```bash
./build.sh                          # build Docker image locally
./build.sh --push username          # build + push to Docker Hub
./stop.sh && ./run.sh               # restart with current image
./test.sh                           # start test instance on port 50081
./test.sh --stop                    # stop test instance
```

## Git Workflow
```bash
# Always work from project root
cd /a0/usr/projects/agent_zero_corporate_edition/agentzero

# Check status before starting
git status
git log --oneline -5

# Stage and commit
git add -A
git commit -m "type: short description"
git push origin main
```

### Commit Types
| Type | When to Use |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code restructure, no behavior change |
| `test` | Adding or fixing tests |
| `docs` | Documentation only |
| `chore` | Config, build, deps |
| `security` | Security hardening |

## Project Conventions

### Python
- No hardcoded secrets — always use `os.getenv("VAR_NAME")`
- Input validation on all functions accepting external data
- Document changes vs upstream Agent Zero in comments: `# SENTINEL: <reason>`
- Prefer lazy imports for optional dependencies
- Follow existing file/class naming patterns

### Security
- All new endpoints must require authentication
- Sanitize user inputs before passing to LLM prompts
- Never log secrets or tokens
- Check OWASP Top 10 for any web-facing changes

### Frontend
- Components live in `webui/components/`
- Alpine.js for reactivity, no heavy framework
- Follow existing Sentinel teal (`#2DD4BF`) color scheme
- Test in both light and dark mode

## Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `AWS_ACCESS_KEY_ID` | Bedrock auth | Yes |
| `AWS_SECRET_ACCESS_KEY` | Bedrock auth | Yes |
| `AWS_DEFAULT_REGION` | Bedrock region | Yes |
| `A0_AUTH_LOGIN` | UI login username | Recommended |
| `A0_AUTH_PASSWORD` | UI login password | Recommended |
| `PORT` | Host port mapping | Optional (default 80) |
| `COMPOSE_PROJECT_NAME` | Docker namespace for multi-instance | Optional |

## Upstream Sync

This is a fork of https://github.com/agent0ai/agent-zero

To check for upstream changes:
```bash
git remote -v  # check if upstream remote exists
git fetch upstream
git log upstream/main --oneline -10  # see what's new
```

When merging upstream:
- Preserve all `# SENTINEL:` annotated changes
- Reapply branding (agents/_context.md, webui branding)
- Re-verify security hardening wasn't reverted
- Run `./run_tests.sh` after merge
