# Agent Working Guidelines

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
   - Status: Branch created, no code yet
   - Next: Extract session management from SlackAmplifierBot

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

## Lessons Learned

### 2024-02-27
- **Lesson**: Must verify work before declaring it complete
- **Action**: Created this AGENTS.md document
- **Rule**: Never move to next issue without full verification
- **Rule**: Always test imports, functionality, and regressions
- **Rule**: Keep increments small (1-2 hours max per PR)
