"""
LLM configuration for agents using Google Gemini directly.
"""
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# Configure API key globally
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)


class GeminiLLM:
    """Wrapper for Google Gemini to provide consistent interface."""

    def __init__(self, model: str = "gemini-2.5-flash-lite", temperature: float = 0.1):
        self.model_name = model
        self.temperature = temperature
        self.model = genai.GenerativeModel(
            model_name=model,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
            )
        )

    def invoke(self, messages: list) -> "GeminiResponse":
        """
        Invoke the model with messages.

        Args:
            messages: List of message objects with 'content' attribute

        Returns:
            Response object with 'content' attribute
        """
        # Convert messages to Gemini format
        prompt_parts = []
        for msg in messages:
            if hasattr(msg, 'content'):
                content = msg.content
            elif isinstance(msg, dict):
                content = msg.get('content', str(msg))
            else:
                content = str(msg)
            prompt_parts.append(content)

        full_prompt = "\n\n".join(prompt_parts)

        response = self.model.generate_content(full_prompt)
        return GeminiResponse(response.text)


class GeminiResponse:
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


def get_llm(temperature: float = 0.1, model: str = "gemini-2.5-flash-lite") -> GeminiLLM:
    """
    Get configured Gemini LLM instance.

    Args:
        temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
        model: Gemini model to use

    Returns:
        GeminiLLM instance
    """
    if not os.getenv("GOOGLE_API_KEY"):
        raise ValueError("GOOGLE_API_KEY not found in environment variables")

    return GeminiLLM(model=model, temperature=temperature)


# Pre-configured instances for different use cases
# Using gemini-2.5-flash-lite (fast & efficient)
def get_parser_llm() -> GeminiLLM:
    """LLM for parsing - needs accuracy, low temperature."""
    return get_llm(temperature=0.0, model="gemini-2.5-flash-lite")


def get_analyzer_llm() -> GeminiLLM:
    """LLM for analysis - balanced."""
    return get_llm(temperature=0.1, model="gemini-2.5-flash-lite")


def get_response_llm() -> GeminiLLM:
    """LLM for generating responses - slightly creative."""
    return get_llm(temperature=0.3, model="gemini-2.5-flash-lite")
