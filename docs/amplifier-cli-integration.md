# Amplifier CLI Integration

## Philosophy

**We use the `amplifier-app-cli` Python modules directly, not the CLI script.**

The Amplifier CLI already provides comprehensive settings management, bundle resolution, and provider configuration. Instead of reinventing these capabilities, we import and use the CLI's Python modules as a library.

## What We Use

### 1. Settings Management (`amplifier_app_cli.lib.settings`)

```python
from amplifier_app_cli.lib.settings import AppSettings, SettingsPaths
```

**What it provides:**
- ✅ Reads `~/.amplifier/settings.yaml` (global settings)
- ✅ Reads `<project>/.amplifier/settings.yaml` (project settings)
- ✅ Reads `<project>/.amplifier/settings.local.yaml` (local overrides)
- ✅ Merges settings with correct priority
- ✅ Resolves environment variable references (`${VAR_NAME}`)
- ✅ Provides `get_active_bundle()`, `get_providers()`, `get_added_bundles()`

**How we use it:**
```python
# For a specific project
paths = SettingsPaths(
    global_settings=Path.home() / ".amplifier" / "settings.yaml",
    project_settings=project_dir / ".amplifier" / "settings.yaml",
    local_settings=project_dir / ".amplifier" / "settings.local.yaml",
)
app_settings = AppSettings(paths)

# For global settings only
app_settings = AppSettings()

# Get active bundle name
bundle_name = app_settings.get_active_bundle()  # Returns "foundation" if not set

# Get providers
providers = app_settings.get_providers()  # Returns dict of provider configs
```

### 2. Bundle Resolution (`amplifier_app_cli.runtime.config`)

```python
from amplifier_app_cli.runtime.config import resolve_bundle_config
```

**What it provides:**
- ✅ Discovers bundles (well-known, user-added, filesystem)
- ✅ Downloads and installs git-based bundles
- ✅ Composes app-level behaviors (modes, notifications)
- ✅ **Injects providers from settings** (the key part!)
- ✅ Applies tool and hook overrides
- ✅ Expands environment variable references
- ✅ Returns a `PreparedBundle` ready to create sessions

**How we use it:**
```python
bundle_config, prepared = await resolve_bundle_config(
    bundle_name="foundation",  # or any bundle name/URI
    app_settings=app_settings,
    console=None,  # no CLI UI in daemon mode
)

# prepared is a PreparedBundle instance
session = await prepared.create_session(
    session_id="unique-id",
    approval_system=approval_system,
    display_system=display_system,
    session_cwd=Path("/working/dir"),
)
```

## What We DON'T Reinvent

### ❌ Don't: Manually read YAML files

**Bad:**
```python
import yaml
with open(Path.home() / ".amplifier" / "settings.yaml") as f:
    settings = yaml.safe_load(f)
providers = settings.get("providers", {})
```

**Good:**
```python
from amplifier_app_cli.lib.settings import AppSettings
app_settings = AppSettings()
providers = app_settings.get_providers()
```

### ❌ Don't: Manually resolve environment variables

**Bad:**
```python
import os
api_key = os.environ.get("ANTHROPIC_API_KEY")
```

**Good:**
```python
# AppSettings.get_providers() already resolves ${ANTHROPIC_API_KEY}
providers = app_settings.get_providers()
# providers["anthropic"]["api_key"] is already resolved
```

### ❌ Don't: Manually validate provider configuration

**Bad:**
```python
if not providers:
    raise RuntimeError("No providers configured. Please add to settings.yaml...")
```

**Good:**
```python
# resolve_bundle_config() already validates everything
# Just let it throw its detailed error messages
try:
    _, prepared = await resolve_bundle_config(bundle_name, app_settings)
except Exception as e:
    # e already contains detailed error with context
    logger.error(f"Bundle preparation failed: {e}")
    raise
```

### ❌ Don't: Manually discover or load bundles

**Bad:**
```python
bundle_path = Path.home() / ".amplifier" / "bundles" / bundle_name / "bundle.md"
with open(bundle_path) as f:
    bundle_content = f.read()
```

**Good:**
```python
# resolve_bundle_config() handles all discovery and loading
_, prepared = await resolve_bundle_config(bundle_name, app_settings)
```

## Error Handling Strategy

**Trust the CLI's error messages.** They are detailed and actionable.

```python
# In session_manager.py
try:
    _, prepared = await resolve_bundle_config(
        bundle_name=load_target,
        app_settings=app_settings,
        console=None,
    )
except Exception as e:
    # Just add context about which project failed
    context = f"project: {project_path}" if project_path else "default bundle"
    logger.error(f"Bundle preparation failed ({context}): {e}")
    raise  # Re-raise with original detailed message
```

```python
# In bot.py - surface to user
try:
    session, lock = await self._get_or_create_session(...)
except Exception as e:
    # The error message from CLI is already detailed and helpful
    await client.chat_postMessage(
        channel=channel,
        thread_ts=reply_ts,
        text=f":x: *Failed to create session*\n\n```{str(e)}```",
    )
    return
```

## Settings File Priority

Managed entirely by `AppSettings`:

1. **Project local**: `<project>/.amplifier/settings.local.yaml`
2. **Project**: `<project>/.amplifier/settings.yaml`
3. **Global**: `~/.amplifier/settings.yaml`

First match wins for each setting key.

## Example: Complete Flow

```python
# 1. User runs: /amplifier open /path/to/project
# 2. Command associates thread with project path
project_manager.associate_thread(thread_id, "/path/to/project")

# 3. User sends message: @bot hello
# 4. Bot creates session using CLI modules

# Get project path from thread association
project_path = project_manager.get_thread_project(thread_id)

# Build AppSettings for this project
if project_path:
    paths = SettingsPaths(
        global_settings=Path.home() / ".amplifier" / "settings.yaml",
        project_settings=Path(project_path) / ".amplifier" / "settings.yaml",
        local_settings=Path(project_path) / ".amplifier" / "settings.local.yaml",
    )
    app_settings = AppSettings(paths)
else:
    app_settings = AppSettings()

# Resolve bundle name from settings
bundle_name = app_settings.get_active_bundle()  # e.g., "foundation"

# Prepare bundle (validates providers, loads modules, etc.)
_, prepared = await resolve_bundle_config(
    bundle_name=bundle_name,
    app_settings=app_settings,  # Providers injected here!
    console=None,
)

# Create session
session = await prepared.create_session(
    session_id=f"slack-{channel}-{thread_ts}",
    approval_system=SlackApprovalSystem(...),
    display_system=None,
    session_cwd=Path(project_path or "/default/dir"),
)

# Execute user message
response = await session.execute(user_message)
```

## Benefits of This Approach

1. **✅ DRY** - Don't repeat what the CLI already does
2. **✅ Consistency** - Same behavior as `amplifier run`
3. **✅ Maintenance** - CLI improvements automatically benefit connectors
4. **✅ Error Messages** - CLI provides detailed, actionable errors
5. **✅ Future-proof** - New CLI features (new providers, bundle types) work automatically

## When to Add Logic

Only add connector-specific logic that the CLI doesn't handle:

- **Thread → project associations** (Slack-specific)
- **Workspace management** (Slack-specific)
- **Error surfacing to chat platform** (platform-specific)
- **Platform-specific tools** (slack_reply, todo_list)

Everything else should use the CLI modules.
