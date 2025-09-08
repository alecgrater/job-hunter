"""
LLM Manager - Abstraction layer for multiple LLM backends.

This module provides a unified interface for both OpenRouter API and local Ollama models,
allowing seamless switching between different LLM providers.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import aiohttp

from ..config import get_llm_config, LLMConfig
from ..utils import get_logger

logger = get_logger(__name__)

@dataclass
class LLMResponse:
    """Standardized response from LLM providers."""
    success: bool
    content: str = ""
    model: str = ""
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate_text(self, prompt: str, system_prompt: str = "", **kwargs) -> LLMResponse:
        """Generate text response."""
        pass
    
    @abstractmethod
    async def generate_structured_response(self, prompt: str, system_prompt: str = "", response_format: Dict[str, str] = None, **kwargs) -> LLMResponse:
        """Generate structured response."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available."""
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Get the model name being used."""
        pass

class OpenRouterProvider(LLMProvider):
    """OpenRouter API provider for various LLM models."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {config.openrouter_api_key}",
            "HTTP-Referer": "http://localhost:8501",
            "X-Title": "AI Job Application Tool",
            "Content-Type": "application/json"
        }
    
    async def generate_text(self, prompt: str, system_prompt: str = "", **kwargs) -> LLMResponse:
        """Generate text response using OpenRouter API."""
        if not self.config.openrouter_api_key:
            return LLMResponse(
                success=False,
                error="OpenRouter API key not configured"
            )
        
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": self.config.default_model,
                "messages": messages,
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data["choices"][0]["message"]["content"]
                        
                        return LLMResponse(
                            success=True,
                            content=content,
                            model=data.get("model", self.config.default_model),
                            usage=data.get("usage", {}),
                            finish_reason=data["choices"][0].get("finish_reason")
                        )
                    else:
                        error_text = await response.text()
                        return LLMResponse(
                            success=False,
                            error=f"OpenRouter API error {response.status}: {error_text}"
                        )
                        
        except Exception as e:
            logger.error(f"Error calling OpenRouter API: {e}")
            return LLMResponse(
                success=False,
                error=f"OpenRouter API error: {str(e)}"
            )
    
    async def generate_structured_response(self, prompt: str, system_prompt: str = "", response_format: Dict[str, str] = None, **kwargs) -> LLMResponse:
        """Generate structured response using OpenRouter API."""
        
        # Add format instructions to the prompt
        if response_format:
            format_instructions = "Respond with a JSON object containing the following fields:\n"
            for field, description in response_format.items():
                format_instructions += f"- {field}: {description}\n"
            
            full_prompt = f"{prompt}\n\n{format_instructions}"
        else:
            full_prompt = prompt
        
        response = await self.generate_text(full_prompt, system_prompt, **kwargs)
        
        if response.success and response_format:
            try:
                # Try to parse JSON from response
                import re
                json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    data = json.loads(json_str)
                    response.data = data
                else:
                    # If no JSON found, create structured data from response
                    response.data = {"response": response.content}
            except json.JSONDecodeError:
                logger.warning("Could not parse structured response as JSON")
                response.data = {"response": response.content}
        
        return response
    
    def is_available(self) -> bool:
        """Check if OpenRouter is available."""
        return bool(self.config.openrouter_api_key)
    
    def get_model_name(self) -> str:
        """Get the model name being used."""
        return self.config.default_model

