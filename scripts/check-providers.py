#!/usr/bin/env python3
"""
Diagnostic script to check provider configuration for Amplifier projects.

Usage:
    python scripts/check-providers.py [project-path]
    
If no project-path is provided, checks global configuration only.
"""

import sys
from pathlib import Path


def check_providers(project_path=None):
    """Check provider configuration for a project or globally."""
    
    print("=" * 70)
    print("Amplifier Provider Configuration Check")
    print("=" * 70)
    print()
    
    try:
        from amplifier_app_cli.lib.settings import AppSettings, SettingsPaths
    except ImportError:
        print("❌ ERROR: amplifier_app_cli is not installed")
        print("   Please ensure you are running within the amplifier uv environment")
        return False
    
    # Build settings paths
    if project_path:
        project_dir = Path(project_path).expanduser().resolve()
        if not project_dir.exists():
            print(f"❌ ERROR: Project path does not exist: {project_dir}")
            return False
        if not project_dir.is_dir():
            print(f"❌ ERROR: Not a directory: {project_dir}")
            return False
            
        print(f"📁 Project: {project_dir}")
        print()
        
        paths = SettingsPaths(
            global_settings=Path.home() / ".amplifier" / "settings.yaml",
            project_settings=project_dir / ".amplifier" / "settings.yaml",
            local_settings=project_dir / ".amplifier" / "settings.local.yaml",
        )
        app_settings = AppSettings(paths)
    else:
        print("🌍 Checking global configuration only")
        print()
        app_settings = AppSettings()
    
    # Check settings files
    print("📄 Settings files:")
    global_settings = Path.home() / ".amplifier" / "settings.yaml"
    print(f"   Global:  {global_settings}")
    print(f"            {'✅ exists' if global_settings.exists() else '❌ NOT FOUND'}")
    
    if project_path:
        project_settings = project_dir / ".amplifier" / "settings.yaml"
        local_settings = project_dir / ".amplifier" / "settings.local.yaml"
        print(f"   Project: {project_settings}")
        print(f"            {'✅ exists' if project_settings.exists() else '⚪ not present'}")
        print(f"   Local:   {local_settings}")
        print(f"            {'✅ exists' if local_settings.exists() else '⚪ not present'}")
    print()
    
    # Check active bundle
    try:
        bundle = app_settings.get_active_bundle()
        print(f"📦 Active bundle: {bundle or '(none - will use foundation)'}")
        print()
    except Exception as e:
        print(f"⚠️  Could not determine active bundle: {e}")
        print()
    
    # Check providers
    print("🔌 Provider configuration:")
    try:
        providers = app_settings.get_providers()
        
        if not providers:
            print("   ❌ NO PROVIDERS CONFIGURED")
            print()
            print("   To fix this, add to ~/.amplifier/settings.yaml:")
            print()
            print("   providers:")
            print("     anthropic:")
            print("       api_key: ${ANTHROPIC_API_KEY}")
            print("       default_model: claude-3-5-sonnet-20241022")
            print()
            return False
        
        print(f"   ✅ Found {len(providers)} provider(s):")
        for name, config in providers.items():
            print(f"      • {name}")
            if isinstance(config, dict):
                for key, value in config.items():
                    if "key" in key.lower() or "secret" in key.lower():
                        # Mask sensitive values
                        display = "***" if value else "(not set)"
                    else:
                        display = value
                    print(f"         - {key}: {display}")
        print()
        
    except AttributeError:
        print("   ⚠️  get_providers() method not available (old version?)")
        print()
    except Exception as e:
        print(f"   ❌ Error checking providers: {e}")
        print()
        return False
    
    # Check environment variables
    import os
    print("🔐 Environment variables:")
    env_vars = ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "AZURE_OPENAI_API_KEY"]
    found_any = False
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            print(f"   ✅ {var}: {'*' * 10} (set)")
            found_any = True
        else:
            print(f"   ⚪ {var}: (not set)")
    
    if not found_any:
        print()
        print("   ⚠️  No API key environment variables found")
        print("   Make sure to export the required API keys before running the connector")
    print()
    
    print("=" * 70)
    print("✅ Configuration check complete")
    print("=" * 70)
    
    return True


if __name__ == "__main__":
    project_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    success = check_providers(project_path)
    sys.exit(0 if success else 1)
