"""
Visual theme: colour palette, font definitions, avatar helpers.
"""

C = {
    "bg":       "#16161e",
    "surface":  "#1e1f2b",
    "border":   "#2b2d3d",
    "accent":   "#8b5cf6",
    "accent2":  "#a78bfa",
    "danger":   "#c0392b",
    "text":     "#e8e8f0",
    "muted":    "#6b6b80",
    "entry_bg": "#1a1b27",
    "hover":    "#262838",
    "green":    "#2ecc71",
    "warn":     "#e67e22",
}

FONT_TITLE   = ("Segoe UI", 22, "bold")
FONT_BODY    = ("Segoe UI", 10)
FONT_MONO    = ("Consolas", 10)
FONT_SMALL   = ("Segoe UI", 9)
FONT_BUTTON  = ("Segoe UI", 10, "bold")
FONT_SERVICE = ("Segoe UI", 11, "bold")
FONT_USER    = ("Segoe UI", 9)

AVATAR_COLORS = [
    "#6366f1", "#8b5cf6", "#ec4899", "#f43f5e",
    "#f97316", "#eab308", "#22c55e", "#14b8a6",
    "#06b6d4", "#3b82f6",
]


def avatar_color(service: str) -> str:
    """Deterministic soft color for a service avatar."""
    return AVATAR_COLORS[hash(service.lower()) % len(AVATAR_COLORS)]