class OllamaProvider(LLMProvider):
    """Local Ollama provider for running models locally."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.base_url = config.ollama_base_url
    
    async def generate_text(self, prompt: str, system_prompt: str = "", **kwargs) -> LLMResponse:
        """Generate text response using Ollama."""
        if not self.is_available():
            return LLMResponse(
                success=False,
                error="Ollama is not available or configured"
            )
        
        try:
            payload = {
                "model": self.config.local_llm_model,
                "prompt": f"{system_prompt}\n\n{prompt}" if system_prompt else prompt,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", self.config.temperature),
                    "num_predict": kwargs.get("max_tokens", self.config.max_tokens)
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        return LLMResponse(
                            success=True,
                            content=data.get("response", ""),
                            model=self.config.local_llm_model,
                            finish_reason="stop" if data.get("done") else "length"
                        )
                    else:
                        error_text = await response.text()
                        return LLMResponse(
                            success=False,
                            error=f"Ollama API error {response.status}: {error_text}"
                        )
                        
        except Exception as e:
            logger.error(f"Error calling Ollama API: {e}")
            return LLMResponse(
                success=False,
                error=f"Ollama API error: {str(e)}"
            )
    
    async def generate_structured_response(self, prompt: str, system_prompt: str = "", response_format: Dict[str, str] = None, **kwargs) -> LLMResponse:
        """Generate structured response using Ollama."""
        
        # Add format instructions to the prompt
        if response_format:
            format_instructions = "Respond with a JSON object containing the following fields:\n"
            for field, description in response_format.items():
                format_instructions += f"- {field}: {description}\n"
            
            full_prompt = f"{prompt}\n\n{format_instructions}"
        else:
            full_prompt = prompt
        
        response = await self.generate_text(full_prompt, system_prompt, **kwargs)
        
        if response.success and response_format:
            try:
                # Try to parse JSON from response
                import re
                json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    data = json.loads(json_str)
                    response.data = data
                else:
                    # If no JSON found, create structured data from response
                    response.data = {"response": response.content}
            except json.JSONDecodeError:
                logger.warning("Could not parse structured response as JSON")
                response.data = {"response": response.content}
        
        return response
    
    def is_available(self) -> bool:
        """Check if Ollama is available."""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_model_name(self) -> str:
        """Get the model name being used."""
        return self.config.local_llm_model

class LLMManager:
    """Main LLM manager that coordinates different providers."""
    
    def __init__(self):
        self.config = get_llm_config()
        self.providers = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize available providers."""
        # OpenRouter provider
        if self.config.openrouter_api_key:
            self.providers["openrouter"] = OpenRouterProvider(self.config)
        
        # Ollama provider
        if self.config.use_local_llm:
            self.providers["ollama"] = OllamaProvider(self.config)
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers."""
        available = []
        for name, provider in self.providers.items():
            if provider.is_available():
                available.append(name)
        return available
    
    def get_primary_provider(self) -> Optional[LLMProvider]:
        """Get the primary provider to use."""
        # Prefer OpenRouter if available
        if "openrouter" in self.providers and self.providers["openrouter"].is_available():
            return self.providers["openrouter"]
        
        # Fall back to Ollama
        if "ollama" in self.providers and self.providers["ollama"].is_available():
            return self.providers["ollama"]
        
        return None
    
    async def generate_text(self, prompt: str, system_prompt: str = "", **kwargs) -> LLMResponse:
        """Generate text using the primary provider."""
        provider = self.get_primary_provider()
        
        if not provider:
            return LLMResponse(
                success=False,
                error="No LLM providers available"
            )
        
        return await provider.generate_text(prompt, system_prompt, **kwargs)
    
    async def generate_structured_response(self, prompt: str, system_prompt: str = "", response_format: Dict[str, str] = None, **kwargs) -> LLMResponse:
        """Generate structured response using the primary provider."""
        provider = self.get_primary_provider()
        
        if not provider:
            return LLMResponse(
                success=False,
                error="No LLM providers available"
            )
        
        return await provider.generate_structured_response(prompt, system_prompt, response_format, **kwargs)
    
    def get_provider_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about available providers."""
        info = {}
        primary_provider = self.get_primary_provider()
        
        # Check each provider
        for name, provider in self.providers.items():
            info[name] = {
                "name": name,
                "available": provider.is_available(),
                "model": provider.get_model_name(),
                "is_primary": provider == primary_provider
            }
        
        return info

# Global LLM manager instance
_llm_manager = None

def get_llm_manager() -> LLMManager:
    """Get the global LLM manager instance."""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
    return _llm_manager

# Convenience functions
async def generate_text(prompt: str, system_prompt: str = "", **kwargs) -> LLMResponse:
    """Generate text using the global LLM manager."""
    manager = get_llm_manager()
    return await manager.generate_text(prompt, system_prompt, **kwargs)

async def generate_structured_response(prompt: str, system_prompt: str = "", response_format: Dict[str, str] = None, **kwargs) -> LLMResponse:
    """Generate structured response using the global LLM manager."""
    manager = get_llm_manager()
    return await manager.generate_structured_response(prompt, system_prompt, response_format, **kwargs)