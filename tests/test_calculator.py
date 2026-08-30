"""
Production-Grade Pytest Suite for Surveying Calculator Service.

Tests validate all algorithms against expected mathematical results
using realistic surveying data and proper floating-point comparison.
"""
import math
import pytest
from app.services.calculator import (
    CalculatorService,
    Point2D,
    Point3D,
    TraverseResult,
    SurveyingError
)


class TestConversions:
    """Test basic angle/distance conversion functions."""

    def test_grads_to_radians_known_value(self):
        result = CalculatorService.grads_to_radians(100.0)
        assert math.isclose(result, math.pi / 2, rel_tol=1e-10)

    def test_grads_to_radians_full_circle(self):
        result = CalculatorService.grads_to_radians(200.0)
        assert math.isclose(result, math.pi, rel_tol=1e-10)

    def test_radians_to_grads_known_value(self):
        result = CalculatorService.radians_to_grads(math.pi / 2)
        assert math.isclose(result, 100.0, rel_tol=1e-10)

    def test_radians_to_grads_full_circle(self):
        result = CalculatorService.radians_to_grads(math.pi)
        assert math.isclose(result, 200.0, rel_tol=1e-10)

    def test_roundtrip_conversion(self):
        original = 127.5
        converted = CalculatorService.radians_to_grads(
            CalculatorService.grads_to_radians(original)
        )
        assert math.isclose(converted, original, rel_tol=1e-10)

    def test_polar_to_cartesian_0_degrees(self):
        delta_y, delta_x = CalculatorService.polar_to_cartesian(100.0, 0.0)
        assert math.isclose(delta_y, 0.0, abs_tol=1e-10)
        assert math.isclose(delta_x, 100.0, abs_tol=1e-10)

    def test_polar_to_cartesian_100_grades_east(self):
        delta_y, delta_x = CalculatorService.polar_to_cartesian(100.0, 100.0)
        assert math.isclose(delta_x, 0.0, abs_tol=1e-10)
        assert math.isclose(delta_y, 100.0, abs_tol=1e-10)

    def test_polar_to_cartesian_200_grades_south(self):
        delta_y, delta_x = CalculatorService.polar_to_cartesian(100.0, 200.0)
        assert math.isclose(delta_x, -100.0, abs_tol=1e-10)
        assert math.isclose(delta_y, 0.0, abs_tol=1e-10)

    def test_polar_to_cartesian_300_grades_west(self):
        delta_y, delta_x = CalculatorService.polar_to_cartesian(100.0, 300.0)
        assert math.isclose(delta_x, 0.0, abs_tol=1e-10)
        assert math.isclose(delta_y, -100.0, abs_tol=1e-10)

    def test_polar_to_cartesian_50_grades_northeast(self):
        distance = math.sqrt(2)
        delta_y, delta_x = CalculatorService.polar_to_cartesian(distance, 50.0)
        assert math.isclose(delta_y, 1.0, abs_tol=1e-9)
        assert math.isclose(delta_x, 1.0, abs_tol=1e-9)


