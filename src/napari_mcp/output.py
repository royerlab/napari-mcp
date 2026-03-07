"""Output storage and truncation utilities."""

from __future__ import annotations


def truncate_output(output: str, line_limit: int) -> tuple[str, bool]:
    """Truncate output to specified line limit.

    Parameters
    ----------
    output : str
        The output text to truncate.
    line_limit : int
        Maximum number of lines to return. If -1, return all lines.

    Returns
    -------
    tuple[str, bool]
        Tuple of (truncated_output, was_truncated).
    """
    try:
        line_limit = int(line_limit)
    except Exception:
        line_limit = 30
    if line_limit < -1:
        line_limit = -1
    if line_limit == -1:
        return output, False

    lines = output.splitlines(keepends=True)
    if len(lines) <= line_limit:
        return output, False

    truncated = "".join(lines[:line_limit])
    return truncated, True
