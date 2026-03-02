# Troubleshooting "No Provider Loaded" Errors

## Problem

When using `/amplifier open <project>` in Slack, users may encounter a "no provider loaded" error when sending the first message to the project.

## Root Cause

The error occurs during session creation when the Amplifier CLI's bundle preparation process cannot find provider configuration. This happens because:

1. The `/amplifier open` command associates a thread with a project path
2. Session creation happens **lazily** when the next message arrives
3. The session manager tries to load the project's bundle using `resolve_bundle_config()`
4. If provider configuration is missing or incomplete, bundle preparation fails

## Solution

### Immediate Fix (User)

Ensure `~/.amplifier/settings.yaml` contains provider configuration:

```yaml
providers:
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    default_model: claude-3-5-sonnet-20241022
```

And set the environment variable:

```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Diagnostic Script

Use the provided diagnostic script to check configuration:

```bash
# Check global configuration
python scripts/check-providers.py

# Check project-specific configuration
python scripts/check-providers.py /path/to/project
```

The script will:
- ✅ Verify settings files exist
- ✅ Check provider configuration
- ✅ Validate environment variables
- ✅ Show active bundle
- ✅ Provide fix suggestions

## Code Improvements

The following improvements have been made to provide better error handling:

### 1. Enhanced Session Manager (`src/connector_core/session_manager.py`)

**Before:**
```python
try:
    _, prepared = await resolve_bundle_config(
        bundle_name=load_target,
        app_settings=app_settings,
        console=None,
    )
except Exception as e:
    raise RuntimeError(f"Failed to prepare bundle '{bundle_name}': {e}") from e
```

**After:**
```python
# Validate provider configuration before attempting bundle preparation
try:
    providers = app_settings.get_providers()
    if not providers:
        error_msg = (
            f"No providers configured for project '{project_path or '(default)'}'. "
            f"Please ensure ~/.amplifier/settings.yaml contains provider configuration..."
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    logger.debug(f"Found {len(providers)} provider(s) configured")
except AttributeError:
    logger.debug("Could not validate providers (method not available)")

try:
    _, prepared = await resolve_bundle_config(...)
except Exception as e:
    error_msg = f"Failed to prepare bundle '{bundle_name}': {e}"
    
    # Check if error is provider-related
    if "provider" in str(e).lower() or "api" in str(e).lower():
        error_msg += "\n\nThis may be a provider configuration issue..."
    
    logger.error(error_msg)
    raise RuntimeError(error_msg) from e
```

### 2. Better Error Messages in Slack Bot (`src/slack_connector/bot.py`)

**Before:**
```python
session, lock = await self._get_or_create_session(channel, reply_ts, reply_ts)
```

**After:**
```python
try:
    session, lock = await self._get_or_create_session(channel, reply_ts, reply_ts)
except RuntimeError as e:
    # Post user-friendly error message
    await client.chat_postMessage(
        channel=channel,
        thread_ts=reply_ts,
        text=(
            f":x: *Failed to create session*\n\n"
            f"```{str(e)}```\n\n"
            f"_Please contact your administrator to resolve this configuration issue._"
        ),
    )
    return
```

### 3. Early Validation in `/amplifier open` (`src/slack_connector/commands.py`)

The command now validates provider configuration **before** associating the thread:

```python
# Validate that we can load this project's bundle before associating
try:
    bundle_name = self.session_manager._get_bundle_name(str(project_path))
    
    # Validate provider configuration
    from amplifier_app_cli.lib.settings import AppSettings, SettingsPaths
    paths = SettingsPaths(...)
    app_settings = AppSettings(paths)
    providers = app_settings.get_providers()
    
    if not providers:
        return {
            "success": False,
            "message": (
                f":x: *No providers configured*\n\n"
                f"Please ensure `~/.amplifier/settings.yaml` contains..."
            ),
        }
except Exception as e:
    return {
        "success": False,
        "message": f":x: *Failed to validate project*\n\n{e}",
    }
```

## Settings File Priority

The session manager reads settings in this order (first match wins):

1. **Project local settings**: `<project>/.amplifier/settings.local.yaml`
2. **Project settings**: `<project>/.amplifier/settings.yaml`
3. **Global settings**: `~/.amplifier/settings.yaml`

Provider configuration should typically be in **global settings** (`~/.amplifier/settings.yaml`) to be available for all projects.

## Common Issues

### Issue 1: Missing Global Settings

**Symptom:** "No providers configured" error

**Fix:**
```bash
# Create global settings file
mkdir -p ~/.amplifier
cat > ~/.amplifier/settings.yaml << 'EOF'
providers:
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    default_model: claude-3-5-sonnet-20241022
EOF
```

### Issue 2: Environment Variable Not Set

**Symptom:** Provider configured but API calls fail

**Fix:**
```bash
# Add to ~/.bashrc or ~/.zshrc
export ANTHROPIC_API_KEY=sk-ant-your-key-here

# Or use .env file with the connector
echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" >> .env
```

### Issue 3: Project Overrides Global Settings

**Symptom:** Works globally but not in specific project

**Fix:**
```bash
# Check project settings
cat /path/to/project/.amplifier/settings.yaml
cat /path/to/project/.amplifier/settings.local.yaml

# Either add providers to project settings, or remove overrides
```

## Testing the Fix

1. **Check configuration:**
   ```bash
   python scripts/check-providers.py /path/to/project
   ```

2. **Test in Slack:**
   ```
   /amplifier open my-project
   ```
   
   Should now show clear error if providers are missing, or success if configured correctly.

3. **Send a message:**
   ```
   @bot hello
   ```
   
   Should create session successfully or show helpful error message.

## For Developers

When extending the connector:

1. **Always validate early** - Check configuration in slash commands before associating resources
2. **Provide context** - Include project path, bundle name, and settings file locations in errors
3. **Surface errors clearly** - Use Slack formatting to make errors scannable
4. **Log thoroughly** - Include debug logs for configuration resolution steps

## Related Files

- `src/connector_core/session_manager.py` - Session and bundle management
- `src/slack_connector/commands.py` - Slash command handlers
- `src/slack_connector/bot.py` - Message handling and error surfacing
- `scripts/check-providers.py` - Diagnostic tool
