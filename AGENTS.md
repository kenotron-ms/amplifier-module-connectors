# Agent Working Guidelines

## Documentation Rules: No Ephemeral Files

### ⛔ NEVER Create Temporary All-Caps Documentation Files

**FORBIDDEN:**
- `TASK_BREAKDOWN_*.md`
- `TODO.md`
- `NOTES.md`
- `PLANNING.md`
- `IMPLEMENTATION_PLAN.md`

**WHY:** These files become stale, create clutter, and duplicate information that belongs in GitHub issues.

### ✅ Instead: Use GitHub Issues

When you're tempted to create a planning/breakdown file, **create a GitHub issue instead**.

**Example: Task Breakdown**

❌ **WRONG:**
```bash
# Create TASK_BREAKDOWN_ISSUE_9.md with 7 sub-tasks
```

✅ **CORRECT:**
```bash
# Create GitHub issue with task breakdown
gh issue create --title "Issue #9 Task Breakdown: SessionManager Sub-Tasks" \
  --body "## Sub-Tasks

### 9.1: Create SessionManager Skeleton (15 min)
- Create src/connector_core/session_manager.py
- Define SessionManager class
- Add __init__ method

### 9.2: Add initialize Method (20 min)
- Add async initialize() method
- Load and prepare bundle

[... rest of breakdown ...]

**Checklist:**
- [ ] Sub-task 9.1 complete
- [ ] Sub-task 9.2 complete
..." \
  --label "task-breakdown"
```

### ✅ When to Use Code Comments vs Issues

**Use Code Comments when:**
- Explaining WHY code works a certain way
- Documenting non-obvious implementation details
- Providing context for future maintainers
- Explaining workarounds or edge cases

```python
# Use Optional[str] instead of str | None for Python 3.9 compatibility
thread_id: Optional[str]
```

**Use GitHub Issues when:**
- Planning work to be done
- Breaking down tasks
- Tracking progress
- Discussing implementation approaches
- Recording decisions

### 📝 GitHub Issue Templates for Common Scenarios

#### Scenario 1: Breaking Down a Large Issue

```bash
gh issue create \
  --title "[Breakdown] Issue #9: SessionManager Implementation" \
  --body "Parent: #9

## Sub-Tasks

- [ ] #[NEW] Create SessionManager skeleton
- [ ] #[NEW] Add initialize method  
- [ ] #[NEW] Add get_or_create_session method
- [ ] #[NEW] Write tests
- [ ] #[NEW] Verify integration

Each sub-task will be created as a separate issue." \
  --label "breakdown,planning"
```

Then create individual sub-task issues:

```bash
gh issue create \
  --title "Sub-task 9.1: Create SessionManager Skeleton" \
  --body "**Parent:** #9
**Time Estimate:** 15 minutes

## Objective
Create basic SessionManager class structure

## Context
\`\`\`python
# From bot.py lines 50-54
self.prepared: Any = None
self.sessions: dict[str, Any] = {}
\`\`\`

## Deliverables
- [ ] Create src/connector_core/session_manager.py
- [ ] Define SessionManager class
- [ ] Add __init__ method

## Acceptance Criteria
- [ ] Imports without error
- [ ] Can instantiate: SessionManager('./bundle.md')

## Verification
\`\`\`bash
python3 -c \"from src.connector_core.session_manager import SessionManager; print('✅')\"
\`\`\`" \
  --label "sub-task" \
  --assignee @me
```

#### Scenario 2: Recording a Decision

```bash
gh issue create \
  --title "[Decision] Use Optional[str] for Python 3.9 Compatibility" \
  --body "## Decision
Use \`Optional[str]\` instead of \`str | None\` union syntax.

## Reasoning
- Python 3.9 doesn't support PEP 604 union syntax
- Project requires Python 3.9+ compatibility
- \`Optional\` from typing module works across all versions

## Impact
- All new code must use \`Optional[T]\` instead of \`T | None\`
- Existing code using \`|\" syntax must be updated

## Related
- #4 UnifiedMessage model
- #6 PlatformAdapter protocol" \
  --label "decision,documentation"
```

#### Scenario 3: Implementation Notes

```bash
gh issue comment 9 --body "## Implementation Notes

Discovered that session management has three parts:
1. Bundle preparation (one-time, expensive)
2. Session caching (per-conversation)
3. Lock management (prevent concurrent execution)

These should all be in SessionManager, not in platform-specific bot code.

**Next Steps:**
- Extract these three concerns into SessionManager
- Make it platform-agnostic (no Slack imports)
- Add comprehensive tests"
```

### 🔍 How to Find Information Later

**Instead of searching through files:**
```bash
# Search issues
gh issue list --label "decision"
gh issue list --label "task-breakdown"
gh issue list --search "SessionManager"
```

**Instead of reading PLANNING.md:**
```bash
# Read issue comments
gh issue view 9 --comments
```

## Two Pizza Rule: Contractor + Sub-Agents Architecture