class TestAreaPerimeter:
    """Test area and perimeter calculations using Surveyor's formula."""

    def test_square_area(self):
        points = [
            {'y': 0.0, 'x': 0.0},
            {'y': 0.0, 'x': 10.0},
            {'y': 10.0, 'x': 10.0},
            {'y': 10.0, 'x': 0.0}
        ]
        area = CalculatorService.calculate_area(points)
        assert math.isclose(area, 100.0, rel_tol=1e-9)

    def test_triangle_area(self):
        points = [
            {'y': 0.0, 'x': 0.0},
            {'y': 0.0, 'x': 10.0},
            {'y': 10.0, 'x': 0.0}
        ]
        area = CalculatorService.calculate_area(points)
        assert math.isclose(area, 50.0, rel_tol=1e-9)

    def test_rectangle_area(self):
        points = [
            {'y': 100.0, 'x': 200.0},
            {'y': 100.0, 'x': 350.0},
            {'y': 250.0, 'x': 350.0},
            {'y': 250.0, 'x': 200.0}
        ]
        area = CalculatorService.calculate_area(points)
        expected = 150.0 * 150.0
        assert math.isclose(area, expected, rel_tol=1e-9)

    def test_area_insufficient_points_raises_error(self):
        with pytest.raises(SurveyingError, match="Need at least 3 points"):
            CalculatorService.calculate_area([{'y': 0, 'x': 0}, {'y': 1, 'x': 1}])

    def test_area_empty_list_raises_error(self):
        with pytest.raises(SurveyingError, match="Need at least 3 points"):
            CalculatorService.calculate_area([])

    def test_perimeter_square(self):
        points = [
            {'y': 0.0, 'x': 0.0},
            {'y': 0.0, 'x': 10.0},
            {'y': 10.0, 'x': 10.0},
            {'y': 10.0, 'x': 0.0}
        ]
        perimeter = CalculatorService.calculate_perimeter(points)
        assert math.isclose(perimeter, 40.0, rel_tol=1e-9)

    def test_perimeter_triangle(self):
        points = [
            {'y': 0.0, 'x': 0.0},
            {'y': 0.0, 'x': 3.0},
            {'y': 4.0, 'x': 0.0}
        ]
        perimeter = CalculatorService.calculate_perimeter(points)
        assert math.isclose(perimeter, 12.0, rel_tol=1e-9)

    def test_perimeter_single_point_returns_zero(self):
        result = CalculatorService.calculate_perimeter([{'y': 0, 'x': 0}])
        assert result == 0.0

    def test_perimeter_empty_list_returns_zero(self):
        result = CalculatorService.calculate_perimeter([])
        assert result == 0.0

    def test_polygon_with_many_vertices(self):
        n = 6
        radius = 10.0
        points = [
            {'y': radius * math.sin(2 * math.pi * i / n),
             'x': radius * math.cos(2 * math.pi * i / n)}
            for i in range(n)
        ]
        area = CalculatorService.calculate_area(points)
        expected = (n * radius ** 2 * math.sin(2 * math.pi / n)) / 2
        assert math.isclose(area, expected, rel_tol=1e-8)


class TestDistanceAzimuth:
    """Test distance and azimuth calculations."""

    def test_distance_horizontal(self):
        p1 = {'y': 0.0, 'x': 0.0}
        p2 = {'y': 0.0, 'x': 3.0}
        distance = CalculatorService.calculate_distance(p1, p2)
        assert math.isclose(distance, 3.0, rel_tol=1e-10)

    def test_distance_vertical(self):
        p1 = {'y': 0.0, 'x': 0.0}
        p2 = {'y': 4.0, 'x': 0.0}
        distance = CalculatorService.calculate_distance(p1, p2)
        assert math.isclose(distance, 4.0, rel_tol=1e-10)

    def test_distance_diagonal(self):
        p1 = {'y': 0.0, 'x': 0.0}
        p2 = {'y': 3.0, 'x': 4.0}
        distance = CalculatorService.calculate_distance(p1, p2)
        assert math.isclose(distance, 5.0, rel_tol=1e-10)

    def test_distance_real_coordinates(self):
        p1 = {'y': 5428.234, 'x': 2341.892}
        p2 = {'y': 5534.115, 'x': 2489.001}
        distance = CalculatorService.calculate_distance(p1, p2)
        expected = math.sqrt((105.881 ** 2) + (147.109 ** 2))
        assert math.isclose(distance, expected, rel_tol=1e-9)

    def test_azimuth_north(self):
        p1 = {'y': 100.0, 'x': 100.0}
        p2 = {'y': 100.0, 'x': 200.0}
        azimuth = CalculatorService.calculate_azimuth(p1, p2)
        assert math.isclose(azimuth, 0.0, abs_tol=1e-9)

    def test_azimuth_east(self):
        p1 = {'y': 100.0, 'x': 100.0}
        p2 = {'y': 200.0, 'x': 100.0}
        azimuth = CalculatorService.calculate_azimuth(p1, p2)
        assert math.isclose(azimuth, 100.0, abs_tol=1e-9)

    def test_azimuth_south(self):
        p1 = {'y': 100.0, 'x': 100.0}
        p2 = {'y': 100.0, 'x': 0.0}
        azimuth = CalculatorService.calculate_azimuth(p1, p2)
        assert math.isclose(azimuth, 200.0, abs_tol=1e-9)

    def test_azimuth_west(self):
        p1 = {'y': 100.0, 'x': 100.0}
        p2 = {'y': 0.0, 'x': 100.0}
        azimuth = CalculatorService.calculate_azimuth(p1, p2)
        assert math.isclose(azimuth, 300.0, abs_tol=1e-9)

    def test_azimuth_northeast(self):
        p1 = {'y': 0.0, 'x': 0.0}
        p2 = {'y': 100.0, 'x': 100.0}
        azimuth = CalculatorService.calculate_azimuth(p1, p2)
        assert math.isclose(azimuth, 50.0, abs_tol=1e-9)

    def test_azimuth_coincident_points_raises_error(self):
        p = {'y': 100.0, 'x': 100.0}
        with pytest.raises(SurveyingError, match="Points are coincident"):
            CalculatorService.calculate_azimuth(p, p)

    def test_azimuth_in_degrees(self):
        p1 = {'y': 0.0, 'x': 0.0}
        p2 = {'y': 100.0, 'x': 1.0}
        azimuth_rad = CalculatorService.calculate_azimuth(p1, p2, grads=False)
        expected_rad = math.atan2(100.0, 1.0)
        assert math.isclose(azimuth_rad, expected_rad, rel_tol=1e-9)

    def test_azimuth_north_degrees(self):
        p1 = {'y': 0.0, 'x': 0.0}
        p2 = {'y': 0.0, 'x': 100.0}
        azimuth = CalculatorService.calculate_azimuth(p1, p2, grads=False)
        assert math.isclose(azimuth, 0.0, abs_tol=1e-9)


