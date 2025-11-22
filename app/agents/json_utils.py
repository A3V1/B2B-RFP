"""
Robust JSON extraction utilities for LLM responses.
Handles common issues like unescaped characters, truncated responses, etc.
"""
import json
import re
from typing import Any


def fix_json_strings(json_text: str) -> str:
    """
    Fix common JSON string issues like unescaped newlines inside strings.
    Walks through the JSON character by character and escapes problematic chars.
    """
    result = []
    in_string = False
    escape_next = False
    i = 0

    while i < len(json_text):
        char = json_text[i]

        if escape_next:
            result.append(char)
            escape_next = False
            i += 1
            continue

        if char == '\\':
            result.append(char)
            escape_next = True
            i += 1
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            result.append(char)
            i += 1
            continue

        if in_string:
            # Replace actual newlines/tabs with escaped versions inside strings
            if char == '\n':
                result.append('\\n')
            elif char == '\r':
                result.append('\\r')
            elif char == '\t':
                result.append('\\t')
            elif ord(char) < 32:
                # Skip other control characters
                pass
            else:
                result.append(char)
        else:
            result.append(char)

        i += 1

    return ''.join(result)


def extract_json_from_response(response_text: str) -> dict:
    """
    Robustly extract JSON from LLM response.
    Tries multiple strategies to parse potentially malformed JSON.

    Args:
        response_text: Raw LLM response text

    Returns:
        Parsed JSON as dictionary

    Raises:
        json.JSONDecodeError: If all parsing strategies fail
    """
    if not response_text or not response_text.strip():
        return {}

    # Step 1: Extract from code blocks
    if "```json" in response_text:
        match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if match:
            response_text = match.group(1)
    elif "```" in response_text:
        match = re.search(r'```\s*(.*?)\s*```', response_text, re.DOTALL)
        if match:
            response_text = match.group(1)

    response_text = response_text.strip()

    # Step 2: Fix trailing commas
    response_text = re.sub(r',\s*}', '}', response_text)
    response_text = re.sub(r',\s*]', ']', response_text)

    # Step 3: Try to parse as-is first
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # Step 4: Try fixing string issues (unescaped newlines)
    try:
        fixed_text = fix_json_strings(response_text)
        return json.loads(fixed_text)
    except json.JSONDecodeError:
        pass

    # Step 5: Try to find and extract just the JSON object
    try:
        start = response_text.find('{')
        end = response_text.rfind('}')
        if start != -1 and end != -1 and end > start:
            json_substr = response_text[start:end+1]
            fixed_substr = fix_json_strings(json_substr)
            return json.loads(fixed_substr)
    except json.JSONDecodeError:
        pass

    # Step 6: Try with more aggressive cleaning - collapse all whitespace
    try:
        cleaned = re.sub(r'\s+', ' ', response_text)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Step 7: Try to repair truncated JSON by closing brackets
    try:
        repaired = repair_truncated_json(response_text)
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # If all else fails, raise the original error for debugging
    return json.loads(response_text)


def repair_truncated_json(json_text: str) -> str:
    """
    Attempt to repair truncated JSON by adding missing closing brackets.
    """
    json_text = json_text.strip()

    # Count brackets
    open_braces = json_text.count('{')
    close_braces = json_text.count('}')
    open_brackets = json_text.count('[')
    close_brackets = json_text.count(']')

    # Check if we're inside a string (unbalanced quotes)
    quote_count = json_text.count('"') - json_text.count('\\"')
    if quote_count % 2 != 0:
        # We're inside a string, close it
        json_text = json_text + '"'

    # Add missing closing brackets
    missing_braces = open_braces - close_braces
    missing_brackets = open_brackets - close_brackets

    # Add closing brackets in reverse order of what's likely open
    # This is a heuristic - may not always be correct
    for _ in range(missing_brackets):
        json_text = json_text + ']'
    for _ in range(missing_braces):
        json_text = json_text + '}'

    return json_text


def sanitize_for_json(obj: Any) -> Any:
    """
    Recursively sanitize an object for safe JSON serialization.
    Removes control characters that cause JSON parsing errors.

    Args:
        obj: Object to sanitize (dict, list, str, or other)

    Returns:
        Sanitized object safe for JSON serialization
    """
    if isinstance(obj, str):
        # Remove control characters except \n, \r, \t
        sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', obj)
        # Truncate very long strings to prevent token overflow
        if len(sanitized) > 1000:
            sanitized = sanitized[:1000] + "..."
        return sanitized
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    return obj
