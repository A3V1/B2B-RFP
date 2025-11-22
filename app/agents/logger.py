"""
Terminal logging utility for agent workflow visualization.
Provides colored output and formatted logging for debugging.
"""
from datetime import datetime
from typing import Any, Optional
import json

# ANSI color codes for terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DIM = '\033[2m'


def get_timestamp() -> str:
    """Get formatted timestamp."""
    return datetime.now().strftime("%H:%M:%S")


def log_agent_start(agent_name: str):
    """Log when an agent starts processing."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}[{get_timestamp()}] {Colors.HEADER}▶ {agent_name.upper()} AGENT STARTED{Colors.ENDC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}")


def log_agent_end(agent_name: str, success: bool = True):
    """Log when an agent finishes processing."""
    if success:
        status = f"{Colors.GREEN}✓ COMPLETED{Colors.ENDC}"
    else:
        status = f"{Colors.RED}✗ FAILED{Colors.ENDC}"
    print(f"\n{Colors.BOLD}[{get_timestamp()}] {Colors.HEADER}◼ {agent_name.upper()} AGENT {status}")
    print(f"{Colors.DIM}{'-'*60}{Colors.ENDC}\n")


def log_step(message: str):
    """Log a processing step."""
    print(f"{Colors.BLUE}  → {message}{Colors.ENDC}")


def log_info(label: str, value: Any):
    """Log information with a label."""
    print(f"{Colors.DIM}    {label}: {Colors.ENDC}{value}")


def log_success(message: str):
    """Log a success message."""
    print(f"{Colors.GREEN}  ✓ {message}{Colors.ENDC}")


def log_warning(message: str):
    """Log a warning message."""
    print(f"{Colors.YELLOW}  ⚠ {message}{Colors.ENDC}")


def log_error(message: str):
    """Log an error message."""
    print(f"{Colors.RED}  ✗ {message}{Colors.ENDC}")


def log_data(label: str, data: Any, max_length: int = 200):
    """Log data with truncation for large content."""
    if isinstance(data, (dict, list)):
        data_str = json.dumps(data, indent=2, default=str)
    else:
        data_str = str(data)

    if len(data_str) > max_length:
        data_str = data_str[:max_length] + f"... ({len(data_str)} chars total)"

    print(f"{Colors.DIM}    {label}:{Colors.ENDC}")
    for line in data_str.split('\n')[:10]:  # Limit to 10 lines
        print(f"{Colors.DIM}      {line}{Colors.ENDC}")


def log_llm_call(model: str, prompt_preview: str = ""):
    """Log an LLM API call."""
    print(f"{Colors.YELLOW}  📡 Calling LLM: {model}{Colors.ENDC}")
    if prompt_preview:
        preview = prompt_preview[:100] + "..." if len(prompt_preview) > 100 else prompt_preview
        print(f"{Colors.DIM}      Prompt: {preview}{Colors.ENDC}")


def log_llm_response(response_preview: str = ""):
    """Log LLM response received."""
    preview = response_preview[:200] + "..." if len(response_preview) > 200 else response_preview
    print(f"{Colors.GREEN}  📥 LLM Response received ({len(response_preview)} chars){Colors.ENDC}")
    print(f"{Colors.DIM}      Preview: {preview}{Colors.ENDC}")


def log_section_divider(title: str = ""):
    """Print a section divider."""
    if title:
        print(f"\n{Colors.DIM}  --- {title} ---{Colors.ENDC}")
    else:
        print(f"{Colors.DIM}  {'─'*40}{Colors.ENDC}")


def log_summary_table(headers: list, rows: list):
    """Print a formatted summary table."""
    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    # Print header
    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    print(f"{Colors.BOLD}    {header_line}{Colors.ENDC}")
    print(f"    {'-' * len(header_line)}")

    # Print rows
    for row in rows[:10]:  # Limit to 10 rows
        row_line = " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))
        print(f"    {row_line}")

    if len(rows) > 10:
        print(f"{Colors.DIM}    ... and {len(rows) - 10} more rows{Colors.ENDC}")


def log_workflow_start(rfp_id: str):
    """Log workflow start."""
    print(f"\n{Colors.BOLD}{Colors.GREEN}{'#'*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.GREEN}#  RFP ANALYSIS WORKFLOW STARTED{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.GREEN}#  RFP ID: {rfp_id}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.GREEN}#  Time: {get_timestamp()}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.GREEN}{'#'*60}{Colors.ENDC}\n")


def log_workflow_end(rfp_id: str, success: bool, duration: float = 0):
    """Log workflow end."""
    print(f"\n{Colors.BOLD}{Colors.GREEN}{'#'*60}{Colors.ENDC}")
    if success:
        print(f"{Colors.BOLD}{Colors.GREEN}#  ✓ WORKFLOW COMPLETED SUCCESSFULLY{Colors.ENDC}")
    else:
        print(f"{Colors.BOLD}{Colors.RED}#  ✗ WORKFLOW COMPLETED WITH ERRORS{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.GREEN}#  RFP ID: {rfp_id}{Colors.ENDC}")
    if duration:
        print(f"{Colors.BOLD}{Colors.GREEN}#  Duration: {duration:.2f} seconds{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.GREEN}{'#'*60}{Colors.ENDC}\n")
