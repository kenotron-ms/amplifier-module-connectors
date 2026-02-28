# Agent Working Guidelines

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

## Lessons Learned

### 2024-02-27
- **Lesson**: Must verify work before declaring it complete
- **Action**: Created this AGENTS.md document
- **Rule**: Never move to next issue without full verification
- **Rule**: Always test imports, functionality, and regressions
- **Rule**: Keep increments small (1-2 hours max per PR)
- **Rule**: Use two-pizza sub-agent model for complex tasks
- **Rule**: Each sub-agent gets minimal context (< 50 lines of reference code)
