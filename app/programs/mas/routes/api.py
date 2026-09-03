"""
API routes for MAS application.
Provides JSON endpoints for AJAX operations.
All surveying calculations run through CalculatorService.
"""
from flask import Blueprint, request, jsonify, session, current_app
from app.services.calculator import CalculatorService, SurveyingError

api_bp = Blueprint('api', __name__)


def get_db():
    return current_app.config['DATABASE']


def error_response(message, status=400):
    return jsonify({'error': message}), status


def success_response(**kwargs):
    return jsonify({'status': 'ok', **kwargs})


@api_bp.route('/set-file', methods=['POST'])
def set_current_file():
    """Set the current working file."""
    data = request.json
    filename = data.get('filename', '')
    
    if not filename:
        return error_response('Filename required')
    
    session['current_file'] = filename
    return success_response(filename=filename)


@api_bp.route('/current-file')
def get_current_file():
    """Get current file info."""
    filename = session.get('current_file')
    if not filename:
        return jsonify({'file': None})
    
    from app.shared.models import SurveyFile
    file_info = SurveyFile.get_by_name(get_db(), filename)
    return jsonify({'file': file_info})


@api_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    """Get or update settings."""
    from app.shared.models import Settings
    
    if request.method == 'POST':
        data = request.json
        for key, value in data.items():
            Settings.set(get_db(), key, value)
        session.pop('settings', None)
        return success_response()
    
    settings_obj = Settings.get_all(get_db())
    return jsonify(settings_obj)


@api_bp.route('/files', methods=['GET', 'POST'])
def files_list():
    """List or create survey files."""
    from app.shared.models import SurveyFile
    
    if request.method == 'POST':
        data = request.json
        name = data.get('name', '').strip()
        
        if not name:
            return error_response('Name required')
        
        result = SurveyFile.create(
            get_db(),
            name=name,
            date=data.get('date'),
            place=data.get('place')
        )
        
        if not result:
            return error_response('File exists')
        
        return success_response(file=result)
    
    files = SurveyFile.get_all(get_db())
    return jsonify(files)


@api_bp.route('/files/upload', methods=['POST'])
def upload_file():
    """Upload and parse a DTF file."""
    from app.shared.models import SurveyFile, SurveyPoint
    import os
    import re
    import struct
    
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    if 'file' not in request.files:
        return error_response('No file provided')
    
    file = request.files['file']
    
    if file.filename == '':
        return error_response('No file selected')
    
    filename = file.filename
    if not re.match(r'^[\w\s\-\.]+\.DTF$', filename, re.IGNORECASE):
        return error_response('Invalid file type. Only DTF files allowed')
    
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    
    if size > MAX_FILE_SIZE:
        return error_response('File too large. Maximum 10MB allowed')
    
    if size < 50:
        return error_response('File is too small or corrupted')
    
    try:
        content = file.read()
        
        header_check = content[:15]
        if not header_check.decode('ascii', errors='ignore').replace(' ', '').isalnum():
            return error_response('Invalid DTF file format')
        
        points = parse_dtf_file(content)
        
        if not points:
            return error_response('No valid points found in file')
        
        base_name = os.path.splitext(filename)[0]
        safe_name = re.sub(r'[^\w\s\-]', '', base_name)[:50]
        
        if not safe_name:
            safe_name = 'uploaded_file'
        
        original_name = safe_name
        counter = 1
        while SurveyFile.get_by_name(get_db(), safe_name):
            safe_name = f"{original_name}_{counter}"
            counter += 1
        
        from datetime import datetime
        file_result = SurveyFile.create(
            get_db(),
            name=safe_name,
            date=datetime.now().strftime('%Y-%m-%d'),
            place='Uploaded'
        )
        
        if not file_result:
            return error_response('Failed to create file', 500)
        
        point_count = SurveyPoint.save_batch(get_db(), safe_name, points)
        session['current_file'] = safe_name
        
        return success_response(
            file=file_result,
            points_count=point_count,
            filename=safe_name
        )
        
    except Exception as e:
        return error_response('Failed to parse file: ' + str(e), 500)


