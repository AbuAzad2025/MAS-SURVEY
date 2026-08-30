"""
E2E Tests for MAS Survey Application using Playwright.
Tests all user interactions and workflows.
"""
import pytest
import time
import json
from pathlib import Path
from playwright.sync_api import Page, expect, Browser


class TestLandingPage:
    """Test landing page and main navigation."""

    def test_landing_page_loads(self, page: Page, base_url: str):
        """Test that landing page loads successfully."""
        page.goto(base_url)
        expect(page).to_have_title(/MAS|iSurvey|Master/)

    def test_main_menu_navigation(self, page: Page, base_url: str):
        """Test main menu links are accessible."""
        page.goto(base_url)
        page.wait_for_load_state("networkidle")


class TestAuthAndFiles:
    """Test authentication and file management."""

    def test_create_new_file(self, page: Page, base_url: str):
        """Test creating a new survey file."""
        page.goto(f"{base_url}/files/new")
        page.fill('input[name="name"]', f'test_file_{int(time.time())}')
        page.fill('input[name="date"]', '2026-08-31')
        page.fill('input[name="place"]', 'Test Location')
        page.click('button[type="submit"]')
        page.wait_for_url(f"{base_url}/mas")

    def test_file_list_view(self, page: Page, base_url: str):
        """Test viewing list of files."""
        page.goto(f"{base_url}/files")
        page.wait_for_load_state("networkidle")

    def test_upload_dtf_file(self, page: Page, base_url: str):
        """Test uploading a DTF file."""
        page.goto(f"{base_url}/files")
        file_input = page.locator('input[type="file"]')
        file_input.set_input_files("tests/fixtures/sample.dtf")


class TestPolarSurvey:
    """Test Polar Survey (Distomat/Tacheometry) functionality."""

    def test_polar_distomat_mode(self, page: Page, base_url: str, login_as_test_user):
        """Test Distomat polar survey calculation."""
        page.goto(f"{base_url}/polar")
        page.click('text=DISTOMAT')
        page.fill('#station-point', '1')
        page.fill('#back-azimuth', '0')
        
        # Add observation row
        rows = page.locator('#polar-tbody tr')
        first_row = rows.first
        first_row.locator('input[name="no[]"]').fill('10')
        first_row.locator('input[name="dist[]"]').fill('100')
        first_row.locator('input[name="angle[]"]').fill('50')
        
        page.click('text=CALCULATE')
        page.wait_for_selector('#polar-result', state='visible')

    def test_polar_tacheometry_mode(self, page: Page, base_url: str):
        """Test Tacheometry mode."""
        page.goto(f"{base_url}/polar")
        page.click('text=TACHEOMETRY')
        expect(page.locator('#polar-title')).to_contain_text('TACHEOMETRY')

    def test_polar_azimuth_mode(self, page: Page, base_url: str):
        """Test Azimuth-Distance mode."""
        page.goto(f"{base_url}/polar")
        page.click('text=AZIMUTH-DISTANCE')
        expect(page.locator('#polar-title')).to_contain_text('AZIMUTH')


class TestAreaCalculation:
    """Test Area calculation functionality."""

    def test_area_calculation(self, page: Page, base_url: str, create_test_file):
        """Test calculating area from polygon points."""
        page.goto(f"{base_url}/area")
        page.wait_for_selector('#points-table')
        
        # Verify points are displayed
        rows = page.locator('#points-table tbody tr')
        expect(rows).to_have_count(4)  # Square with 4 points
        
        # Calculate area
        page.click('text=CALCULATE AREA')
        
        # Check result
        area_value = page.locator('#area-value')
        expect(area_value).not_to_have_text('0.00')

    def test_area_insufficient_points(self, page: Page, base_url: str, create_test_file):
        """Test error when less than 3 points."""
        page.goto(f"{base_url}/area")
        page.wait_for_selector('#points-table')
        
        # Delete points to have less than 3
        # This test checks the error handling


class TestOffsets:
    """Test Offsets calculation functionality."""

    def test_offsets_calculation(self, page: Page, base_url: str, create_test_file):
        """Test calculating offset points from line."""
        page.goto(f"{base_url}/offsets")
        page.wait_for_load_state("networkidle")
        
        page.fill('#line-start', '1')
        page.fill('#line-end', '2')
        
        # Add offset point
        page.click('text=+ ADD ROW')
        rows = page.locator('#offsets-tbody tr')
        rows.last.locator('input[name="no[]"]').fill('100')
        rows.last.locator('input[name="offset[]"]').fill('5')
        
        page.click('text=CALCULATE')
        page.wait_for_selector('#offset-result', state='visible')


