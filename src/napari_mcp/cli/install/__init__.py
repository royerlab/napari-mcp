"""Installation commands for various LLM applications."""

from .claude_desktop import ClaudeDesktopInstaller
from .claude_code import ClaudeCodeInstaller
from .cursor import CursorInstaller
from .cline_vscode import ClineVSCodeInstaller
from .cline_cursor import ClineCursorInstaller
from .gemini_cli import GeminiCLIInstaller
from .codex_cli import CodexCLIInstaller

__all__ = [
    "ClaudeDesktopInstaller",
    "ClaudeCodeInstaller",
    "CursorInstaller",
    "ClineVSCodeInstaller",
    "ClineCursorInstaller",
    "GeminiCLIInstaller",
    "CodexCLIInstaller",
]