def parse_dtf_file(content):
    """Parse DTF file format (Survey Data File)."""
    import struct
    
    if len(content) < 50:
        return []
    
    try:
        header = content[:15].decode('ascii', errors='ignore')
        if not header.strip():
            return []
        
        marker_pos = content.find(b'\xdc\x05\x00\x00')
        
        if marker_pos == -1:
            marker_pos = content.find(b'\xdc\x05')
            if marker_pos == -1:
                return []
        
        data_start = marker_pos + 40
        
        if data_start >= len(content):
            return []
        
        binary_data = content[data_start:]
        points = []
        i = 0
        
        while i + 24 <= len(binary_data):
            try:
                y = struct.unpack('<d', binary_data[i:i+8])[0]
                x = struct.unpack('<d', binary_data[i+8:i+16])[0]
                h = struct.unpack('<d', binary_data[i+16:i+24])[0]
                
                if (0 < abs(y) < 50_000_000 and 
                    0 < abs(x) < 50_000_000 and 
                    -1000 < h < 10000):
                    
                    if not (abs(y) < 0.001 and abs(x) < 0.001 and abs(h) < 0.001):
                        points.append({
                            'no': len(points) + 1,
                            'y': round(y, 3),
                            'x': round(x, 3),
                            'h': round(h, 3)
                        })
                
                i += 24
            except:
                i += 24
        
        return points
        
    except Exception:
        return []