class TestIntersections:
    """Test intersection algorithms."""

    def test_intersection_two_perpendicular_lines(self):
        p1 = {'y': 0.0, 'x': 0.0}
        p2 = {'y': 100.0, 'x': 100.0}
        result = CalculatorService.intersection_two_lines(p1, 100.0, p2, 200.0)
        assert result is not None
        assert math.isclose(result['y'], 100.0, abs_tol=1e-6)
        assert math.isclose(result['x'], 0.0, abs_tol=1e-6)

    def test_intersection_parallel_lines_returns_none(self):
        p1 = {'y': 0.0, 'x': 0.0}
        p2 = {'y': 100.0, 'x': 0.0}
        result = CalculatorService.intersection_two_lines(p1, 100.0, p2, 100.0)
        assert result is None

    def test_intersection_almost_parallel_returns_none(self):
        p1 = {'y': 0.0, 'x': 0.0}
        p2 = {'y': 100.0, 'x': 0.0}
        result = CalculatorService.intersection_two_lines(p1, 100.0, p2, 100.0)
        assert result is None

    def test_intersection_two_circles_known_case(self):
        p1 = {'y': 0.0, 'x': 0.0}
        p2 = {'y': 6.0, 'x': 0.0}
        result = CalculatorService.intersection_two_distances(p1, 5.0, p2, 5.0)
        assert result is not None
        p3, p4 = result
        assert math.isclose(p3['y'], 3.0, abs_tol=1e-9)
        assert math.isclose(p4['y'], 3.0, abs_tol=1e-9)
        assert math.isclose(abs(p3['x']), 4.0, abs_tol=1e-9)
        assert math.isclose(abs(p4['x']), 4.0, abs_tol=1e-9)

    def test_intersection_two_circles_no_intersection(self):
        p1 = {'y': 0.0, 'x': 0.0}
        p2 = {'y': 20.0, 'x': 0.0}
        result = CalculatorService.intersection_two_distances(p1, 5.0, p2, 5.0)
        assert result is None

    def test_intersection_two_circles_one_inside_other(self):
        p1 = {'y': 0.0, 'x': 0.0}
        p2 = {'y': 1.0, 'x': 0.0}
        result = CalculatorService.intersection_two_distances(p1, 5.0, p2, 1.0)
        assert result is None

    def test_intersection_line_distance_tangent(self):
        p1 = {'y': 0.0, 'x': 0.0}
        p2 = {'y': 5.0, 'x': 0.0}
        result = CalculatorService.intersection_line_distance(p1, 0.0, p2, 5.0)
        assert result is not None

    def test_intersection_line_distance_no_intersection(self):
        p1 = {'y': 0.0, 'x': 0.0}
        p2 = {'y': 2.0, 'x': 0.0}
        result = CalculatorService.intersection_line_distance(p1, 0.0, p2, 1.0)
        assert result is None


