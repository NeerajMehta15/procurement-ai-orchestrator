"""
Abstract base class for LLM providers.
Defines the interface that all providers (Anthropic, OpenAI, Gemini, Grok) must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime


class BaseLLMProvider(ABC):
    """
    Abstract interface for LLM providers.
    
    All providers must implement:
    - generate() - Main text generation with structured output support
    - get_provider_name() - Return provider identifier
    """
    
    def __init__(self, api_key: str, model: str):
        """
        Initialize the LLM provider.
        
        Args:
            api_key: API key for the provider
            model: Model identifier (e.g., "claude-sonnet-4-20250514")
        """
        self.api_key = api_key
        self.model = model
        self._validate_api_key()
    
    
    def _validate_api_key(self) -> None:
        """Validate that API key is provided"""
        if not self.api_key:
            raise ValueError(f"{self.get_provider_name()} API key is required")
    
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_schema: Optional[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: User prompt/query
            system_prompt: Optional system instructions
            response_schema: Optional JSON schema for structured output
            temperature: Sampling temperature (0.0 - 1.0)
            max_tokens: Maximum tokens in response
            **kwargs: Provider-specific parameters
        
        Returns:
            {
                "content": str | dict,  # Text or structured JSON if schema provided
                "model": str,
                "provider": str,
                "usage": {
                    "prompt_tokens": int,
                    "completion_tokens": int,
                    "total_tokens": int
                },
                "generated_at": str (ISO datetime),
                "raw_response": dict  # Original API response
            }
        """
        pass
    
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the provider name (e.g., 'anthropic', 'openai')"""
        pass
    
    
    def _build_response(
        self,
        content: Any,
        usage: Dict[str, int],
        raw_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build standardized response format.
        
        Args:
            content: Generated content (text or structured data)
            usage: Token usage statistics
            raw_response: Original API response
        
        Returns:
            Standardized response dictionary
        """
        return {
            "content": content,
            "model": self.model,
            "provider": self.get_provider_name(),
            "usage": usage,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "raw_response": raw_response
        }
    
    
    def _extract_usage(self, raw_response: Dict[str, Any]) -> Dict[str, int]:
        """
        Extract token usage from provider-specific response format.
        Override this in subclasses if provider has different usage format.
        
        Returns:
            {
                "prompt_tokens": int,
                "completion_tokens": int,
                "total_tokens": int
            }
        """
        # Default implementation - override in subclasses
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    
    
    def validate_schema(self, schema: Dict[str, Any]) -> bool:
        """
        Validate JSON schema format.
        Basic validation - providers may implement stricter checks.
        
        Args:
            schema: JSON schema dictionary
        
        Returns:
            True if valid, raises ValueError if invalid
        """
        if not isinstance(schema, dict):
            raise ValueError("Schema must be a dictionary")
        
        # Basic required fields for JSON schema
        if "type" not in schema:
            raise ValueError("Schema must have 'type' field")
        
        return True
    
    
    def __repr__(self) -> str:
        """String representation of provider"""
        return f"{self.__class__.__name__}(model={self.model})"