@api_bp.route('/guide')
def get_guide():
    """Get MAS user guide content."""
    import os
    import re
    
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    guide_path = os.path.join(base_dir, 'USER_GUIDE.md')
    
    try:
        with open(guide_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        html = content
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1 style="color:#00ff41;font-size:18px;margin-bottom:15px;">\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong style="color:#00ff41;">\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        html = re.sub(r'\n\n+', r'<br><br>', html)
        html = re.sub(r'---', '<hr style="border:0;border-top:1px solid #004400;margin:15px 0;">', html)
        
        lines = html.split('\n')
        in_table = False
        formatted_lines = []
        for line in lines:
            if line.strip().startswith('|'):
                if not in_table:
                    in_table = True
                    formatted_lines.append('<table style="width:100%;border-collapse:collapse;margin:10px 0;font-size:12px;">')
                    parts = [p.strip() for p in line.split('|')[1:-1]]
                    if parts:
                        formatted_lines.append('<tr>')
                        for p in parts:
                            formatted_lines.append(f'<th style="border:1px solid #004400;padding:8px;background:#001a00;color:#00ff41;">{p}</th>')
                        formatted_lines.append('</tr>')
                else:
                    parts = [p.strip() for p in line.split('|')[1:-1]]
                    if '-' in line:
                        continue
                    formatted_lines.append('<tr>')
                    for p in parts:
                        formatted_lines.append(f'<td style="border:1px solid #004400;padding:6px;">{p}</td>')
                    formatted_lines.append('</tr>')
            else:
                if in_table:
                    in_table = False
                    formatted_lines.append('</table>')
                formatted_lines.append(line)
        
        if in_table:
            formatted_lines.append('</table>')
        
        html = '\n'.join(formatted_lines)
        return html
        
    except Exception as e:
        return f'<p style="color:red;">Error loading guide: {str(e)}</p>'


@api_bp.route('/files/<name>', methods=['GET', 'DELETE'])
def file_detail(name):
    """Get or delete a specific file."""
    from app.shared.models import SurveyFile
    
    if request.method == 'DELETE':
        file_info = SurveyFile.get_by_name(get_db(), name)
        if not file_info:
            return error_response('File not found', 404)
        SurveyFile.delete(get_db(), name)
        return success_response()
    
    file_info = SurveyFile.get_by_name(get_db(), name)
    if not file_info:
        return error_response('Not found', 404)
    
    return jsonify(file_info)


@api_bp.route('/points', methods=['GET'])
def get_points():
    """Get points for current file."""
    filename = session.get('current_file')
    if not filename:
        return jsonify([])
    
    from app.shared.models import SurveyPoint
    points = SurveyPoint.get_by_file(get_db(), filename)
    return jsonify(points)


@api_bp.route('/points', methods=['POST'])
def save_points():
    """Save points for current file."""
    filename = session.get('current_file')
    if not filename:
        return error_response('No file selected')
    
    data = request.json
    points = data.get('points', [])
    
    from app.shared.models import SurveyPoint
    count = SurveyPoint.save_batch(get_db(), filename, points)
    
    return success_response(count=count)


@api_bp.route('/calculate/area', methods=['POST'])
def calculate_area():
    """Calculate area using Surveyor's formula."""
    data = request.json
    points = data.get('points', [])
    
    if len(points) < 3:
        return error_response('Need at least 3 points')
    
    try:
        area = CalculatorService.calculate_area(points)
        perimeter = CalculatorService.calculate_perimeter(points)
        return jsonify({
            'area': round(area, 3),
            'perimeter': round(perimeter, 3),
            'formatted': f"{area:.2f} m²"
        })
    except SurveyingError as e:
        return error_response(str(e))


@api_bp.route('/calculate/perimeter', methods=['POST'])
def calculate_perimeter():
    """Calculate perimeter from points."""
    data = request.json
    points = data.get('points', [])
    
    try:
        perimeter = CalculatorService.calculate_perimeter(points)
        return jsonify({
            'perimeter': round(perimeter, 3),
            'formatted': f"{perimeter:.2f} m"
        })
    except SurveyingError as e:
        return error_response(str(e))


@api_bp.route('/calculate/polar', methods=['POST'])
def calculate_polar():
    """
    Calculate polar coordinates (Distomat, Tacheometry, Azimuth-Distance).
    """
    data = request.json
    polar_type = data.get('type', 'DISTOMAT')
    station_no = data.get('station_no', 1)
    back_azimuth = data.get('back_azimuth', 0)
    observations = data.get('observations', [])
    
    results = []
    for obs in observations:
        distance = obs.get('distance', 0)
        angle = obs.get('angle', 0)
        h = obs.get('h', 0)
        
        bearing = (back_azimuth + angle) % 400
        
        delta_y, delta_x = CalculatorService.polar_to_cartesian(distance, bearing)
        
        results.append({
            'no': obs.get('no'),
            'y': round(delta_y, 3),
            'x': round(delta_x, 3),
            'h': h,
            'bearing': round(bearing, 4)
        })
    
    return jsonify({
        'status': 'ok',
        'type': polar_type,
        'results': results
    })


@api_bp.route('/calculate/offsets', methods=['POST'])
def calculate_offsets():
    """Calculate offsets from line to points (MASSAH06 algorithm)."""
    data = request.json
    line_start = data.get('line_start', {'y': 0, 'x': 0})
    line_end = data.get('line_end', {'y': 100, 'x': 100})
    points = data.get('points', [])
    
    results = []
    for p in points:
        offset_dist = p.get('offset_distance', 0)
        side = p.get('side', 'LEFT')
        
        try:
            result = CalculatorService.calculate_offset_point(
                line_start, line_end, offset_dist, side
            )
            results.append({
                'no': p.get('no'),
                'y': round(result['y'], 3),
                'x': round(result['x'], 3),
                'side': side
            })
        except SurveyingError as e:
            results.append({
                'no': p.get('no'),
                'error': str(e),
                'side': side
            })
    
    return jsonify({
        'status': 'ok',
        'results': results
    })


@api_bp.route('/calculate/intersection', methods=['POST'])
def calculate_intersection():
    """Calculate intersection of two lines, circles, or line-circle."""
    data = request.json
    intersection_type = data.get('type', 'TWO_LINES')
    p1 = data.get('p1', {'y': 0, 'x': 0})
    p2 = data.get('p2', {'y': 0, 'x': 0})
    
    try:
        if intersection_type == 'TWO_LINES' or intersection_type == 'BEARING_BEARING':
            bearing1 = data.get('bearing1', 0)
            bearing2 = data.get('bearing2', 100)
            result = CalculatorService.intersection_two_lines(p1, bearing1, p2, bearing2)
            
            if result is None:
                return error_response('Lines are parallel or nearly parallel')
            
            return jsonify({
                'status': 'ok',
                'type': intersection_type,
                'point': {'y': round(result['y'], 3), 'x': round(result['x'], 3)}
            })
        
        elif intersection_type == 'TWO_DISTANCES':
            d1 = data.get('distance1', 100)
            d2 = data.get('distance2', 100)
            result = CalculatorService.intersection_two_distances(p1, d1, p2, d2)
            
            if result is None:
                return error_response('Circles do not intersect')
            
            return jsonify({
                'status': 'ok',
                'type': intersection_type,
                'point1': {'y': round(result[0]['y'], 3), 'x': round(result[0]['x'], 3)},
                'point2': {'y': round(result[1]['y'], 3), 'x': round(result[1]['x'], 3)}
            })
        
        elif intersection_type == 'LINE_DISTANCE':
            bearing1 = data.get('bearing1', 0)
            distance2 = data.get('distance2', 100)
            result = CalculatorService.intersection_line_distance(p1, bearing1, p2, distance2)
            
            if result is None:
                return error_response('Line and circle do not intersect')
            
            return jsonify({
                'status': 'ok',
                'type': intersection_type,
                'point1': {'y': round(result[0]['y'], 3), 'x': round(result[0]['x'], 3)},
                'point2': {'y': round(result[1]['y'], 3), 'x': round(result[1]['x'], 3)}
            })
        
        else:
            return error_response('Unknown intersection type')
            
    except SurveyingError as e:
        return error_response(str(e))


@api_bp.route('/calculate/implant', methods=['POST'])
def calculate_implant():
    """Calculate implantation (stake out) point from base and direction."""
    data = request.json
    base = data.get('base_point', {'y': 0, 'x': 0, 'h': 0})
    distance = data.get('distance', 0)
    bearing = data.get('bearing', 0)
    height = data.get('height', 0)
    
    delta_y, delta_x = CalculatorService.polar_to_cartesian(distance, bearing)
    
    implant_point = {
        'y': round(base['y'] + delta_y, 3),
        'x': round(base['x'] + delta_x, 3),
        'h': height if height else base.get('h', 0)
    }
    
    return jsonify({
        'status': 'ok',
        'base': base,
        'implant': implant_point,
        'distance': distance,
        'bearing': bearing
    })


@api_bp.route('/calculate/circle', methods=['POST'])
def calculate_circle():
    """Circle calculations (ARC, CIRCUMFERENCE, AREA, CENTER, etc.)."""
    import math
    
    data = request.json
    calc_type = data.get('type', 'AREA')
    v1 = data.get('value1', 0)
    v2 = data.get('value2', 0)
    
    result = 0
    result_unit = ''
    
    if calc_type == 'ARC':
        angle = v1
        radius = v2
        result = (angle / 200) * math.pi * radius
        result_unit = 'm'
    
    elif calc_type == 'CIRCUMFERENCE':
        radius = v1
        result = 2 * math.pi * radius
        result_unit = 'm'
    
    elif calc_type == 'AREA':
        radius = v1
        result = math.pi * radius * radius
        result_unit = 'm²'
    
    elif calc_type == 'CENTER':
        p1 = data.get('p1', {'y': 0, 'x': 0})
        p2 = data.get('p2', {'y': 0, 'x': 0})
        p3 = data.get('p3', {'y': 0, 'x': 0})
        center_result = CalculatorService.circle_center_3points(p1, p2, p3)
        
        if center_result is None:
            return error_response('Points are collinear - cannot calculate circle center')
        
        return jsonify({
            'status': 'ok',
            'type': calc_type,
            'center': {
                'y': round(center_result['y'], 3),
                'x': round(center_result['x'], 3)
            },
            'radius': round(center_result['radius'], 3)
        })
    
    elif calc_type == 'RADIUS':
        if v2 > 0:
            result = math.sqrt(v1 / math.pi)
        else:
            result = v1 / (2 * math.pi)
        result_unit = 'm'
    
    elif calc_type == 'CHORD':
        radius = v1
        angle = v2
        result = 2 * radius * math.sin((angle * math.pi / 200) / 2)
        result_unit = 'm'
    
    return jsonify({
        'status': 'ok',
        'type': calc_type,
        'result': round(result, 3),
        'unit': result_unit
    })


@api_bp.route('/calculate/resection', methods=['POST'])
def calculate_resection():
    """
    3-Point or 2-Point Resection (Tienstra's formula).
    
    3-Point: Calculate station position from 3 known points with observed angles
    2-Point: Calculate station position from 2 known points with distances
    """
    data = request.json
    resection_type = data.get('type', '3POINTS')
    
    try:
        if resection_type == '3POINTS':
            p1 = data.get('p1', {'y': 0, 'x': 0})
            p2 = data.get('p2', {'y': 0, 'x': 0})
            p3 = data.get('p3', {'y': 0, 'x': 0})
            angle1 = data.get('angle1', 0)
            angle2 = data.get('angle2', 0)
            angle3 = data.get('angle3', 0)
            
            station = CalculatorService.resection_3point(p1, angle1, p2, angle2, p3, angle3)
            
            if station is None:
                return error_response('Resection calculation failed - check angles')
            
            return jsonify({
                'status': 'ok',
                'type': '3POINTS',
                'point': {'y': round(station['y'], 3), 'x': round(station['x'], 3)}
            })
        
        elif resection_type == '2POINTS':
            p1 = data.get('p1', {'y': 0, 'x': 0})
            p2 = data.get('p2', {'y': 0, 'x': 0})
            dist1 = data.get('dist1', 0)
            dist2 = data.get('dist2', 0)
            
            result = CalculatorService.resection_2point(p1, dist1, p2, dist2)
            
            if result is None:
                return error_response('2-point resection failed - check distances')
            
            return jsonify({
                'status': 'ok',
                'type': '2POINTS',
                'point1': {'y': round(result[0]['y'], 3), 'x': round(result[0]['x'], 3)},
                'point2': {'y': round(result[1]['y'], 3), 'x': round(result[1]['x'], 3)}
            })
        
        else:
            return error_response('Unknown resection type')
            
    except SurveyingError as e:
        return error_response(str(e))


@api_bp.route('/calculate/interpolation', methods=['POST'])
def calculate_interpolation():
    """
    Interpolation along line segments at vertical intervals (MASSAH12).
    """
    data = request.json
    vertical_interval = data.get('vertical_interval', 0.5)
    lines = data.get('lines', [])
    
    if vertical_interval <= 0:
        return error_response('Vertical interval must be positive')
    
    if not lines:
        return error_response('No lines specified')
    
    try:
        from app.shared.models import SurveyPoint
        filename = session.get('current_file')

        if not filename:
            return error_response('No file selected')

        points_list = SurveyPoint.get_by_file(get_db(), filename)
        points_dict = {
            p['no']: {'y': p.get('y', 0), 'x': p.get('x', 0), 'h': p.get('h', 0)}
            for p in points_list
        }
        
        results = CalculatorService.interpolate_points(points_dict, lines, vertical_interval)
        
        return jsonify({
            'status': 'ok',
            'vertical_interval': vertical_interval,
            'results': results
        })
        
    except SurveyingError as e:
        return error_response(str(e))
    except Exception as e:
        return error_response('Interpolation failed: ' + str(e))


@api_bp.route('/calculate/traverse', methods=['POST'])
def calculate_traverse():
    """
    Bowditch Traverse Adjustment (MASSAH11).
    """
    data = request.json
    points = data.get('points', [])
    known_start = data.get('known_start')
    known_end = data.get('known_end')
    
    if len(points) < 2:
        return error_response('Need at least 2 points for traverse')
    
    try:
        traverse_points = []
        for p in points:
            azimuth = p.get('azimuth', 0)
            distance = p.get('distance', 0)
            
            delta_y, delta_x = CalculatorService.polar_to_cartesian(distance, azimuth)
            
            traverse_points.append({
                'no': p.get('no'),
                'y': p.get('y', 0),
                'x': p.get('x', 0),
                'h': p.get('h', 0),
                'delta_y': delta_y,
                'delta_x': delta_x,
                'distance': distance
            })
        
        result = CalculatorService.bowditch_traverse(
            traverse_points,
            known_start,
            known_end
        )
        
        return jsonify({
            'status': 'ok',
            'total_distance': result.total_distance,
            'closure_error_y': result.closure_error_y,
            'closure_error_x': result.closure_error_x,
            'linear_misclosure': result.linear_misclosure,
            'precision_ratio': result.precision_ratio,
            'adjusted_points': result.adjusted_points
        })
        
    except SurveyingError as e:
        return error_response(str(e))


@api_bp.route('/calculate/freenumbers', methods=['POST'])
def calculate_freenumbers():
    """
    Get free (deleted) points where Y=0 and X=0.
    """
    data = request.json
    from_no = data.get('from_no', 1)
    to_no = data.get('to_no', 9999)
    
    try:
        from app.shared.models import SurveyPoint
        filename = session.get('current_file')
        
        if not filename:
            return error_response('No file selected')
        
        all_points = SurveyPoint.get_by_file(get_db(), filename)
        free_points = CalculatorService.get_free_numbers(all_points, from_no, to_no)
        
        return jsonify({
            'status': 'ok',
            'points': free_points,
            'count': len(free_points)
        })
        
    except SurveyingError as e:
        return error_response(str(e))


@api_bp.route('/print/coordinates', methods=['POST'])
def print_coordinates():
    """Get coordinates for printing."""
    data = request.json
    print_type = data.get('type', 'all')
    from_no = data.get('from_no', 1)
    to_no = data.get('to_no', 9999)
    
    try:
        from app.shared.models import SurveyFile, SurveyPoint
        
        filename = session.get('current_file')
        if not filename:
            return error_response('No file selected')
        
        all_points = SurveyPoint.get_by_file(get_db(), filename)
        file_info = SurveyFile.get_by_name(get_db(), filename)
        
        if print_type == 'single':
            filtered = [p for p in all_points if p.get('no') == from_no]
        elif print_type == 'group':
            filtered = [p for p in all_points if from_no <= p.get('no', 0) <= to_no]
        else:
            filtered = all_points
        
        return jsonify({
            'points': filtered,
            'header': file_info
        })
        
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/print/freenumbers', methods=['POST'])
def print_freenumbers():
    """Get free numbers for printing."""
    data = request.json
    from_no = data.get('from_no', 1)
    to_no = data.get('to_no', 9999)
    
    try:
        from app.shared.models import SurveyFile, SurveyPoint
        
        filename = session.get('current_file')
        if not filename:
            return error_response('No file selected')
        
        all_points = SurveyPoint.get_by_file(get_db(), filename)
        free_points = CalculatorService.get_free_numbers(all_points, from_no, to_no)
        file_info = SurveyFile.get_by_name(get_db(), filename)
        
        return jsonify({
            'points': free_points,
            'header': file_info
        })
        
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/print/gridlimits', methods=['GET'])
def print_gridlimits():
    """Get grid limits for printing."""
    try:
        from app.shared.models import SurveyFile, SurveyPoint
        
        filename = session.get('current_file')
        if not filename:
            return error_response('No file selected')
        
        points = SurveyPoint.get_by_file(get_db(), filename)
        file_info = SurveyFile.get_by_name(get_db(), filename)
        
        if not points:
            return error_response('No points in file')
        
        y_values = [p.get('y', 0) for p in points]
        x_values = [p.get('x', 0) for p in points]
        
        return jsonify({
            'grid': {
                'y_west': {'value': min(y_values)},
                'y_east': {'value': max(y_values)},
                'x_south': {'value': min(x_values)},
                'x_north': {'value': max(x_values)}
            },
            'header': file_info
        })
        
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/print/draw', methods=['GET'])
def print_draw():
    """Get all points with heights for drawing."""
    try:
        from app.shared.models import SurveyFile, SurveyPoint
        
        filename = session.get('current_file')
        if not filename:
            return error_response('No file selected')
        
        points = SurveyPoint.get_by_file(get_db(), filename)
        file_info = SurveyFile.get_by_name(get_db(), filename)
        
        has_heights = any(p.get('h', 0) != 0 for p in points)
        
        if not has_heights:
            return jsonify({'error': 'no_heights'})
        
        return jsonify({
            'points': points,
            'header': file_info
        })
        
    except Exception as e:
        return error_response(str(e))
