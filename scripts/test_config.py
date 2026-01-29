"""
Test configuration loading.
"""

from config import get_config_summary

if __name__ == "__main__":
    print("\n🔧 Testing Configuration System\n")
    
    config = get_config_summary()
    
    for key, value in config.items():
        print(f"  ✓ {key}: {value}")
    
    print("\n✅ Configuration loaded successfully\n")