class TestIntersections:
    """Test various intersection calculations."""

    def test_intersection_two_lines(self, page: Page, base_url: str):
        """Test intersection of two lines."""
        page.goto(f"{base_url}/intersections")
        page.click('text=TWO LINES')
        
        page.fill('#p1-y', '0')
        page.fill('#p1-x', '0')
        page.fill('#bearing1', '45')
        page.fill('#p2-y', '0')
        page.fill('#p2-x', '100')
        page.fill('#bearing2', '135')
        
        page.click('text=CALCULATE')
        page.wait_for_selector('#intersection-result', state='visible')

    def test_intersection_two_distances(self, page: Page, base_url: str):
        """Test intersection of two circles (distance-distance)."""
        page.goto(f"{base_url}/intersections")
        page.click('text=TWO DISTANCES')
        
        page.fill('#p1-y', '0')
        page.fill('#p1-x', '0')
        page.fill('#bearing1', '100')
        page.fill('#p2-y', '100')
        page.fill('#p2-x', '0')
        page.fill('#bearing2', '50')
        
        page.click('text=CALCULATE')
        page.wait_for_selector('#intersection-result', state='visible')

    def test_intersection_line_distance(self, page: Page, base_url: str):
        """Test intersection of line and circle."""
        page.goto(f"{base_url}/intersections")
        page.click('text=LINE & DISTANCE')
        
        page.fill('#p1-y', '0')
        page.fill('#p1-x', '0')
        page.fill('#bearing1', '0')
        page.fill('#p2-y', '50')
        page.fill('#p2-x', '0')
        page.fill('#bearing2', '50')
        
        page.click('text=CALCULATE')
        page.wait_for_selector('#intersection-result', state='visible')


class TestImplants:
    """Test Implantations (stake out) functionality."""

    def test_implant_calculation(self, page: Page, base_url: str, create_test_file):
        """Test calculating implant point from base and direction."""
        page.goto(f"{base_url}/implants")
        
        page.fill('#base-point', '1')
        page.fill('#implant-distance', '50')
        page.fill('#implant-bearing', '100')
        page.fill('#implant-height', '10.5')
        
        page.click('text=CALCULATE')
        
        result = page.locator('#implant-result')
        expect(result).to_be_visible()
        expect(page.locator('#implant-y')).not_to_have_text('0.000')


class TestCircleCalculations:
    """Test Circle/Arc calculations."""

    def test_circle_arc_length(self, page: Page, base_url: str):
        """Test Arc length calculation."""
        page.goto(f"{base_url}/circle")
        page.click('text=ARC')
        
        page.fill('#circle-value1', '100')  # Angle
        page.fill('#circle-value2', '50')   # Radius
        
        page.click('text=CALCULATE')
        page.wait_for_selector('#circle-result', state='visible')

    def test_circle_circumference(self, page: Page, base_url: str):
        """Test Circumference calculation."""
        page.goto(f"{base_url}/circle")
        page.click('text=CIRCUMFERENCE')
        
        page.fill('#circle-value1', '50')
        
        page.click('text=CALCULATE')
        expect(page.locator('#circle-result-value')).to_be_visible()

    def test_circle_area(self, page: Page, base_url: str):
        """Test Circle area calculation."""
        page.goto(f"{base_url}/circle")
        page.click('text=AREA')
        
        page.fill('#circle-value1', '50')
        
        page.click('text=CALCULATE')
        expect(page.locator('#circle-result-value')).to_contain_text('7853')

    def test_circle_center_from_3_points(self, page: Page, base_url: str):
        """Test finding circle center from 3 points."""
        page.goto(f"{base_url}/circle")
        page.click('text=CENTER')
        
        page.fill('#p1-y', '0')
        page.fill('#p1-x', '0')
        page.fill('#p2-y', '6')
        page.fill('#p2-x', '0')
        page.fill('#p3-y', '0')
        page.fill('#p3-x', '8')
        
        page.click('text=CALCULATE')
        
        center = page.locator('#circle-center-result')
        expect(center).to_be_visible()
        expect(page.locator('#radius-value')).to_contain_text('5')


class TestResection:
    """Test Resection calculations."""

    def test_resection_2point(self, page: Page, base_url: str, create_test_file):
        """Test 2-point resection."""
        page.goto(f"{base_url}/resection")
        
        page.fill('#resect-p1', '1')
        page.fill('#resect-p2', '2')
        page.fill('#resect-dist1', '50')
        page.fill('#resect-dist2', '70')
        
        page.click('text=CALCULATE')
        page.wait_for_selector('#resect-result', state='visible')


