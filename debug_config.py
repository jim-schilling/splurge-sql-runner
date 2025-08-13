#!/usr/bin/env python3
"""Debug script to test configuration loading."""

import json
import tempfile
from splurge_sql_runner.config.app_config import AppConfig

def test_config_loading():
    """Test configuration loading with debug output."""
    config_data = {
        "database": {
            "url": "sqlite:///test.db",
            "connection": {"timeout": 60},
            "enable_debug": True,
        }
    }
    
    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        fname = f.name
    
    try:
        # Test JSON parsing directly
        print("Testing JSON parsing...")
        json_config = AppConfig.load_json_file(fname)
        print(f"  JSON URL: {json_config.database.url}")
        print(f"  JSON Timeout: {json_config.database.connection.timeout}")
        print(f"  JSON Debug: {json_config.database.enable_debug}")
        
        # Test full config loading
        print("\nTesting full config loading...")
        config = AppConfig.load(fname)
        print(f"  Final URL: {config.database.url}")
        print(f"  Final Timeout: {config.database.connection.timeout}")
        print(f"  Final Debug: {config.database.enable_debug}")
        
    finally:
        import os
        os.unlink(fname)

if __name__ == "__main__":
    test_config_loading()
