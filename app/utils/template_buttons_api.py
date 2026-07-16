"""Serialize stored template buttons for API consumers (single color_code + type-only list)."""

DEFAULT_TEMPLATE_BUTTON_COLOR = "#2563eb"


def template_color_code_and_type_only_buttons(
    buttons_json: list | None,
) -> tuple[str, list[dict[str, str]]]:
    raw = buttons_json if isinstance(buttons_json, list) else []
    colors: list[str] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        c = str(item.get("color_code") or "").strip()
        if c:
            colors.append(c)
    unique: list[str] = []
    for c in colors:
        if c not in unique:
            unique.append(c)
    if not unique:
        color_code = DEFAULT_TEMPLATE_BUTTON_COLOR
    else:
        # One field for clients: first distinct color (all match in normal flow).
        color_code = unique[0]
    out: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        t = str(item.get("type") or "").strip().lower()
        if t:
            out.append({"type": t})
    return color_code, out