### Philosophy
The main agent acts as a **contractor** who delegates work to specialized **sub-agents**. Each sub-agent has a small, focused context window and handles ONE specific task. This mirrors the "two pizza team" rule - if you can't feed the team with two pizzas, it's too big.

### Contractor Agent Responsibilities
1. **Break down issues** into atomic sub-tasks (30 min - 1 hour each)
2. **Delegate to sub-agents** with clear, minimal context
3. **Verify sub-agent output** before accepting work
4. **Integrate verified work** into the codebase
5. **Report status** to the user

### Sub-Agent Characteristics
- **Small context**: Only receives what's needed for their specific task
- **Single responsibility**: One clear objective (create file, write test, verify import)
- **Verifiable output**: Must produce testable, demonstrable results
- **No dependencies**: Can work independently without full project context

### Example Sub-Agent Delegation

**Bad (Too Big):**
```
Sub-Agent: "Implement SessionManager and refactor SlackAmplifierBot to use it"
Context: Entire bot.py file (437 lines)
```

**Good (Right Size):**
```
Sub-Agent 1: "Create SessionManager class with __init__ and prepare_bundle method"
Context: Lines 50-54 of bot.py, PreparedBundle type signature

Sub-Agent 2: "Add get_or_create_session method to SessionManager"
Context: SessionManager class stub, lines 168-208 of bot.py

Sub-Agent 3: "Write unit tests for SessionManager"
Context: SessionManager implementation, test template

Sub-Agent 4: "Update SlackAmplifierBot to use SessionManager"
Context: SessionManager API, bot.py session-related methods
```

### Sub-Agent Task Template

```markdown
## Sub-Agent Task: [TASK_NAME]

**Objective**: [One sentence description]

**Context** (minimal):
- File: path/to/file.py
- Lines: 10-20 (only relevant section)
- Dependencies: Class X, method Y

**Deliverable**:
- [ ] Create/modify file Z
- [ ] Add N lines of code
- [ ] Self-verify: imports work

**Acceptance Criteria**:
1. Code imports without error
2. Basic functionality test passes
3. No changes to unrelated code

**Time Box**: 30-60 minutes
```

## Core Principles

### 1. **Small, Verified Increments**
- Work in small, testable increments
- Each change must be independently verifiable
- Never declare work "done" without verification
- Test before committing, not after

### 2. **Verification Requirements**

Before marking any work as complete:

1. **Import Test**: Verify all new modules import correctly
   ```bash
   python3 -c "from src.module import Class; print('✅ Imports work')"
   ```

2. **Functionality Test**: Verify basic functionality works
   ```bash
   python3 -c "from src.module import Class; obj = Class(); obj.method(); print('✅ Works')"
   ```

3. **Backward Compatibility**: Verify existing code still works
   ```bash
   python3 -c "from src.existing import ExistingClass; print('✅ No regressions')"
   ```

4. **Git Status**: Ensure clean state
   ```bash
   git status  # Should show only intended changes
   ```

### 3. **Stability Checks**

After each increment:

- ✅ All new code imports without errors
- ✅ All new code has basic functionality tests
- ✅ Existing code still imports and works
- ✅ Git commits are clean and focused
- ✅ PRs are created with proper descriptions

### 4. **Incremental Development Process**

```
1. Create feature branch
2. Make ONE small change
3. Verify imports work
4. Verify functionality works
5. Verify no regressions
6. Commit with clear message
7. Push branch
8. Create PR
9. STOP and get confirmation before continuing
```

### 5. **Never Skip Verification**

❌ **WRONG:**
```
"I've created the code. It should work. Moving on to next issue..."
```

✅ **CORRECT:**
```
"I've created the code. Let me verify:
1. Imports work ✅
2. Basic functionality works ✅
3. No regressions ✅
4. Committed and pushed ✅
Ready for review before proceeding."
```

## Current Project Status

### Completed & Verified ✅

1. **Issue #4 - UnifiedMessage model**
   - Branch: `feature/issue-4-unified-message-model`
   - PR: #14
   - Verified: ✅ Imports work, functionality works, no regressions
   - Status: Ready for review

2. **Issue #6 - PlatformAdapter protocol**
   - Branch: `feature/issue-6-platform-adapter-protocol`
   - PR: #15
   - Verified: ✅ Imports work, functionality works, protocol conformance works
   - Status: Ready for review

### In Progress 🚧

3. **Issue #9 - SessionManager**
   - Branch: `feature/issue-9-session-manager`
   - Status: Task breakdown complete
   - Sub-tasks: 7 tasks defined (see TASK_BREAKDOWN_ISSUE_9.md)
   - Next: Execute sub-tasks 9.1 - 9.7

### Not Started ⏸️

All other issues from Epic #2

## Verification Script Template

Use this template for each increment:

