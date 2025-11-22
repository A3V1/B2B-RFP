"""
LLM configuration for agents using OpenRouter API.
Supports multiple models through a unified interface.
"""
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# Default model - can be overridden per agent
DEFAULT_MODEL = "x-ai/grok-4.1-fast:free"


class OpenRouterLLM:
    """Wrapper for OpenRouter API to provide consistent interface."""

    def __init__(self, model: str = DEFAULT_MODEL, temperature: float = 0.1):
        self.model = model
        self.temperature = temperature
        self.api_key = OPENROUTER_API_KEY

        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")

    def invoke(self, messages: list) -> "LLMResponse":
        """
        Invoke the model with messages.

        Args:
            messages: List of message objects with 'content' attribute

        Returns:
            Response object with 'content' attribute
        """
        # Convert messages to OpenRouter format (OpenAI-compatible)
        formatted_messages = []
        for msg in messages:
            if hasattr(msg, 'content'):
                content = msg.content
                # Determine role based on message type
                if isinstance(msg, SystemMessage):
                    role = "system"
                elif isinstance(msg, HumanMessage):
                    role = "user"
                else:
                    role = "user"
            elif isinstance(msg, dict):
                content = msg.get('content', str(msg))
                role = msg.get('role', 'user')
            else:
                content = str(msg)
                role = "user"

            formatted_messages.append({
                "role": role,
                "content": content
            })

        # Make API request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",  # Required by OpenRouter
            "X-Title": "B2B-RFP-Analyzer"  # Optional - shows in OpenRouter dashboard
        }

        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": self.temperature,
            "max_tokens": 4096
        }

        # Use httpx for sync request
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                OPENROUTER_BASE_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()

            # Extract content from response
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                return LLMResponse(content)
            else:
                raise ValueError(f"Unexpected response format: {data}")


class LLMResponse:
    """Response wrapper to match expected interface."""

    def __init__(self, content: str):
        self.content = content


class Message:
    """Simple message class."""

    def __init__(self, content: str):
        self.content = content


class SystemMessage(Message):
    """System message (instructions)."""
    pass


class HumanMessage(Message):
    """Human/user message."""
    pass


def get_llm(temperature: float = 0.1, model: str = DEFAULT_MODEL) -> OpenRouterLLM:
    """
    Get configured OpenRouter LLM instance.

    Args:
        temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
        model: Model to use (OpenRouter model ID)

    Returns:
        OpenRouterLLM instance
    """
    return OpenRouterLLM(model=model, temperature=temperature)


# Pre-configured instances for different use cases
def get_parser_llm() -> OpenRouterLLM:
    """LLM for parsing - needs accuracy, low temperature."""
    return get_llm(temperature=0.0, model=DEFAULT_MODEL)


def get_analyzer_llm() -> OpenRouterLLM:
    """LLM for analysis - balanced."""
    return get_llm(temperature=0.1, model=DEFAULT_MODEL)


def get_response_llm() -> OpenRouterLLM:
    """LLM for generating responses - slightly creative."""
    return get_llm(temperature=0.3, model=DEFAULT_MODEL)
