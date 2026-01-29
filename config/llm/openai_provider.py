"""
OpenAI LLM Provider implementation.
Supports GPT-4, GPT-4 Turbo, and structured output via JSON mode.
"""

from typing import Dict, Any, Optional
import json
from openai import OpenAI

from config.llm.base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI provider for GPT-4 models.
    
    Supported models:
    - gpt-4-turbo-preview
    - gpt-4-1106-preview
    - gpt-4
    - gpt-3.5-turbo
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            model: Model identifier (default: gpt-4-turbo-preview)
        """
        super().__init__(api_key, model)
        self.client = OpenAI(api_key=self.api_key)
    
    
    def get_provider_name(self) -> str:
        """Return provider name"""
        return "openai"
    
    
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
        Generate response using OpenAI API.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system instructions
            response_schema: Optional JSON schema for structured output
            temperature: Sampling temperature (0.0 - 1.0)
            max_tokens: Maximum tokens in response
            **kwargs: Additional OpenAI-specific parameters
        
        Returns:
            Standardized response dictionary
        """
        try:
            # Build messages
            messages = []
            
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # If schema provided, instruct model to return JSON
            if response_schema:
                self.validate_schema(response_schema)
                
                # Add JSON instruction to prompt
                schema_instruction = f"\n\nRespond with valid JSON matching this schema:\n{json.dumps(response_schema, indent=2)}"
                prompt_with_schema = prompt + schema_instruction
                
                messages.append({
                    "role": "user",
                    "content": prompt_with_schema
                })
            else:
                messages.append({
                    "role": "user",
                    "content": prompt
                })
            
            # Prepare API call parameters
            api_params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            
            # Enable JSON mode if schema provided (GPT-4 Turbo feature)
            if response_schema and "gpt-4-turbo" in self.model:
                api_params["response_format"] = {"type": "json_object"}
            
            # Add any additional kwargs
            api_params.update(kwargs)
            
            # Make API call
            response = self.client.chat.completions.create(**api_params)
            
            # Extract content
            content = response.choices[0].message.content
            
            # Parse JSON if schema was provided
            if response_schema:
                try:
                    content = json.loads(content)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Failed to parse JSON response: {e}\nContent: {content}")
            
            # Extract usage
            usage = self._extract_usage(response.model_dump())
            
            # Build standardized response
            return self._build_response(
                content=content,
                usage=usage,
                raw_response=response.model_dump()
            )
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    
    def _extract_usage(self, raw_response: Dict[str, Any]) -> Dict[str, int]:
        """
        Extract token usage from OpenAI response.
        
        Args:
            raw_response: Raw OpenAI API response
        
        Returns:
            Token usage dictionary
        """
        usage = raw_response.get("usage", {})
        
        return {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        }