```bash
#!/bin/bash
# Verification script for [ISSUE_NUMBER]

cd /path/to/repo

# 1. Import test
python3 -c "
import sys
sys.path.insert(0, '.')
from src.new_module import NewClass
print('✅ Imports work')
"

# 2. Functionality test
python3 -c "
import sys
sys.path.insert(0, '.')
from src.new_module import NewClass
obj = NewClass()
result = obj.method()
assert result is not None
print('✅ Functionality works')
"

# 3. Regression test
python3 -c "
import sys
sys.path.insert(0, '.')
from src.existing_module import ExistingClass
print('✅ No regressions')
"

# 4. Git status
git status --short
echo "✅ Git status clean"

echo ""
echo "✅✅✅ All verifications passed!"
```

## Sub-Agent Workflow Example

### Issue #9: Extract SessionManager (Contractor View)

**Contractor breaks down into sub-tasks:**

#### Sub-Task 9.1: Create SessionManager Skeleton
- **Agent**: File Creator
- **Context**: 10 lines from bot.py (lines 50-54, type hints)
- **Output**: `session_manager.py` with class definition and `__init__`
- **Time**: 15 minutes

#### Sub-Task 9.2: Add prepare_bundle Method
- **Agent**: Method Implementer
- **Context**: SessionManager skeleton, lines 66-77 from bot.py
- **Output**: `prepare_bundle()` method
- **Time**: 20 minutes

#### Sub-Task 9.3: Add get_or_create_session Method
- **Agent**: Method Implementer
- **Context**: SessionManager with prepare_bundle, lines 168-208 from bot.py
- **Output**: `get_or_create_session()` method
- **Time**: 30 minutes

#### Sub-Task 9.4: Write SessionManager Tests
- **Agent**: Test Writer
- **Context**: SessionManager API only (not implementation details)
- **Output**: `test_session_manager.py` with 5 tests
- **Time**: 30 minutes

#### Sub-Task 9.5: Verify SessionManager Works
- **Agent**: Verifier
- **Context**: SessionManager code + tests
- **Output**: Verification report (imports, tests pass)
- **Time**: 10 minutes

#### Sub-Task 9.6: Update SlackAmplifierBot
- **Agent**: Refactorer
- **Context**: SessionManager API, bot.py session methods
- **Output**: Modified bot.py using SessionManager
- **Time**: 30 minutes

#### Sub-Task 9.7: Integration Verification
- **Agent**: Integration Tester
- **Context**: Full updated codebase
- **Output**: Verification that Slack bot still works
- **Time**: 15 minutes

**Total**: 7 sub-agents, ~2.5 hours, each task < 1 hour

## Daemon Management

### ⚠️ ALWAYS Use Standard Restart Script

When code changes require restarting the daemon, **ALWAYS** use the standard restart script:

```bash
./restart-daemon.sh
```

**DO NOT:**
- ❌ Use `kill` directly on the process
- ❌ Use `launchctl stop/start` manually
- ❌ Try to restart the daemon with custom commands

**WHY:**
- The restart script handles proper shutdown, unload, reload, and restart sequence
- Ensures clean daemon state
- Works consistently across the project
- Documented and maintained

### Standard Daemon Management Scripts

All daemon management should use these scripts (see `DAEMON.md` for details):

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `./restart-daemon.sh` | **Quick restart** | **After code changes** |
| `./manage-daemon.sh restart` | Full restart with status | Testing new features |
| `./manage-daemon.sh status` | Check daemon status | Verify it's running |
| `./manage-daemon.sh logs` | View recent logs | Debug issues |
| `./manage-daemon.sh follow` | Follow logs live | Watch activity |

### Quick Development Workflow

```bash
# 1. Make code changes
vim src/slack_connector/bridge.py

# 2. Restart daemon (ALWAYS use this)
./restart-daemon.sh

# 3. Watch logs to verify
./manage-daemon.sh follow

# 4. Test in Slack
```

### Platform Detection

To detect the current platform:

```bash
uname -s
# Darwin = macOS
# Linux = Linux server
```

**Important:** 
- On **macOS (Darwin)**: Use the shell scripts above (`./restart-daemon.sh`)
- On **Linux servers**: May use `systemctl` commands (e.g., `sudo systemctl restart amplifier`)

Always check the platform before attempting daemon operations to use the correct method.

## Lessons Learned

### 2024-02-27
- **Lesson**: Must verify work before declaring it complete
- **Action**: Created this AGENTS.md document
- **Rule**: Never move to next issue without full verification
- **Rule**: Always test imports, functionality, and regressions
- **Rule**: Keep increments small (1-2 hours max per PR)
- **Rule**: Use two-pizza sub-agent model for complex tasks
- **Rule**: Each sub-agent gets minimal context (< 50 lines of reference code)
- **Rule**: Restart daemon with `./restart-daemon.sh` after making changes (macOS) or appropriate systemctl command (Linux)

### 2025-01-15
- **Lesson**: Always use standard restart script (`./restart-daemon.sh`), never manual kill/restart
- **Action**: Updated AGENTS.md with clear daemon management guidelines
- **Rule**: Use `./restart-daemon.sh` for all daemon restarts during development
- **Rule**: Use `./manage-daemon.sh` for status checks and log viewing
- **Why**: Ensures clean shutdown/startup sequence, consistent behavior, proper daemon state
