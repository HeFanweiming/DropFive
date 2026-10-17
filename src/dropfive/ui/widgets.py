"""Small custom controls used by the DropFive window."""

import tkinter as tk
from collections.abc import Callable

from dropfive.ui import theme


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
        points = _rounded_points(1, 1, width - 1, height - 1, 7)
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


class SegmentedControl(tk.Canvas):
    """Compact single-choice control for game mode and difficulty."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        options: list[tuple[str, str]],
        selected: str,
        command: Callable[[str], None],
        background: str,
        width: int = 232,
        height: int = 36,
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
        if not options:
            raise ValueError("SegmentedControl requires at least one option")
        if selected not in {value for value, _ in options}:
            raise ValueError("Selected value must match an option")

        self._segment_options = options
        self._selected = selected
        self._command = command
        self._width_hint = width
        self._height_hint = height
        self._enabled = True
        self._hovered_index: int | None = None

        self.bind("<Configure>", self._handle_configure)
        self.bind("<Button-1>", self._handle_click)
        self.bind("<Motion>", self._handle_motion)
        self.bind("<Leave>", self._handle_leave)
        self.configure(cursor="hand2")
        self._draw()

    def set_selected(self, value: str) -> None:
        if value not in {option_value for option_value, _ in self._segment_options}:
            raise ValueError("Unknown segmented control value")
        if value != self._selected:
            self._selected = value
            self._draw()

    def set_enabled(self, enabled: bool) -> None:
        if enabled == self._enabled:
            return
        self._enabled = enabled
        self._hovered_index = None
        self.configure(cursor="hand2" if enabled else "arrow")
        self._draw()

    def _handle_configure(self, _event: tk.Event) -> None:
        self._draw()

    def _handle_click(self, event: tk.Event) -> None:
        if not self._enabled:
            return
        index = self._index_at(event.x)
        value = self._segment_options[index][0]
        if value != self._selected:
            self._selected = value
            self._draw()
            self._command(value)

    def _handle_motion(self, event: tk.Event) -> None:
        if not self._enabled:
            return
        index = self._index_at(event.x)
        if index != self._hovered_index:
            self._hovered_index = index
            self._draw()

    def _handle_leave(self, _event: tk.Event) -> None:
        self._hovered_index = None
        self._draw()

    def _draw(self) -> None:
        width = max(self.winfo_width(), self._width_hint)
        height = max(self.winfo_height(), self._height_hint)
        self.delete("all")

        track_fill = theme.SURFACE_ALT if self._enabled else theme.BUTTON_DISABLED_BG
        self.create_polygon(
            _rounded_points(1, 1, width - 1, height - 1, 8),
            smooth=True,
            splinesteps=24,
            fill=track_fill,
            outline=theme.BORDER,
            width=1,
        )

        segment_width = (width - 4) / len(self._segment_options)
        for index, (value, label) in enumerate(self._segment_options):
            x0 = 2 + index * segment_width
            x1 = x0 + segment_width
            selected = value == self._selected
            hovered = index == self._hovered_index and not selected
            if selected:
                fill = theme.ACCENT if self._enabled else "#C7D2CC"
                foreground = "#FFFFFF" if self._enabled else "#7E8B85"
            elif hovered:
                fill = "#E3DCD0"
                foreground = theme.INK
            else:
                fill = track_fill
                foreground = theme.MUTED if self._enabled else theme.BUTTON_DISABLED_FG

            if selected or hovered:
                self.create_polygon(
                    _rounded_points(x0 + 2, 4, x1 - 2, height - 4, 6),
                    smooth=True,
                    splinesteps=20,
                    fill=fill,
                    outline="",
                )
            self.create_text(
                (x0 + x1) / 2,
                height / 2,
                text=label,
                fill=foreground,
                font=("Microsoft YaHei UI", 9, "bold" if selected else "normal"),
            )

    def _index_at(self, x: float) -> int:
        width = max(self.winfo_width(), self._width_hint)
        segment_width = (width - 4) / len(self._segment_options)
        index = int((x - 2) / segment_width)
        return max(0, min(len(self._segment_options) - 1, index))
