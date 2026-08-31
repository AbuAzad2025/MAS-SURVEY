"""
Surveying calculation services.
Contains all surveying mathematics and algorithms.
"""
import math


class SurveyCalculator:
    """
    Surveying calculations based on GW-BASIC original algorithms.
    All calculations maintain compatibility with the original MAS system.
    """
    
    GRADS_TO_RADIANS = math.pi / 200
    RADIANS_TO_GRADS = 200 / math.pi
    
    @staticmethod
    def grads_to_radians(grads):
        return grads * SurveyCalculator.GRADS_TO_RADIANS
    
    @staticmethod
    def radians_to_grads(radians):
        return radians * SurveyCalculator.RADIANS_TO_GRADS
    
    @staticmethod
    def polar_to_cartesian(distance, bearing, unit='GRADS'):
        if unit == 'DEGREES':
            bearing = bearing * 90 / 100
        
        angle_rad = SurveyCalculator.grads_to_radians(bearing)
        delta_y = distance * math.sin(angle_rad)
        delta_x = distance * math.cos(angle_rad)
        
        return delta_y, delta_x
    
    @staticmethod
    def calculate_area(points):
        if len(points) < 3:
            return 0
        
        area = 0
        n = len(points)
        
        for i in range(n):
            j = (i + 1) % n
            area += points[i]['y'] * points[j]['x']
            area -= points[j]['y'] * points[i]['x']
        
        return abs(area) / 2
    
    @staticmethod
    def calculate_perimeter(points):
        if len(points) < 2:
            return 0
        
        perimeter = 0
        n = len(points)
        
        for i in range(n):
            j = (i + 1) % n
            dy = points[j]['y'] - points[i]['y']
            dx = points[j]['x'] - points[i]['x']
            perimeter += math.sqrt(dy * dy + dx * dx)
        
        return perimeter
    
    @staticmethod
    def calculate_distance(y1, x1, y2, x2):
        dy = y2 - y1
        dx = x2 - x1
        return math.sqrt(dy * dy + dx * dx)
    
    @staticmethod
    def calculate_offset(point, line_start, line_end):
        dy_line = line_end['y'] - line_start['y']
        dx_line = line_end['x'] - line_start['x']
        
        dy_point = point['y'] - line_start['y']
        dx_point = point['x'] - line_start['x']
        
        line_length = math.sqrt(dy_line * dy_line + dx_line * dx_line)
        
        if line_length < 0.0001:
            return math.sqrt(dy_point * dy_point + dx_point * dx_point)
        
        offset = abs(dy_point * dx_line - dx_point * dy_line) / line_length
        
        return offset
    
    @staticmethod
    def calculate_intersection_two_lines(p1, bearing1, p2, bearing2, unit='GRADS'):
        if unit == 'DEGREES':
            bearing1 = bearing1 * 90 / 100
            bearing2 = bearing2 * 90 / 100
        
        a1 = math.tan(SurveyCalculator.grads_to_radians(bearing1))
        a2 = math.tan(SurveyCalculator.grads_to_radians(bearing2))
        
        if abs(a1 - a2) < 0.0001:
            return None
        
        x = (a1 * p1['x'] - a2 * p2['x'] - p1['y'] + p2['y']) / (a1 - a2)
        y = a1 * (x - p1['x']) + p1['y']
        
        return {'y': y, 'x': x}
    
    @staticmethod
    def calculate_intersection_two_distances(p1, d1, p2, d2):
        dy = p2['y'] - p1['y']
        dx = p2['x'] - p1['x']
        d = math.sqrt(dy * dy + dx * dx)
        
        if d > d1 + d2 or d < abs(d1 - d2):
            return None
        
        a = (d1 * d1 - d2 * d2 + d * d) / (2 * d)
        h = math.sqrt(d1 * d1 - a * a)
        
        dx_perp = dy / d
        dy_perp = -dx / d
        
        xm = p1['x'] + a * (dx / d)
        ym = p1['y'] + a * (dy / d)
        
        p3 = {
            'y': ym + h * dy_perp,
            'x': xm + h * dx_perp
        }
        p4 = {
            'y': ym - h * dy_perp,
            'x': xm - h * dx_perp
        }
        
        return (p3, p4)
    
    @staticmethod
    def calculate_intersection_line_distance(p1, bearing1, p2, distance2):
        a1 = math.tan(SurveyCalculator.grads_to_radians(bearing1))
        
        dx = p2['x'] - p1['x']
        dy = p2['y'] - p1['y']
        
        cos_a = math.cos(SurveyCalculator.grads_to_radians(bearing1))
        sin_a = math.sin(SurveyCalculator.grads_to_radians(bearing1))
        
        A = 1
        B = -2 * (dx * cos_a + dy * sin_a)
        C = dx * dx + dy * dy - distance2 * distance2
        
        discriminant = B * B - 4 * A * C
        
        if discriminant < 0:
            return None
        
        t1 = (-B + math.sqrt(discriminant)) / (2 * A)
        t2 = (-B - math.sqrt(discriminant)) / (2 * A)
        
        p3 = {
            'y': p1['y'] + t1 * sin_a,
            'x': p1['x'] + t1 * cos_a
        }
        p4 = {
            'y': p1['y'] + t2 * sin_a,
            'x': p1['x'] + t2 * cos_a
        }
        
        return (p3, p4)
    
    @staticmethod
    def traverse_adjustment(points, known_start=None, known_end=None, precision=1.0):
        if len(points) < 2:
            return points
        
        total_dy = sum(p.get('delta_y', 0) for p in points)
        total_dx = sum(p.get('delta_x', 0) for p in points)
        
        if not known_end:
            return points
        
        perimeter = sum(
            math.sqrt(p.get('delta_y', 0) ** 2 + p.get('delta_x', 0) ** 2)
            for p in points
        )
        
        if perimeter < 0.0001:
            return points
        
        correction_factor = precision / perimeter
        
        adjusted = []
        cumulative_correction_y = 0
        cumulative_correction_x = 0
        
        for p in points:
            cumulative_correction_y += total_dy * correction_factor
            cumulative_correction_x += total_dx * correction_factor
            
            adjusted.append({
                'y': p.get('y', 0) - cumulative_correction_y,
                'x': p.get('x', 0) - cumulative_correction_x,
                'h': p.get('h', 0)
            })
        
        return adjusted
    
    @staticmethod
    def interpolation(vertical_interval, lines, points_dict):
        """
        Interpolate points at vertical intervals along lines.
        Based on MASSAH12.BAS algorithm.
        
        Args:
            vertical_interval: Interval in meters (e.g., 0.5 for half meter)
            lines: List of point pairs [(from_no, to_no), ...]
            points_dict: Dict of {point_no: {'y': y, 'x': x, 'h': height}}
        
        Returns:
            List of interpolated results, each containing distance and height
        """
        results = []
        
        if vertical_interval <= 0:
            return results
        
        e4 = 1 / vertical_interval
        
        for (from_no, to_no) in lines:
            if from_no not in points_dict or to_no not in points_dict:
                continue
            
            p1 = points_dict[from_no]
            p2 = points_dict[to_no]
            
            dh = p2['h'] - p1['h']
            if abs(dh) < 0.001:
                continue
            
            distance = SurveyCalculator.calculate_distance(p1['y'], p1['x'], p2['y'], p2['x'])
            
            if dh < 0:
                t = -1
            else:
                t = 1
            
            h1_start = p1['h']
            h1_frac = h1_start - int(h1_start)
            
            e = 1
            while True:
                dk = h1_frac - e * vertical_interval
                if dk < 0:
                    break
                e += 1
            
            if t == 1:
                h_result = int(h1_start) + e * vertical_interval
            else:
                h_result = int(h1_start) + (e - 1) * vertical_interval
            
            h_diff = h_result - p1['h']
            d1 = distance * h_diff / dh
            
            if d1 > distance or d1 < 0:
                continue
            
            line_result = {
                'from': from_no,
                'to': to_no,
                'distance': distance,
                'height_diff': dh,
                'points': []
            }
            
            current_h = h_result
            current_d = d1
            
            while True:
                line_result['points'].append({
                    'distance': round(current_d, 2),
                    'height': round(current_h, 2)
                })
                
                current_h = current_h + vertical_interval * t
                
                if t == 1 and current_h > p2['h']:
                    break
                if t == -1 and current_h < p2['h']:
                    break
                if t == 1 and current_h > p2['h']:
                    current_h = p2['h']
                    h_diff_final = current_h - p1['h']
                    current_d = distance * h_diff_final / dh
                    line_result['points'].append({
                        'distance': round(current_d, 2),
                        'height': round(current_h, 2)
                    })
                    break
                if t == -1 and current_h < p2['h']:
                    current_h = p2['h']
                    h_diff_final = current_h - p1['h']
                    current_d = distance * h_diff_final / dh
                    line_result['points'].append({
                        'distance': round(current_d, 2),
                        'height': round(current_h, 2)
                    })
                    break
                
                h_diff_new = current_h - p1['h']
                current_d = distance * h_diff_new / dh
            
            results.append(line_result)
        
        return results
    
    @staticmethod
    def resection(p1, angle1, p2, angle2, p3, angle3):
        """
        Calculate station position from 3 known points and 2 angles.
        Based on MASSAH09.BAS algorithm.
        
        Args:
            p1, p2, p3: Known points with y, x coordinates
            angle1, angle2, angle3: Observed angles at station
        
        Returns:
            Calculated station coordinates
        """
        ya = p1['y']
        xa = p1['x']
        yb = p2['y']
        xb = p2['x']
        yc = p3['y']
        xc = p3['x']
        
        a1 = 1.0 / math.tan(SurveyCalculator.grads_to_radians(angle1))
        a2 = 1.0 / math.tan(SurveyCalculator.grads_to_radians(angle2))
        a3 = 1.0 / math.tan(SurveyCalculator.grads_to_radians(angle3))
        
        d12 = SurveyCalculator.calculate_distance(ya, xa, yb, xb)
        d13 = SurveyCalculator.calculate_distance(ya, xa, yc, xc)
        d23 = SurveyCalculator.calculate_distance(yb, xb, yc, xc)
        
        cos_a = (d12**2 + d13**2 - d23**2) / (2 * d12 * d13)
        cos_b = (d12**2 + d23**2 - d13**2) / (2 * d12 * d23)
        cos_c = (d13**2 + d23**2 - d12**2) / (2 * d13 * d23)
        
        term1 = d12 * cos_a * a3
        term2 = d12 * cos_b * a2
        term3 = d13 * cos_a * a3
        term4 = d13 * cos_c * a1
        
        denom = term1 + term2 - term3 - term4
        
        if abs(denom) < 0.0001:
            return None
        
        x_station = ((yb - ya) * term1 + (xc - xa) * term2) / denom
        y_station = ((xb - xa) * term1 + (yc - ya) * term2) / denom
        
        return {'y': y_station, 'x': x_station}
    
    @staticmethod
    def resection_simple(p1, p2, dist1, dist2):
        """
        Simple resection from 2 points with distances.
        Returns two possible solutions.
        """
        ya, xa = p1['y'], p1['x']
        yb, xb = p2['y'], p2['x']
        
        d = SurveyCalculator.calculate_distance(ya, xa, yb, xb)
        
        if dist1 > d or dist2 > d:
            return None
        
        a = (dist1**2 - dist2**2 + d**2) / (2 * d)
        h = math.sqrt(dist1**2 - a**2)
        
        dx = xb - xa
        dy = yb - ya
        
        xm = xa + a * dx / d
        ym = ya + a * dy / d
        
        dx_perp = dy / d
        dy_perp = -dx / d
        
        p3 = {
            'y': ym + h * dy_perp,
            'x': xm + h * dx_perp
        }
        p4 = {
            'y': ym - h * dy_perp,
            'x': xm - h * dx_perp
        }
        
        return (p3, p4)
    
    @staticmethod
    def _sqrt(value):
        return math.sqrt(value) if value > 0 else 0
    
    @staticmethod
    def format_coordinate(value, decimals=2):
        return f"{value:.{decimals}f}"
    
    @staticmethod
    def format_angle(value, unit='GRADS'):
        if unit == 'DEGREES':
            value = value * 9 / 10
        return f"{value:.4f} {unit}"
