"""
Central configuration management for the procurement orchestrator.
Loads environment variables and provides typed access to settings.
"""

import os
from dotenv import load_dotenv
from typing import Literal

load_dotenv()

# ==========================================
# Database Configuration
# ==========================================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")


# ==========================================
# LLM Provider Configuration
# ==========================================

LLMProvider = Literal["anthropic", "openai", "gemini", "grok"]

LLM_PROVIDER: LLMProvider = os.getenv("LLM_PROVIDER", "anthropic")  # Default to Anthropic

# Validate provider choice
VALID_PROVIDERS = ["anthropic", "openai", "gemini", "grok"]
if LLM_PROVIDER not in VALID_PROVIDERS:
    raise ValueError(f"LLM_PROVIDER must be one of {VALID_PROVIDERS}, got: {LLM_PROVIDER}")


# API Keys (only the selected provider's key is required)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROK_API_KEY = os.getenv("GROK_API_KEY")


# Validate that the selected provider has an API key
def validate_api_keys():
    """Ensure the selected LLM provider has an API key configured"""
    key_mapping = {
        "anthropic": ANTHROPIC_API_KEY,
        "openai": OPENAI_API_KEY,
        "gemini": GOOGLE_API_KEY,
        "grok": GROK_API_KEY
    }
    
    selected_key = key_mapping.get(LLM_PROVIDER)
    
    if not selected_key:
        raise ValueError(
            f"API key for selected provider '{LLM_PROVIDER}' is not configured. "
            f"Set {LLM_PROVIDER.upper()}_API_KEY in your .env file."
        )

# Run validation on import
validate_api_keys()


# ==========================================
# LLM Model Configuration
# ==========================================

# Default models for each provider
DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4-turbo-preview",
    "gemini": "gemini-1.5-pro",
    "grok": "grok-2-latest"
}

# Get model for current provider
LLM_MODEL = os.getenv("LLM_MODEL", DEFAULT_MODELS[LLM_PROVIDER])


# ==========================================
# Application Settings
# ==========================================

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")  # development, staging, production

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Feature Flags
ENABLE_AI_AGENTS = os.getenv("ENABLE_AI_AGENTS", "true").lower() == "true"
ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "false").lower() == "true"


# ==========================================
# Helper Functions
# ==========================================

def get_config_summary() -> dict:
    """Return sanitized config summary (no API keys)"""
    return {
        "environment": ENVIRONMENT,
        "llm_provider": LLM_PROVIDER,
        "llm_model": LLM_MODEL,
        "database_configured": bool(DATABASE_URL),
        "api_key_configured": bool(get_api_key_for_provider(LLM_PROVIDER)),
        "ai_agents_enabled": ENABLE_AI_AGENTS,
        "web_search_enabled": ENABLE_WEB_SEARCH
    }


def get_api_key_for_provider(provider: LLMProvider) -> str:
    """Get API key for specified provider"""
    key_mapping = {
        "anthropic": ANTHROPIC_API_KEY,
        "openai": OPENAI_API_KEY,
        "gemini": GOOGLE_API_KEY,
        "grok": GROK_API_KEY
    }
    
    key = key_mapping.get(provider)
    
    if not key:
        raise ValueError(f"API key for provider '{provider}' is not configured")
    
    return key


# ==========================================
# Print Config on Import (Development Only)
# ==========================================

if ENVIRONMENT == "development":
    print("\n" + "="*60)
    print("  Configuration Loaded")
    print("="*60)
    config = get_config_summary()
    for key, value in config.items():
        print(f"  {key}: {value}")
    print("="*60 + "\n")