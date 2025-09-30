"""Installation commands for various LLM applications."""

from .claude_code import ClaudeCodeInstaller
from .claude_desktop import ClaudeDesktopInstaller
from .cline_cursor import ClineCursorInstaller
from .cline_vscode import ClineVSCodeInstaller
from .codex_cli import CodexCLIInstaller
from .cursor import CursorInstaller
from .gemini_cli import GeminiCLIInstaller

__all__ = [
    "ClaudeDesktopInstaller",
    "ClaudeCodeInstaller",
    "CursorInstaller",
    "ClineVSCodeInstaller",
    "ClineCursorInstaller",
    "GeminiCLIInstaller",
    "CodexCLIInstaller",
]