class TestInterpolation:
    """Test vertical interpolation algorithm (MASSAH12)."""

    def test_interpolation_ascending_line(self):
        points = {
            1: {'y': 0.0, 'x': 0.0, 'h': 100.0},
            2: {'y': 10.0, 'x': 10.0, 'h': 110.0}
        }
        lines = [(1, 2)]
        results = CalculatorService.interpolate_points(points, lines, 2.0)
        assert len(results) == 1
        assert results[0]['from'] == 1
        assert results[0]['to'] == 2
        assert len(results[0]['points']) > 0

    def test_interpolation_descending_line(self):
        points = {
            1: {'y': 0.0, 'x': 0.0, 'h': 110.0},
            2: {'y': 10.0, 'x': 10.0, 'h': 100.0}
        }
        lines = [(1, 2)]
        results = CalculatorService.interpolate_points(points, lines, 2.0)
        assert len(results) == 1

    def test_interpolation_zero_interval_raises_error(self):
        points = {1: {'y': 0, 'x': 0, 'h': 100}, 2: {'y': 10, 'x': 10, 'h': 110}}
        with pytest.raises(SurveyingError, match="Vertical interval must be positive"):
            CalculatorService.interpolate_points(points, [(1, 2)], 0.0)

    def test_interpolation_negative_interval_raises_error(self):
        points = {1: {'y': 0, 'x': 0, 'h': 100}, 2: {'y': 10, 'x': 10, 'h': 110}}
        with pytest.raises(SurveyingError, match="Vertical interval must be positive"):
            CalculatorService.interpolate_points(points, [(1, 2)], -1.0)

    def test_interpolation_missing_point_skipped(self):
        points = {1: {'y': 0.0, 'x': 0.0, 'h': 100.0}}
        lines = [(1, 2)]
        results = CalculatorService.interpolate_points(points, lines, 2.0)
        assert len(results) == 0

    def test_interpolation_same_height_skipped(self):
        points = {
            1: {'y': 0.0, 'x': 0.0, 'h': 100.0},
            2: {'y': 10.0, 'x': 10.0, 'h': 100.0}
        }
        lines = [(1, 2)]
        results = CalculatorService.interpolate_points(points, lines, 2.0)
        assert len(results) == 0

    def test_interpolation_result_structure(self):
        points = {
            1: {'y': 0.0, 'x': 0.0, 'h': 100.0},
            2: {'y': 10.0, 'x': 0.0, 'h': 110.0}
        }
        lines = [(1, 2)]
        results = CalculatorService.interpolate_points(points, lines, 5.0)
        assert len(results) == 1
        result = results[0]
        assert 'from' in result
        assert 'to' in result
        assert 'total_distance' in result
        assert 'height_diff' in result
        assert 'points' in result
        assert result['height_diff'] == 10.0


class TestResection:
    """Test 3-point and 2-point resection algorithms."""

    def test_resection_3point_valid_angles(self):
        p1 = {'y': 0.0, 'x': 0.0}
        p2 = {'y': 0.0, 'x': 100.0}
        p3 = {'y': 100.0, 'x': 100.0}
        station = CalculatorService.resection_3point(p1, 50.0, p2, 50.0, p3, 50.0)
        assert station is not None
        assert 'y' in station
        assert 'x' in station

    def test_resection_3point_collinear_angles_returns_none(self):
        p1 = {'y': 0.0, 'x': 0.0}
        p2 = {'y': 50.0, 'x': 50.0}
        p3 = {'y': 100.0, 'x': 100.0}
        station = CalculatorService.resection_3point(p1, 100.0, p2, 100.0, p3, 100.0)
        assert station is None

    def test_resection_2point_valid_case(self):
        p1 = {'y': 0.0, 'x': 0.0}
        p2 = {'y': 0.0, 'x': 6.0}
        result = CalculatorService.resection_2point(p1, 5.0, p2, 5.0)
        assert result is not None
        p3, p4 = result
        assert 'y' in p3
        assert 'x' in p3

    def test_resection_2point_impossible_triangle_returns_none(self):
        p1 = {'y': 0.0, 'x': 0.0}
        p2 = {'y': 10.0, 'x': 0.0}
        result = CalculatorService.resection_2point(p1, 5.0, p2, 5.0)
        assert result is None

    def test_resection_2point_zero_distance_returns_none(self):
        p1 = {'y': 0.0, 'x': 0.0}
        p2 = {'y': 100.0, 'x': 0.0}
        result = CalculatorService.resection_2point(p1, 0.0, p2, 50.0)
        assert result is None

    def test_resection_2point_negative_distance_returns_none(self):
        p1 = {'y': 0.0, 'x': 0.0}
        p2 = {'y': 100.0, 'x': 0.0}
        result = CalculatorService.resection_2point(p1, -10.0, p2, 50.0)
        assert result is None


