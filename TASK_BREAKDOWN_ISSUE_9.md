# Issue #9: Extract SessionManager - Task Breakdown

**Parent Issue**: #9 - Extract SessionManager from SlackAmplifierBot  
**Estimated Total Time**: 2.5 hours  
**Number of Sub-Tasks**: 7

---

## Sub-Task 9.1: Create SessionManager Skeleton ⏱️ 15 min

**Objective**: Create basic SessionManager class structure with __init__

**Context Needed**:
```python
# From bot.py lines 50-54
self.prepared: Any = None
self.sessions: dict[str, Any] = {}
self.locks: dict[str, asyncio.Lock] = {}
```

**Deliverable**:
- Create `src/connector_core/session_manager.py`
- Define `SessionManager` class
- Add `__init__(self, bundle_path: str)` method
- Initialize: `self.bundle_path`, `self.prepared`, `self.sessions`, `self.locks`

**Acceptance Criteria**:
- [ ] File imports without error
- [ ] Can instantiate: `SessionManager("./bundle.md")`
- [ ] No dependencies on Slack-specific code

**Verification**:
```bash
python3 -c "from src.connector_core.session_manager import SessionManager; sm = SessionManager('./test.md'); print('✅')"
```

---

## Sub-Task 9.2: Add initialize Method ⏱️ 20 min

**Objective**: Add bundle loading/preparation method

**Context Needed**:
```python
# From bot.py lines 66-77 (startup method)
from amplifier_foundation import load_bundle
bundle = await load_bundle(self.bundle_path)
self.prepared = await bundle.prepare()
```

**Deliverable**:
- Add `async def initialize(self) -> None` to SessionManager
- Load bundle and prepare it once
- Store in `self.prepared`

**Acceptance Criteria**:
- [ ] Method signature correct
- [ ] Handles ImportError with helpful message
- [ ] Logs success/failure

**Verification**:
```python
# Mock test (amplifier-foundation not installed)
sm = SessionManager("./bundle.md")
# Check method exists
assert hasattr(sm, 'initialize')
```

---

## Sub-Task 9.3: Add get_or_create_session Method ⏱️ 30 min

**Objective**: Implement session creation and caching logic

**Context Needed**:
```python
# From bot.py lines 168-208 (_get_or_create_session)
# Key logic:
# - Check if session exists in self.sessions
# - If not, create using self.prepared.create_session()
# - Cache session and lock
# - Return (session, lock)
```

**Deliverable**:
- Add `async def get_or_create_session()` to SessionManager
- Parameters: `conversation_id: str, approval_system: Any, display_system: Any | None, platform_tool: Any | None`
- Returns: `tuple[Any, asyncio.Lock]`
- Implement caching logic

**Acceptance Criteria**:
- [ ] Creates new session if not cached
- [ ] Returns cached session if exists
- [ ] Creates lock per conversation
- [ ] Platform-agnostic (no Slack imports)

**Verification**:
```python
# Check method signature
sm = SessionManager("./bundle.md")
assert hasattr(sm, 'get_or_create_session')
```

---

## Sub-Task 9.4: Add close_all Method ⏱️ 15 min

**Objective**: Add cleanup method for all sessions

**Context Needed**:
```python
# From bot.py lines 100-109 (shutdown method)
for conv_id, session in list(self.sessions.items()):
    await session.close()
self.sessions.clear()
self.locks.clear()
```

**Deliverable**:
- Add `async def close_all(self) -> None` to SessionManager
- Close all sessions gracefully
- Clear caches

**Acceptance Criteria**:
- [ ] Closes all sessions
- [ ] Handles errors gracefully
- [ ] Clears sessions and locks dictionaries

---

## Sub-Task 9.5: Write SessionManager Unit Tests ⏱️ 30 min

**Objective**: Create comprehensive tests for SessionManager

**Context Needed**:
- SessionManager API (all methods)
- Test template from `tests/test_models.py`

**Deliverable**:
- Create `tests/test_session_manager.py`
- Tests:
  1. `test_create_session_manager` - instantiation
  2. `test_initialize_without_amplifier` - handles missing dependency
  3. `test_get_or_create_session_caching` - sessions are cached
  4. `test_get_or_create_session_creates_lock` - locks created
  5. `test_close_all` - cleanup works

**Acceptance Criteria**:
- [ ] 5+ tests written
- [ ] Tests use mocks (no real Amplifier dependency)
- [ ] All tests pass

**Verification**:
```bash
python3 -c "from tests.test_session_manager import *; print('✅ Tests import')"
```

---

## Sub-Task 9.6: Verify SessionManager Standalone ⏱️ 10 min

**Objective**: Verify SessionManager works independently

**Context Needed**:
- Complete SessionManager implementation
- All tests

**Deliverable**:
- Verification report showing:
  - Imports work
  - Can instantiate
  - Methods exist
  - No Slack dependencies

**Acceptance Criteria**:
- [ ] `from src.connector_core.session_manager import SessionManager` works
- [ ] No `ImportError` related to Slack
- [ ] Can create instance without Amplifier installed

**Verification Script**:
```bash
cd /Users/ken/workspace/amplifier-module-connectors
python3 -c "
import sys
sys.path.insert(0, '.')
from src.connector_core.session_manager import SessionManager

sm = SessionManager('./bundle.md')
assert sm.bundle_path == './bundle.md'
assert hasattr(sm, 'initialize')
assert hasattr(sm, 'get_or_create_session')
assert hasattr(sm, 'close_all')
print('✅ SessionManager verified!')
"
```

---

## Sub-Task 9.7: Update connector_core Exports ⏱️ 5 min

**Objective**: Add SessionManager to module exports

**Context Needed**:
```python
# Current src/connector_core/__init__.py
from .models import UnifiedMessage
from .protocols import PlatformAdapter, ApprovalPrompt
```

**Deliverable**:
- Update `src/connector_core/__init__.py`
- Add `from .session_manager import SessionManager`
- Add to `__all__`

**Acceptance Criteria**:
- [ ] Can import: `from src.connector_core import SessionManager`
- [ ] All exports work

**Verification**:
```bash
python3 -c "from src.connector_core import UnifiedMessage, PlatformAdapter, SessionManager; print('✅')"
```

---

## Contractor Checklist

Before marking Issue #9 complete:

- [ ] All 7 sub-tasks completed
- [ ] Each sub-task verified independently
- [ ] SessionManager imports without errors
- [ ] SessionManager has no Slack dependencies
- [ ] Tests written and pass
- [ ] Git commits are clean
- [ ] Branch pushed
- [ ] PR created
- [ ] Existing Slack connector still works (no regressions)

---

## Notes

- **Do NOT** refactor SlackAmplifierBot in this issue (that's a separate issue)
- **Do NOT** add any Slack-specific code to SessionManager
- **Keep it platform-agnostic** - SessionManager should work for Teams, Discord, etc.
- **Use Optional typing** for Python 3.9+ compatibility