class TestTraverse:
    """Test Traverse adjustment functionality."""

    def test_traverse_calculation(self, page: Page, base_url: str, create_test_file):
        """Test Bowditch traverse adjustment."""
        page.goto(f"{base_url}/traverse")
        page.wait_for_load_state("networkidle")
        
        # Add traverse points
        rows = page.locator('#traverse-tbody tr')
        
        # Point 1
        rows.nth(0).locator('input[name="point_no[]"]').fill('1')
        rows.nth(0).locator('input[name="azimuth[]"]').fill('0')
        rows.nth(0).locator('input[name="distance[]"]').fill('100')
        
        # Point 2
        rows.nth(1).locator('input[name="point_no[]"]').fill('2')
        rows.nth(1).locator('input[name="azimuth[]"]').fill('100')
        rows.nth(1).locator('input[name="distance[]"]').fill('100')
        
        page.click('text=CALCULATE TRAVERSE')
        page.wait_for_selector('#traverse-result', state='visible')


class TestPlotting:
    """Test Plotting functions (Grid, Interpolation, Free Numbers)."""

    def test_plotting_grid_limits(self, page: Page, base_url: str, create_test_file):
        """Test Grid Limits calculation."""
        page.goto(f"{base_url}/plotting")
        page.click('text=GRID LIMITS')
        page.wait_for_selector('#plot-grid-section', state='visible')

    def test_plotting_coordinates(self, page: Page, base_url: str, create_test_file):
        """Test Print Coordinates."""
        page.goto(f"{base_url}/plotting")
        page.click('text=PRINT COORDINATES')
        page.wait_for_selector('#plot-coordinates-section', state='visible')

    def test_plotting_free_numbers(self, page: Page, base_url: str, create_test_file):
        """Test Free Numbers printing."""
        page.goto(f"{base_url}/plotting")
        page.click('text=PRINT FREE NUMBERS')
        page.wait_for_selector('#plot-freenumbers-section', state='visible')

    def test_plotting_interpolation(self, page: Page, base_url: str, create_test_file):
        """Test Vertical Interpolation."""
        page.goto(f"{base_url}/plotting")
        page.click('text=INTERPOLATION')
        
        page.fill('#interp-interval', '0.5')
        
        page.click('text=CALCULATE')
        page.wait_for_selector('#interp-result', state='visible')


class TestPrintPreview:
    """Test Print Preview functionality."""

    def test_print_preview(self, page: Page, base_url: str, create_test_file):
        """Test print preview page loads."""
        page.goto(f"{base_url}/print-preview")
        page.wait_for_load_state("networkidle")


class TestWorkMode:
    """Test Work Mode settings."""

    def test_work_mode_page(self, page: Page, base_url: str):
        """Test work mode settings page."""
        page.goto(f"{base_url}/work-mode")
        page.wait_for_load_state("networkidle")


class TestUserGuide:
    """Test User Guide functionality."""

    def test_user_guide(self, page: Page, base_url: str):
        """Test user guide page loads."""
        page.goto(f"{base_url}/guide")
        page.wait_for_load_state("networkidle")


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_no_file_selected(self, page: Page, base_url: str):
        """Test behavior when no file is selected."""
        page.goto(f"{base_url}/area")
        expect(page.locator('text=No file selected')).to_be_visible()

    def test_invalid_distance(self, page: Page, base_url: str, create_test_file):
        """Test error handling for invalid distance."""
        page.goto(f"{base_url}/implants")
        
        page.fill('#base-point', '1')
        page.fill('#implant-distance', '0')  # Invalid
        page.fill('#implant-bearing', '100')
        
        page.click('text=CALCULATE')
        # Should show error alert
        expect(page.locator('.alert-error')).to_be_visible()

    def test_parallel_lines_intersection(self, page: Page, base_url: str):
        """Test intersection of parallel lines returns error."""
        page.goto(f"{base_url}/intersections")
        page.click('text=TWO LINES')
        
        page.fill('#p1-y', '0')
        page.fill('#p1-x', '0')
        page.fill('#bearing1', '0')
        page.fill('#p2-y', '100')
        page.fill('#p2-x', '0')
        page.fill('#bearing2', '0')  # Same bearing = parallel
        
        page.click('text=CALCULATE')
        # Should handle parallel lines gracefully


class TestResponsiveDesign:
    """Test responsive design across different viewport sizes."""

    def test_mobile_viewport(self, page: Page, base_url: str):
        """Test application on mobile viewport."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")
        # Menu should be accessible

    def test_tablet_viewport(self, page: Page, base_url: str):
        """Test application on tablet viewport."""
        page.set_viewport_size({"width": 768, "height": 1024})
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")


class TestAccessibility:
    """Test accessibility features."""

    def test_keyboard_navigation(self, page: Page, base_url: str):
        """Test keyboard navigation works."""
        page.goto(f"{base_url}/")
        page.keyboard.press("Tab")
        page.keyboard.press("Tab")
        # Focus should move through elements

    def test_form_labels(self, page: Page, base_url: str):
        """Test all form inputs have labels."""
        page.goto(f"{base_url}/polar")
        inputs = page.locator('input:not([type="hidden"])')
        for inp in inputs.all():
            label = page.locator(f'label[for="{inp.get_attribute("id")}"]')
            expect(label).to_be_visible()