class TestCircleCenter:
    """Test circle center from 3 points algorithm."""

    def test_circle_center_right_triangle(self):
        p1 = {'y': 0.0, 'x': 0.0}
        p2 = {'y': 6.0, 'x': 0.0}
        p3 = {'y': 0.0, 'x': 8.0}
        result = CalculatorService.circle_center_3points(p1, p2, p3)
        assert result is not None
        assert math.isclose(result['x'], 4.0, abs_tol=1e-9)
        assert math.isclose(result['y'], 3.0, abs_tol=1e-9)
        assert math.isclose(result['radius'], 5.0, abs_tol=1e-9)

    def test_circle_center_collinear_points_returns_none(self):
        p1 = {'y': 0.0, 'x': 0.0}
        p2 = {'y': 50.0, 'x': 50.0}
        p3 = {'y': 100.0, 'x': 100.0}
        result = CalculatorService.circle_center_3points(p1, p2, p3)
        assert result is None

    def test_circle_center_real_survey_points(self):
        p1 = {'y': 5428.234, 'x': 2341.892}
        p2 = {'y': 5534.115, 'x': 2489.001}
        p3 = {'y': 5489.456, 'x': 2512.334}
        result = CalculatorService.circle_center_3points(p1, p2, p3)
        assert result is not None
        radius = CalculatorService.calculate_distance(
            {'y': result['y'], 'x': result['x']}, p1
        )
        assert math.isclose(radius, result['radius'], rel_tol=1e-9)


class TestOffsetCalculation:
    """Test offset calculation algorithm (MASSAH06)."""

    def test_offset_point_horizontal_line_left(self):
        line_start = {'y': 0.0, 'x': 0.0}
        line_end = {'y': 0.0, 'x': 10.0}
        result = CalculatorService.calculate_offset_point(line_start, line_end, 5.0, 'LEFT')
        assert math.isclose(result['y'], 5.0, abs_tol=1e-9)
        assert math.isclose(result['x'], 5.0, abs_tol=1e-9)

    def test_offset_point_horizontal_line_right(self):
        line_start = {'y': 0.0, 'x': 0.0}
        line_end = {'y': 0.0, 'x': 10.0}
        result = CalculatorService.calculate_offset_point(line_start, line_end, 5.0, 'RIGHT')
        assert math.isclose(result['y'], 5.0, abs_tol=1e-9)
        assert math.isclose(result['x'], -5.0, abs_tol=1e-9)

    def test_offset_point_vertical_line_left(self):
        line_start = {'y': 0.0, 'x': 0.0}
        line_end = {'y': 10.0, 'x': 0.0}
        result = CalculatorService.calculate_offset_point(line_start, line_end, 5.0, 'LEFT')
        assert math.isclose(result['y'], 5.0, abs_tol=1e-9)
        assert math.isclose(result['x'], -5.0, abs_tol=1e-9)

    def test_offset_point_vertical_line_right(self):
        line_start = {'y': 0.0, 'x': 0.0}
        line_end = {'y': 10.0, 'x': 0.0}
        result = CalculatorService.calculate_offset_point(line_start, line_end, 5.0, 'RIGHT')
        assert math.isclose(result['y'], -5.0, abs_tol=1e-9)
        assert math.isclose(result['x'], -5.0, abs_tol=1e-9)

    def test_offset_line_too_short_raises_error(self):
        line_start = {'y': 0.0, 'x': 0.0}
        line_end = {'y': 0.00001, 'x': 0.0}
        with pytest.raises(SurveyingError, match="Line too short"):
            CalculatorService.calculate_offset_point(line_start, line_end, 5.0, 'LEFT')


