"""
Factory for creating LLM provider instances.
Selects provider based on configuration.
"""

from typing import Optional
from config.llm.base import BaseLLMProvider
from config.llm.openai_provider import OpenAIProvider
from config.settings import (
    LLM_PROVIDER,
    LLM_MODEL,
    get_api_key_for_provider
)


def get_llm_provider(
    provider: Optional[str] = None,
    model: Optional[str] = None
) -> BaseLLMProvider:
    """
    Get configured LLM provider instance.
    
    Args:
        provider: Override configured provider (anthropic, openai, gemini, grok)
        model: Override configured model
    
    Returns:
        Initialized provider instance
    
    Raises:
        ValueError: If provider is not supported
    
    Example:
        >>> provider = get_llm_provider()
        >>> response = provider.generate("What is the capital of France?")
    """
    # Use config defaults if not overridden
    selected_provider = provider or LLM_PROVIDER
    selected_model = model or LLM_MODEL
    
    # Get API key for provider
    api_key = get_api_key_for_provider(selected_provider)
    
    # Instantiate provider
    if selected_provider == "openai":
        return OpenAIProvider(api_key=api_key, model=selected_model)
    
    # TODO: Add other providers
    # elif selected_provider == "anthropic":
    #     return AnthropicProvider(api_key=api_key, model=selected_model)
    # elif selected_provider == "gemini":
    #     return GeminiProvider(api_key=api_key, model=selected_model)
    # elif selected_provider == "grok":
    #     return GrokProvider(api_key=api_key, model=selected_model)
    
    else:
        raise ValueError(
            f"Unsupported LLM provider: {selected_provider}. "
            f"Currently supported: openai (more coming soon)"
        )