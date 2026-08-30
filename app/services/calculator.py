"""
Surveying Calculator Service - Production Grade.
Pure Python functions for surveying mathematics.
All algorithms based on original GW-BASIC MAS system.
"""
import math
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass


@dataclass
class Point2D:
    """2D Point with Y (East-West) and X (North-South) coordinates."""
    y: float
    x: float
    
    def to_dict(self) -> Dict[str, float]:
        return {'y': self.y, 'x': self.x}


@dataclass
class Point3D:
    """3D Point with Y, X coordinates and Height."""
    y: float
    x: float
    h: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        return {'y': self.y, 'x': self.x, 'h': self.h}


@dataclass
class TraverseResult:
    """Traverse adjustment result."""
    adjusted_points: List[Dict[str, Any]]
    closure_error_x: float
    closure_error_y: float
    linear_misclosure: float
    precision_ratio: float
    total_distance: float


class SurveyingError(Exception):
    """Custom exception for surveying calculations."""
    pass


class CalculatorService:
    """
    Surveying calculation service with all core algorithms.
    All methods are pure functions with no side effects.
    """
    
    GRADS_TO_RADIANS = math.pi / 200
    RADIANS_TO_GRADS = 200 / math.pi
    
    # =========================================================================
    # BASIC CONVERSIONS
    # =========================================================================
    
    @staticmethod
    def grads_to_radians(grads: float) -> float:
        """Convert grads to radians."""
        return grads * CalculatorService.GRADS_TO_RADIANS
    
    @staticmethod
    def radians_to_grads(radians: float) -> float:
        """Convert radians to grads."""
        return radians * CalculatorService.RADIANS_TO_GRADS
    
    @staticmethod
    def polar_to_cartesian(distance: float, bearing: float) -> Tuple[float, float]:
        """
        Convert polar coordinates (distance + bearing) to Cartesian (delta Y, delta X).
        
        Args:
            distance: Horizontal distance
            bearing: Bearing angle in grads
            
        Returns:
            Tuple of (delta_y, delta_x)
        """
        angle_rad = CalculatorService.grads_to_radians(bearing)
        delta_y = distance * math.sin(angle_rad)
        delta_x = distance * math.cos(angle_rad)
        return delta_y, delta_x
    
    # =========================================================================
    # AREA & PERIMETER
    # =========================================================================
    
    @staticmethod
    def calculate_area(points: List[Dict[str, float]]) -> float:
        """
        Calculate area using Surveyor's formula (Shoelace/Gaussian).
        Original MAS system algorithm.
        
        Args:
            points: List of points with 'y' and 'x' keys
            
        Returns:
            Area in square meters
        """
        if len(points) < 3:
            raise SurveyingError("Need at least 3 points to calculate area")
        
        area = 0.0
        n = len(points)
        
        for i in range(n):
            j = (i + 1) % n
            area += points[i]['y'] * points[j]['x']
            area -= points[j]['y'] * points[i]['x']
        
        return abs(area) / 2.0
    
    @staticmethod
    def calculate_perimeter(points: List[Dict[str, float]]) -> float:
        """
        Calculate perimeter of polygon.
        
        Args:
            points: List of points with 'y' and 'x' keys
            
        Returns:
            Perimeter length in meters
        """
        if len(points) < 2:
            return 0.0
        
        perimeter = 0.0
        n = len(points)
        
        for i in range(n):
            j = (i + 1) % n
            dy = points[j]['y'] - points[i]['y']
            dx = points[j]['x'] - points[i]['x']
            perimeter += math.sqrt(dy * dy + dx * dx)
        
        return perimeter
    
    # =========================================================================
    # DISTANCE & AZIMUTH
    # =========================================================================
    
    @staticmethod
    def calculate_distance(p1: Dict[str, float], p2: Dict[str, float]) -> float:
        """
        Calculate horizontal distance between two points.
        
        Args:
            p1: First point {'y': y1, 'x': x1}
            p2: Second point {'y': y2, 'x': x2}
            
        Returns:
            Distance in meters
        """
        dy = p2['y'] - p1['y']
        dx = p2['x'] - p1['x']
        return math.sqrt(dy * dy + dx * dx)
    
    @staticmethod
    def calculate_azimuth(p1: Dict[str, float], p2: Dict[str, float], 
                          grads: bool = True) -> float:
        """
        Calculate azimuth from point 1 to point 2.
        
        Args:
            p1: From point
            p2: To point
            grads: True for grads, False for degrees
            
        Returns:
            Azimuth in grads (or degrees if grads=False)
        """
        dy = p2['y'] - p1['y']
        dx = p2['x'] - p1['x']
        
        if abs(dy) < 0.0000001 and abs(dx) < 0.0000001:
            raise SurveyingError("Points are coincident")
        
        if abs(dx) < 0.0000001:
            return 100.0 if dy > 0 else 300.0 if grads else 270.0
        
        azimuth = math.atan2(dy, dx)
        
        if grads:
            azimuth = CalculatorService.radians_to_grads(azimuth)
            if azimuth < 0:
                azimuth += 400.0
        else:
            if azimuth < 0:
                azimuth += 360.0
        
        return azimuth
    
    # =========================================================================
    # INTERSECTION ALGORITHMS
    # =========================================================================
    
    @staticmethod
    def intersection_two_lines(
        p1: Dict[str, float], bearing1: float,
        p2: Dict[str, float], bearing2: float
    ) -> Optional[Dict[str, float]]:
        """
        Calculate intersection of two lines given by point and bearing.
        
        Args:
            p1: First point {'y': y1, 'x': x1}
            bearing1: First line bearing in grads
            p2: Second point {'y': y2, 'x': x2}
            bearing2: Second line bearing in grads
            
        Returns:
            Intersection point {'y': y, 'x': x} or None if parallel
        """
        a1 = math.tan(CalculatorService.grads_to_radians(bearing1))
        a2 = math.tan(CalculatorService.grads_to_radians(bearing2))
        
        if abs(a1 - a2) < 0.0001:
            return None
        
        x = (a1 * p1['x'] - a2 * p2['x'] - p1['y'] + p2['y']) / (a1 - a2)
        y = a1 * (x - p1['x']) + p1['y']
        
        return {'y': y, 'x': x}
    
    @staticmethod
    def intersection_two_distances(
        p1: Dict[str, float], d1: float,
        p2: Dict[str, float], d2: float
    ) -> Optional[Tuple[Dict[str, float], Dict[str, float]]]:
        """
        Calculate intersection of two circles (distance-distance).
        Returns two possible solutions.
        
        Args:
            p1: First center point
            d1: First circle radius
            p2: Second center point
            d2: Second circle radius
            
        Returns:
            Tuple of two intersection points or None
        """
        dy = p2['y'] - p1['y']
        dx = p2['x'] - p1['x']
        d = math.sqrt(dy * dy + dx * dx)
        
        if d > d1 + d2 or d < abs(d1 - d2):
            return None
        
        a = (d1 * d1 - d2 * d2 + d * d) / (2 * d)
        h = math.sqrt(max(0, d1 * d1 - a * a))
        
        xm = p1['x'] + a * dx / d
        ym = p1['y'] + a * dy / d
        
        dx_perp = dy / d
        dy_perp = -dx / d
        
        p3 = {'y': ym + h * dy_perp, 'x': xm + h * dx_perp}
        p4 = {'y': ym - h * dy_perp, 'x': xm - h * dx_perp}
        
        return (p3, p4)
    
    @staticmethod
    def intersection_line_distance(
        p1: Dict[str, float], bearing1: float,
        p2: Dict[str, float], distance2: float
    ) -> Optional[Tuple[Dict[str, float], Dict[str, float]]]:
        """
        Calculate intersection of line (point+bearing) and circle (point+radius).
        
        Args:
            p1: Point on line
            bearing1: Line bearing
            p2: Circle center
            distance2: Circle radius
            
        Returns:
            Tuple of two intersection points or None
        """
        cos_a = math.cos(CalculatorService.grads_to_radians(bearing1))
        sin_a = math.sin(CalculatorService.grads_to_radians(bearing1))
        
        dx = p2['x'] - p1['x']
        dy = p2['y'] - p1['y']
        
        A = 1.0
        B = -2.0 * (dx * cos_a + dy * sin_a)
        C = dx * dx + dy * dy - distance2 * distance2
        
        discriminant = B * B - 4 * A * C
        
        if discriminant < 0:
            return None
        
        t1 = (-B + math.sqrt(discriminant)) / (2 * A)
        t2 = (-B - math.sqrt(discriminant)) / (2 * A)
        
        p3 = {'y': p1['y'] + t1 * sin_a, 'x': p1['x'] + t1 * cos_a}
        p4 = {'y': p1['y'] + t2 * sin_a, 'x': p1['x'] + t2 * cos_a}
        
        return (p3, p4)
    
    # =========================================================================
    # INTERPOLATION (MASSAH12)
    # =========================================================================
    
    @staticmethod
    def interpolate_points(
        points: Dict[int, Dict[str, float]],
        lines: List[Tuple[int, int]],
        vertical_interval: float
    ) -> List[Dict[str, Any]]:
        """
        Interpolate points at vertical intervals along line segments.
        Original MASSAH12.BAS algorithm.
        
        Args:
            points: Dict of {point_no: {'y': y, 'x': x, 'h': h}}
            lines: List of (from_no, to_no) tuples
            vertical_interval: Vertical interval in meters
            
        Returns:
            List of interpolation results with coordinates
        """
        if vertical_interval <= 0:
            raise SurveyingError("Vertical interval must be positive")
        
        results = []
        
        for from_no, to_no in lines:
            if from_no not in points or to_no not in points:
                continue
            
            p1 = points[from_no]
            p2 = points[to_no]
            
            dh = p2['h'] - p1['h']
            if abs(dh) < 0.001:
                continue
            
            distance = CalculatorService.calculate_distance(p1, p2)
            
            t = -1 if dh < 0 else 1
            
            h1_frac = p1['h'] - math.floor(p1['h'])
            
            e = 1
            while True:
                dk = h1_frac - e * vertical_interval
                if dk < 0:
                    break
                e += 1
            
            if t == 1:
                h_result = math.floor(p1['h']) + e * vertical_interval
            else:
                h_result = math.floor(p1['h']) + (e - 1) * vertical_interval
            
            h_diff = h_result - p1['h']
            d1 = distance * h_diff / dh
            
            if d1 > distance or d1 < 0:
                continue
            
            interpolated = []
            current_h = h_result
            current_d = d1
            
            direction_y = p2['y'] - p1['y']
            direction_x = p2['x'] - p1['x']
            
            while True:
                interpolated.append({
                    'height': round(current_h, 3),
                    'distance': round(current_d, 3),
                    'y': round(p1['y'] + direction_y * current_d / distance, 3),
                    'x': round(p1['x'] + direction_x * current_d / distance, 3)
                })
                
                current_h = current_h + vertical_interval * t
                
                if t == 1 and current_h >= p2['h']:
                    current_h = p2['h']
                    h_diff_final = current_h - p1['h']
                    current_d = distance * h_diff_final / dh
                    interpolated.append({
                        'height': round(current_h, 3),
                        'distance': round(current_d, 3),
                        'y': round(p1['y'] + direction_y * current_d / distance, 3),
                        'x': round(p1['x'] + direction_x * current_d / distance, 3)
                    })
                    break
                
                if t == -1 and current_h <= p2['h']:
                    current_h = p2['h']
                    h_diff_final = current_h - p1['h']
                    current_d = distance * h_diff_final / dh
                    interpolated.append({
                        'height': round(current_h, 3),
                        'distance': round(current_d, 3),
                        'y': round(p1['y'] + direction_y * current_d / distance, 3),
                        'x': round(p1['x'] + direction_x * current_d / distance, 3)
                    })
                    break
                
                h_diff_new = current_h - p1['h']
                current_d = distance * h_diff_new / dh
            
            results.append({
                'from': from_no,
                'to': to_no,
                'total_distance': round(distance, 3),
                'height_diff': round(dh, 3),
                'points': interpolated
            })
        
        return results
    
    # =========================================================================
    # 3-POINT RESECTION (MASSAH09 - Tienstra Method)
    # =========================================================================
    
    @staticmethod
    def resection_3point(
        p1: Dict[str, float], angle1: float,
        p2: Dict[str, float], angle2: float,
        p3: Dict[str, float], angle3: float
    ) -> Optional[Dict[str, float]]:
        """
        Calculate station position using 3-point resection with Tienstra's formula.
        Original MASSAH09.BAS algorithm.
        
        Args:
            p1, p2, p3: Known control points with 'y' and 'x'
            angle1, angle2, angle3: Observed angles at unknown station (in grads)
            
        Returns:
            Calculated station position {'y': y, 'x': x} or None on error
        """
        try:
            w1 = 1.0 / math.tan(CalculatorService.grads_to_radians(angle1))
            w2 = 1.0 / math.tan(CalculatorService.grads_to_radians(angle2))
            w3 = 1.0 / math.tan(CalculatorService.grads_to_radians(angle3))
            
            sum_w = w1 + w2 + w3
            
            if abs(sum_w) < 0.0001:
                return None
            
            x_station = (w1 * p1['x'] + w2 * p2['x'] + w3 * p3['x']) / sum_w
            y_station = (w1 * p1['y'] + w2 * p2['y'] + w3 * p3['y']) / sum_w
            
            return {'y': y_station, 'x': x_station}
        
        except (ValueError, ZeroDivisionError):
            return None
    
    @staticmethod
    def resection_2point(
        p1: Dict[str, float], dist1: float,
        p2: Dict[str, float], dist2: float
    ) -> Optional[Tuple[Dict[str, float], Dict[str, float]]]:
        """
        Calculate station position from 2 points with distances.
        Returns two possible solutions.
        
        Args:
            p1: First control point
            dist1: Distance to station from p1
            p2: Second control point
            dist2: Distance to station from p2
            
        Returns:
            Tuple of two possible station positions or None
        """
        dy = p2['y'] - p1['y']
        dx = p2['x'] - p1['x']
        d = math.sqrt(dy * dy + dx * dx)
        
        if d <= 0 or dist1 <= 0 or dist2 <= 0:
            return None
        
        if dist1 + dist2 <= d or dist1 + d <= dist2 or dist2 + d <= dist1:
            return None
        
        a = (dist1 * dist1 - dist2 * dist2 + d * d) / (2 * d)
        h = math.sqrt(max(0, dist1 * dist1 - a * a))
        
        xm = p1['x'] + a * dx / d
        ym = p1['y'] + a * dy / d
        
        dx_perp = dy / d
        dy_perp = -dx / d
        
        p3 = {'y': ym + h * dy_perp, 'x': xm + h * dx_perp}
        p4 = {'y': ym - h * dy_perp, 'x': xm - h * dx_perp}
        
        return (p3, p4)
    
    # =========================================================================
    # CIRCLE CENTER FROM 3 POINTS (MASSAH07)
    # =========================================================================
    
    @staticmethod
    def circle_center_3points(
        p1: Dict[str, float],
        p2: Dict[str, float],
        p3: Dict[str, float]
    ) -> Optional[Dict[str, float]]:
        """
        Calculate circle center and radius from 3 non-collinear points.
        Uses circumcenter determination.
        
        Args:
            p1, p2, p3: Three points on the circle
            
        Returns:
            {'y': center_y, 'x': center_x, 'radius': r} or None if collinear
        """
        x1, y1 = p1['x'], p1['y']
        x2, y2 = p2['x'], p2['y']
        x3, y3 = p3['x'], p3['y']
        
        d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
        
        if abs(d) < 0.0000001:
            return None
        
        x_center = ((x1**2 + y1**2) * (y2 - y3) +
                     (x2**2 + y2**2) * (y3 - y1) +
                     (x3**2 + y3**2) * (y1 - y2)) / d
        
        y_center = ((x1**2 + y1**2) * (x3 - x2) +
                     (x2**2 + y2**2) * (x1 - x3) +
                     (x3**2 + y3**2) * (x2 - x1)) / d
        
        radius = CalculatorService.calculate_distance(
            {'y': y_center, 'x': x_center}, p1
        )
        
        return {'y': y_center, 'x': x_center, 'radius': radius}
    
    # =========================================================================
    # OFFSET CALCULATIONS (MASSAH06)
    # =========================================================================
    
    @staticmethod
    def calculate_offset_point(
        line_start: Dict[str, float],
        line_end: Dict[str, float],
        distance: float,
        side: str = 'LEFT'
    ) -> Dict[str, float]:
        """
        Calculate point offset from line segment.
        Original MASSAH06.BAS algorithm.
        
        Args:
            line_start: Start point of line
            line_end: End point of line
            distance: Distance along line from start
            side: 'LEFT' or 'RIGHT' offset
            
        Returns:
            Calculated point {'y': y, 'x': x}
        """
        dy_line = line_end['y'] - line_start['y']
        dx_line = line_end['x'] - line_start['x']
        
        line_length = math.sqrt(dy_line * dy_line + dx_line * dx_line)
        
        if line_length < 0.0001:
            raise SurveyingError("Line too short")
        
        fnxof_y = dy_line / line_length
        fnxof_x = dx_line / line_length
        
        offset = distance
        if side == 'RIGHT':
            offset = -distance
        
        point_y = line_start['y'] + fnxof_y * offset + fnxof_x * distance
        point_x = line_start['x'] + fnxof_x * offset - fnxof_y * distance
        
        return {'y': point_y, 'x': point_x}
    
    # =========================================================================
    # FREE NUMBERS (Deleted Points)
    # =========================================================================
    
    @staticmethod
    def get_free_numbers(
        points: List[Dict[str, Any]],
        from_no: int = 1,
        to_no: int = 9999
    ) -> List[Dict[str, Any]]:
        """
        Get list of deleted/unallocated points (Y=0, X=0).
        Original MASSAH01.BAS algorithm - FREE NUMBERS prints only deleted points.
        
        Args:
            points: List of all points
            from_no: Start point number range
            to_no: End point number range
            
        Returns:
            List of free (deleted) points
        """
        free_points = []
        
        for p in points:
            no = p.get('no', 0)
            if from_no <= no <= to_no:
                if abs(p.get('y', 0)) < 0.01 and abs(p.get('x', 0)) < 0.01:
                    free_points.append(p)
        
        return free_points
    
    # =========================================================================
    # BOWDITCH TRAVERSE ADJUSTMENT
    # =========================================================================
    
    @staticmethod
    def bowditch_traverse(
        points: List[Dict[str, Any]],
        known_start: Optional[Dict[str, float]] = None,
        known_end: Optional[Dict[str, float]] = None
    ) -> TraverseResult:
        """
        Perform closed traverse adjustment using Bowditch (Compass Rule).
        Original MASSAH11.BAS algorithm.
        
        Args:
            points: List of traverse points with delta_y, delta_x, distance
            known_start: Known start point (optional)
            known_end: Known end point for closing (optional)
            
        Returns:
            TraverseResult with adjusted coordinates and error analysis
        """
        if len(points) < 2:
            raise SurveyingError("Need at least 2 points for traverse")
        
        total_distance = sum(p.get('distance', 0) for p in points)
        
        if total_distance < 0.0001:
            raise SurveyingError("Total distance is too small")
        
        sum_delta_y = sum(p.get('delta_y', 0) for p in points)
        sum_delta_x = sum(p.get('delta_x', 0) for p in points)
        
        if known_end and known_start:
            closure_y = known_end['y'] - (known_start['y'] + sum_delta_y)
            closure_x = known_end['x'] - (known_start['x'] + sum_delta_x)
        else:
            closure_y = -sum_delta_y
            closure_x = -sum_delta_x
        
        linear_misclosure = math.sqrt(closure_y * closure_y + closure_x * closure_x)
        precision_ratio = total_distance / linear_misclosure if linear_misclosure > 0 else 0
        
        adjusted_points = []
        correction_y = 0.0
        correction_x = 0.0
        
        cumulative_distance = 0.0
        
        for p in points:
            cumulative_distance += p.get('distance', 0)
            
            correction_factor = cumulative_distance / total_distance
            
            correction_y = closure_y * correction_factor
            correction_x = closure_x * correction_factor
            
            adjusted = {
                'no': p.get('no'),
                'y': p.get('y', 0) + correction_y,
                'x': p.get('x', 0) + correction_x,
                'h': p.get('h', 0),
                'delta_y': p.get('delta_y', 0),
                'delta_x': p.get('delta_x', 0),
                'distance': p.get('distance', 0),
                'correction_y': round(correction_y, 4),
                'correction_x': round(correction_x, 4)
            }
            adjusted_points.append(adjusted)
        
        return TraverseResult(
            adjusted_points=adjusted_points,
            closure_error_x=round(closure_x, 4),
            closure_error_y=round(closure_y, 4),
            linear_misclosure=round(linear_misclosure, 4),
            precision_ratio=round(precision_ratio, 0) if precision_ratio > 0 else 0,
            total_distance=round(total_distance, 2)
        )
    
    # =========================================================================
    # UTILITY FUNCTIONS
    # =========================================================================
    
    @staticmethod
    def format_coordinate(value: float, decimals: int = 2) -> str:
        """Format coordinate for display."""
        return f"{value:.{decimals}f}"
    
    @staticmethod
    def format_angle(value: float, unit: str = 'GRADS') -> str:
        """Format angle for display."""
        if unit == 'DEGREES':
            value = value * 9 / 10
        return f"{value:.4f} {unit}"