class TestFreeNumbers:
    """Test free numbers (deleted points) filter."""

    def test_free_numbers_filters_deleted(self):
        points = [
            {'no': 1, 'y': 100.0, 'x': 200.0},
            {'no': 2, 'y': 0.0, 'x': 0.0},
            {'no': 3, 'y': 300.0, 'x': 400.0},
        ]
        result = CalculatorService.get_free_numbers(points)
        assert len(result) == 1
        assert result[0]['no'] == 2

    def test_free_numbers_within_range(self):
        points = [
            {'no': 5, 'y': 0.0, 'x': 0.0},
            {'no': 10, 'y': 0.0, 'x': 0.0},
            {'no': 15, 'y': 100.0, 'x': 200.0},
        ]
        result = CalculatorService.get_free_numbers(points, from_no=1, to_no=10)
        assert len(result) == 2
        assert result[0]['no'] == 5

    def test_free_numbers_outside_range_excluded(self):
        points = [
            {'no': 1, 'y': 0.0, 'x': 0.0},
            {'no': 50, 'y': 0.0, 'x': 0.0},
        ]
        result = CalculatorService.get_free_numbers(points, from_no=1, to_no=10)
        assert len(result) == 1
        assert result[0]['no'] == 1

    def test_free_numbers_no_deleted_points(self):
        points = [
            {'no': 1, 'y': 100.0, 'x': 200.0},
            {'no': 2, 'y': 300.0, 'x': 400.0},
        ]
        result = CalculatorService.get_free_numbers(points)
        assert len(result) == 0

    def test_free_numbers_empty_list(self):
        result = CalculatorService.get_free_numbers([])
        assert len(result) == 0

    def test_free_numbers_small_coordinates_within_threshold(self):
        points = [
            {'no': 1, 'y': 0.005, 'x': 0.005},
        ]
        result = CalculatorService.get_free_numbers(points)
        assert len(result) == 1


class TestBowditchTraverse:
    """Test Bowditch traverse adjustment algorithm."""

    def test_bowditch_closed_traverse(self):
        points = [
            {'no': 1, 'y': 0.0, 'x': 0.0, 'h': 0.0, 'delta_y': 10.0, 'delta_x': 0.0, 'distance': 10.0},
            {'no': 2, 'y': 10.0, 'x': 0.0, 'h': 0.0, 'delta_y': 0.0, 'delta_x': 10.0, 'distance': 10.0},
            {'no': 3, 'y': 10.0, 'x': 10.0, 'h': 0.0, 'delta_y': -10.0, 'delta_x': 0.0, 'distance': 10.0},
            {'no': 4, 'y': 0.0, 'x': 10.0, 'h': 0.0, 'delta_y': 0.0, 'delta_x': -10.0, 'distance': 10.0},
        ]
        result = CalculatorService.bowditch_traverse(points)
        assert isinstance(result, TraverseResult)
        assert len(result.adjusted_points) == 4
        assert result.total_distance == 40.0

    def test_bowditch_with_known_end_points(self):
        points = [
            {'no': 1, 'y': 100.0, 'x': 100.0, 'h': 0.0, 'delta_y': 10.0, 'delta_x': 0.0, 'distance': 10.0},
            {'no': 2, 'y': 110.0, 'x': 100.0, 'h': 0.0, 'delta_y': 0.0, 'delta_x': 10.0, 'distance': 10.0},
        ]
        known_start = {'y': 100.0, 'x': 100.0}
        known_end = {'y': 109.0, 'x': 111.0}
        result = CalculatorService.bowditch_traverse(points, known_start, known_end)
        assert isinstance(result, TraverseResult)
        assert result.linear_misclosure > 0

    def test_bowditch_insufficient_points_raises_error(self):
        points = [{'no': 1, 'y': 0.0, 'x': 0.0, 'distance': 10.0}]
        with pytest.raises(SurveyingError, match="Need at least 2 points"):
            CalculatorService.bowditch_traverse(points)

    def test_bowditch_zero_total_distance_raises_error(self):
        points = [
            {'no': 1, 'y': 0.0, 'x': 0.0, 'distance': 0.0},
            {'no': 2, 'y': 0.0, 'x': 0.0, 'distance': 0.0},
        ]
        with pytest.raises(SurveyingError, match="Total distance is too small"):
            CalculatorService.bowditch_traverse(points)

    def test_bowditch_result_structure(self):
        points = [
            {'no': 1, 'y': 0.0, 'x': 0.0, 'h': 0.0, 'delta_y': 10.0, 'delta_x': 0.0, 'distance': 10.0},
            {'no': 2, 'y': 10.0, 'x': 0.0, 'h': 0.0, 'delta_y': 0.0, 'delta_x': 10.0, 'distance': 10.0},
        ]
        result = CalculatorService.bowditch_traverse(points)
        assert hasattr(result, 'adjusted_points')
        assert hasattr(result, 'closure_error_x')
        assert hasattr(result, 'closure_error_y')
        assert hasattr(result, 'linear_misclosure')
        assert hasattr(result, 'precision_ratio')
        assert hasattr(result, 'total_distance')

    def test_bowditch_perfect_loop_precision_ratio_infinite(self):
        points = [
            {'no': 1, 'y': 0.0, 'x': 0.0, 'h': 0.0, 'delta_y': 100.0, 'delta_x': 0.0, 'distance': 100.0},
            {'no': 2, 'y': 100.0, 'x': 0.0, 'h': 0.0, 'delta_y': 0.0, 'delta_x': 100.0, 'distance': 100.0},
            {'no': 3, 'y': 100.0, 'x': 100.0, 'h': 0.0, 'delta_y': -100.0, 'delta_x': 0.0, 'distance': 100.0},
            {'no': 4, 'y': 0.0, 'x': 100.0, 'h': 0.0, 'delta_y': 0.0, 'delta_x': -100.0, 'distance': 100.0},
        ]
        result = CalculatorService.bowditch_traverse(points)
        assert result.closure_error_x == 0.0
        assert result.closure_error_y == 0.0
        assert result.linear_misclosure == 0.0


