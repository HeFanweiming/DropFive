"""Small custom controls used by the DropFive window."""

import tkinter as tk
from collections.abc import Callable

from dropfive.ui import theme


class ActionButton(tk.Canvas):
    """Rounded canvas button with hover, focus, and disabled states."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        text: str,
        icon: str,
        command: Callable[[], None],
        background: str,
        variant: str = "primary",
        width: int = 232,
        height: int = 48,
    ) -> None:
        super().__init__(
            master,
            width=width,
            height=height,
            background=background,
            highlightthickness=0,
            borderwidth=0,
            takefocus=True,
        )
        self._text = text
        self._icon = icon
        self._command = command
        self._background = background
        self._variant = variant
        self._width_hint = width
        self._height_hint = height
        self._enabled = True
        self._hovered = False
        self._pressed = False
        self._focused = False

        self.bind("<Configure>", self._handle_configure)
        self.bind("<Enter>", self._handle_enter)
        self.bind("<Leave>", self._handle_leave)
        self.bind("<Button-1>", self._handle_press)
        self.bind("<ButtonRelease-1>", self._handle_release)
        self.bind("<FocusIn>", self._handle_focus_in)
        self.bind("<FocusOut>", self._handle_focus_out)
        self.bind("<Return>", self._handle_keyboard)
        self.bind("<space>", self._handle_keyboard)
        self.configure(cursor="hand2")
        self._draw()

    def set_enabled(self, enabled: bool) -> None:
        if self._enabled == enabled:
            return
        self._enabled = enabled
        self._hovered = False
        self._pressed = False
        self.configure(cursor="hand2" if enabled else "arrow")
        self._draw()

    def invoke(self) -> None:
        if self._enabled:
            self._command()

    def _handle_configure(self, _event: tk.Event) -> None:
        self._draw()

    def _handle_enter(self, _event: tk.Event) -> None:
        if not self._enabled:
            return
        self._hovered = True
        self._draw()

    def _handle_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._pressed = False
        self._draw()

    def _handle_press(self, _event: tk.Event) -> None:
        if not self._enabled:
            return
        self.focus_set()
        self._pressed = True
        self._draw()

    def _handle_release(self, event: tk.Event) -> None:
        if not self._enabled:
            return
        inside = 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height()
        was_pressed = self._pressed
        self._pressed = False
        self._draw()
        if was_pressed and inside:
            self.invoke()

    def _handle_focus_in(self, _event: tk.Event) -> None:
        self._focused = True
        self._draw()

    def _handle_focus_out(self, _event: tk.Event) -> None:
        self._focused = False
        self._draw()

    def _handle_keyboard(self, _event: tk.Event) -> str:
        self.invoke()
        return "break"

    def _draw(self) -> None:
        width = max(self.winfo_width(), self._width_hint)
        height = max(self.winfo_height(), self._height_hint)
        self.delete("all")

        fill, foreground = self._colors()
        outline = theme.FOCUS if self._focused and self._enabled else fill
        points = self._rounded_points(1, 1, width - 1, height - 1, 7)
        self.create_polygon(
            points,
            smooth=True,
            splinesteps=24,
            fill=fill,
            outline=outline,
            width=2 if self._focused and self._enabled else 0,
        )
        self.create_text(
            20,
            height / 2,
            text=self._icon,
            anchor="w",
            fill=foreground,
            font=("Segoe UI Symbol", 14, "bold"),
        )
        self.create_text(
            46,
            height / 2,
            text=self._text,
            anchor="w",
            fill=foreground,
            font=("Microsoft YaHei UI", 10, "bold"),
        )

    def _colors(self) -> tuple[str, str]:
        if not self._enabled:
            return theme.BUTTON_DISABLED_BG, theme.BUTTON_DISABLED_FG
        if self._variant == "primary":
            fill = theme.ACCENT_ACTIVE if self._pressed else theme.ACCENT
            if self._hovered and not self._pressed:
                fill = "#417963"
            return fill, "#FFFFFF"

        fill = theme.ACCENT_SOFT_HOVER if self._hovered else theme.ACCENT_SOFT
        if self._pressed:
            fill = "#C9DCD2"
        return fill, theme.ACCENT_ACTIVE

    @staticmethod
    def _rounded_points(
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        radius: float,
    ) -> tuple[float, ...]:
        return (
            x0 + radius,
            y0,
            x1 - radius,
            y0,
            x1,
            y0,
            x1,
            y0 + radius,
            x1,
            y1 - radius,
            x1,
            y1,
            x1 - radius,
            y1,
            x0 + radius,
            y1,
            x0,
            y1,
            x0,
            y1 - radius,
            x0,
            y0 + radius,
            x0,
            y0,
        )
