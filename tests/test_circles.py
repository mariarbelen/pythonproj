import pytest

from circle_intersection import (
    COINCIDENT,
    CONTAINED,
    EXTERNALLY_TANGENT,
    INTERNALLY_TANGENT,
    INTERSECTING,
    SEPARATE,
    classify_circles,
)


@pytest.mark.parametrize(
    "circles, expected",
    [
        ((0, 0, 5, 20, 0, 5), SEPARATE),
        ((0, 0, 5, 10, 0, 5), EXTERNALLY_TANGENT),
        ((0, 0, 5, 8, 0, 5), INTERSECTING),
        ((0, 0, 10, 5, 0, 5), INTERNALLY_TANGENT),
        ((0, 0, 10, 2, 0, 3), CONTAINED),
        ((0, 0, 10, 0, 0, 3), CONTAINED),
        ((3, 4, 7, 3, 4, 7), COINCIDENT),
        ((0, 0, 3, 3, 4, 2), EXTERNALLY_TANGENT),  # 3-4-5 triangle: distance is 5
    ],
)
def test_classify_circles(circles, expected):
    assert classify_circles(*circles) == expected


def test_order_of_circles_does_not_matter():
    assert classify_circles(5, 0, 5, 0, 0, 10) == INTERNALLY_TANGENT


def test_tolerance_treats_near_touching_as_touching():
    assert classify_circles(0, 0, 5, 10.4, 0, 5) == SEPARATE
    assert classify_circles(0, 0, 5, 10.4, 0, 5, tolerance=1.0) == EXTERNALLY_TANGENT


def test_rejects_non_positive_radius():
    with pytest.raises(ValueError):
        classify_circles(0, 0, 0, 5, 5, 5)