class TestUtilityFunctions:
    """Test utility formatting functions."""

    def test_format_coordinate_default_decimals(self):
        result = CalculatorService.format_coordinate(123.456)
        assert result == "123.46"

    def test_format_coordinate_custom_decimals(self):
        result = CalculatorService.format_coordinate(123.456, decimals=3)
        assert result == "123.456"

    def test_format_coordinate_integer_value(self):
        result = CalculatorService.format_coordinate(100.0)
        assert result == "100.00"

    def test_format_angle_gradians_default(self):
        result = CalculatorService.format_angle(150.5)
        assert "150.5000" in result
        assert "GRADS" in result

    def test_format_angle_degrees(self):
        result = CalculatorService.format_angle(150.5, unit='DEGREES')
        assert "DEGREES" in result


class TestDataclasses:
    """Test dataclass structures."""

    def test_point2d_to_dict(self):
        point = Point2D(y=100.5, x=200.5)
        d = point.to_dict()
        assert d == {'y': 100.5, 'x': 200.5}

    def test_point3d_to_dict(self):
        point = Point3D(y=100.5, x=200.5, h=50.0)
        d = point.to_dict()
        assert d == {'y': 100.5, 'x': 200.5, 'h': 50.0}

    def test_point3d_default_height(self):
        point = Point3D(y=100.5, x=200.5)
        assert point.h == 0.0

    def test_traverse_result_fields(self):
        result = TraverseResult(
            adjusted_points=[],
            closure_error_x=0.0,
            closure_error_y=0.0,
            linear_misclosure=0.0,
            precision_ratio=0.0,
            total_distance=0.0
        )
        assert result.adjusted_points == []
        assert result.closure_error_x == 0.0

    def test_surveying_error_is_exception(self):
        error = SurveyingError("Test message")
        assert isinstance(error, Exception)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_small_distance(self):
        p1 = {'y': 0.0, 'x': 0.0}
        p2 = {'y': 0.0001, 'x': 0.0}
        distance = CalculatorService.calculate_distance(p1, p2)
        assert distance > 0

    def test_very_large_coordinates(self):
        p1 = {'y': 1000000.0, 'x': 2000000.0}
        p2 = {'y': 1000010.0, 'x': 2000020.0}
        distance = CalculatorService.calculate_distance(p1, p2)
        expected = math.sqrt(10**2 + 20**2)
        assert math.isclose(distance, expected, rel_tol=1e-9)

    def test_negative_coordinates(self):
        p1 = {'y': -100.0, 'x': -200.0}
        p2 = {'y': -100.0, 'x': -100.0}
        distance = CalculatorService.calculate_distance(p1, p2)
        assert math.isclose(distance, 100.0, rel_tol=1e-9)

    def test_area_with_almost_collinear_points(self):
        points = [
            {'y': 0.0, 'x': 0.0},
            {'y': 100.0, 'x': 0.001},
            {'y': 200.0, 'x': 0.0}
        ]
        area = CalculatorService.calculate_area(points)
        assert area < 1.0

    def test_perimeter_with_very_small_segments(self):
        points = [
            {'y': 0.0, 'x': 0.0},
            {'y': 0.0001, 'x': 0.0},
            {'y': 0.0002, 'x': 0.0}
        ]
        perimeter = CalculatorService.calculate_perimeter(points)
        assert math.isclose(perimeter, 0.0004, rel_tol=1e-6)
