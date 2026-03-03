"""Template rendering — str.replace for __PLACEHOLDER__ tokens, atomic write + chmod."""

from __future__ import annotations

import re
from pathlib import Path


class TemplateError(Exception):
    """Raised when template rendering fails."""


def render_template(
    template_path: Path,
    output_path: Path,
    placeholders: dict[str, str],
    mode: int = 0o700,
) -> None:
    """Render a template file by substituting __PLACEHOLDER__ tokens.

    Args:
        template_path: Path to the template file.
        output_path: Where to write the rendered output.
        placeholders: Mapping of placeholder names (without __) to values.
        mode: File permissions for the output file (default: 700).

    Raises:
        TemplateError: If the template is missing or has unsubstituted placeholders.
    """
    if not template_path.is_file():
        raise TemplateError(f"Template not found: {template_path}")

    content = template_path.read_text()

    for key, value in placeholders.items():
        token = f"__{key}__"
        content = content.replace(token, value)

    # Verify no unsubstituted placeholders remain
    remaining = re.findall(r"__[A-Z_]+__", content)
    if remaining:
        unique = sorted(set(remaining))
        raise TemplateError(
            f"Unsubstituted placeholders in {template_path.name}: {', '.join(unique)}"
        )

    # Atomic write with correct permissions
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(".tmp")
    tmp_path.write_text(content)
    tmp_path.chmod(mode)
    tmp_path.rename(output_path)
