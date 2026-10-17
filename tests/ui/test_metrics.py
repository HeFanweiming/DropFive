import pytest

from dropfive.ui.metrics import board_visual_scale


def test_board_details_grow_with_cell_spacing() -> None:
    windowed = board_visual_scale(38)
    fullscreen = board_visual_scale(90)

    assert fullscreen.stone_radius > windowed.stone_radius
    assert fullscreen.coordinate_font_size > windowed.coordinate_font_size
    assert fullscreen.last_move_radius > windowed.last_move_radius
    assert fullscreen.stone_radius == pytest.approx(39.6)
