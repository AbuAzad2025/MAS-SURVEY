"""
API routes for MAS application.
Provides JSON endpoints for AJAX operations.
"""
from flask import Blueprint, request, jsonify, session, current_app
from app.shared.models import SurveyFile, SurveyPoint, Settings
import os
import re
import struct

api_bp = Blueprint('api', __name__)


@api_bp.route('/set-file', methods=['POST'])
def set_current_file():
    """Set the current working file."""
    data = request.json
    filename = data.get('filename', '')
    
    if not filename:
        return jsonify({'error': 'Filename required'}), 400
    
    session['current_file'] = filename
    return jsonify({'status': 'ok', 'filename': filename})


@api_bp.route('/current-file')
def get_current_file():
    """Get current file info."""
    filename = session.get('current_file')
    if not filename:
        return jsonify({'file': None})
    
    file_info = SurveyFile.get_by_name(current_app.config['DATABASE'], filename)
    return jsonify({'file': file_info})


@api_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    """Get or update settings."""
    if request.method == 'POST':
        data = request.json
        for key, value in data.items():
            Settings.set(current_app.config['DATABASE'], key, value)
        session.pop('settings', None)
        return jsonify({'status': 'ok'})
    
    settings = Settings.get_all(current_app.config['DATABASE'])
    return jsonify(settings)


@api_bp.route('/files', methods=['GET', 'POST'])
def files_list():
    """List or create survey files."""
    if request.method == 'POST':
        data = request.json
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({'error': 'Name required'}), 400
        
        result = SurveyFile.create(
            current_app.config['DATABASE'],
            name=name,
            date=data.get('date'),
            place=data.get('place')
        )
        
        if not result:
            return jsonify({'error': 'File exists'}), 400
        
        return jsonify({'status': 'ok', 'file': result})
    
    files = SurveyFile.get_all(current_app.config['DATABASE'])
    return jsonify(files)


@api_bp.route('/files/upload', methods=['POST'])
def upload_file():
    """Upload and parse a DTF file."""
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB max
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    filename = file.filename
    if not re.match(r'^[\w\s\-\.]+\.DTF$', filename, re.IGNORECASE):
        return jsonify({'error': 'Invalid file type. Only DTF files allowed'}), 400
    
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    
    if size > MAX_FILE_SIZE:
        return jsonify({'error': 'File too large. Maximum 10MB allowed'}), 400
    
    if size < 50:
        return jsonify({'error': 'File is too small or corrupted'}), 400
    
    try:
        content = file.read()
        
        header_check = content[:15]
        if not header_check.decode('ascii', errors='ignore').replace(' ', '').isalnum():
            return jsonify({'error': 'Invalid DTF file format'}), 400
        
        points = parse_dtf_file(content)
        
        if not points:
            return jsonify({'error': 'No valid points found in file'}), 400
        
        base_name = os.path.splitext(filename)[0]
        safe_name = re.sub(r'[^\w\s\-]', '', base_name)[:50]
        
        if not safe_name:
            safe_name = 'uploaded_file'
        
        original_name = safe_name
        counter = 1
        while SurveyFile.get_by_name(current_app.config['DATABASE'], safe_name):
            safe_name = f"{original_name}_{counter}"
            counter += 1
        
        from datetime import datetime
        file_result = SurveyFile.create(
            current_app.config['DATABASE'],
            name=safe_name,
            date=datetime.now().strftime('%Y-%m-%d'),
            place='Uploaded'
        )
        
        if not file_result:
            return jsonify({'error': 'Failed to create file'}), 500
        
        point_count = SurveyPoint.save_batch(
            current_app.config['DATABASE'],
            safe_name,
            points
        )
        
        session['current_file'] = safe_name
        
        return jsonify({
            'status': 'ok',
            'file': file_result,
            'points_count': point_count,
            'filename': safe_name
        })
        
    except Exception as e:
        return jsonify({'error': 'Failed to parse file: ' + str(e)}), 500


def parse_dtf_file(content):
    """Parse DTF file format (Survey Data File)."""
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
    """Get MAS user guide content for modal display."""
    # Path to USER_GUIDE.md in parent folder
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
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
    if request.method == 'DELETE':
        SurveyFile.delete(current_app.config['DATABASE'], name)
        return jsonify({'status': 'ok'})
    
    file_info = SurveyFile.get_by_name(current_app.config['DATABASE'], name)
    if not file_info:
        return jsonify({'error': 'Not found'}), 404
    
    return jsonify(file_info)


@api_bp.route('/points', methods=['GET'])
def get_points():
    """Get points for current file."""
    filename = session.get('current_file')
    if not filename:
        return jsonify([])
    
    points = SurveyPoint.get_by_file(current_app.config['DATABASE'], filename)
    return jsonify(points)


@api_bp.route('/points', methods=['POST'])
def save_points():
    """Save points for current file."""
    filename = session.get('current_file')
    if not filename:
        return jsonify({'error': 'No file selected'}), 400
    
    data = request.json
    points = data.get('points', [])
    
    count = SurveyPoint.save_batch(
        current_app.config['DATABASE'],
        filename,
        points
    )
    
    return jsonify({'status': 'ok', 'count': count})


@api_bp.route('/calculate/area', methods=['POST'])
def calculate_area():
    """Calculate area from points."""
    from app.programs.mas.services.calculator import SurveyCalculator
    
    data = request.json
    points = data.get('points', [])
    
    if len(points) < 3:
        return jsonify({'error': 'Need at least 3 points'}), 400
    
    area = SurveyCalculator.calculate_area(points)
    
    return jsonify({
        'area': area,
        'formatted': f"{area:.2f} m²"
    })


@api_bp.route('/calculate/perimeter', methods=['POST'])
def calculate_perimeter():
    """Calculate perimeter from points."""
    from app.programs.mas.services.calculator import SurveyCalculator
    
    data = request.json
    points = data.get('points', [])
    
    perimeter = SurveyCalculator.calculate_perimeter(points)
    
    return jsonify({
        'perimeter': perimeter,
        'formatted': f"{perimeter:.2f} m"
    })


@api_bp.route('/calculate/polar', methods=['POST'])
def calculate_polar():
    """Calculate polar coordinates."""
    from app.programs.mas.services.calculator import SurveyCalculator
    
    data = request.json
    polar_type = data.get('type', 'DISTOMAT')
    station_no = data.get('station_no', 1)
    back_azimuth = data.get('back_azimuth', 0)
    observations = data.get('observations', [])
    
    filename = session.get('current_file')
    station_y, station_x = 0, 0
    
    if filename:
        points = SurveyPoint.get_by_file(current_app.config['DATABASE'], filename)
        for p in points:
            if p['no'] == station_no:
                station_y = p['y']
                station_x = p['x']
                break
    
    results = []
    for obs in observations:
        distance = obs.get('distance', 0)
        angle = obs.get('angle', 0)
        h = obs.get('h', 0)
        
        bearing = (back_azimuth + angle) % 400
        delta_y, delta_x = SurveyCalculator.polar_to_cartesian(distance, bearing)
        
        results.append({
            'no': obs.get('no'),
            'y': round(station_y + delta_y, 2),
            'x': round(station_x + delta_x, 2),
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
    """Calculate offsets from line to points - based on MASSAH06.BAS algorithm."""
    from app.programs.mas.services.calculator import SurveyCalculator
    
    data = request.json
    line_start_no = data.get('line_start_no', 0)
    line_end_no = data.get('line_end_no', 0)
    points_data = data.get('points', [])
    
    filename = session.get('current_file')
    if not filename:
        return jsonify({'error': 'No file selected'}), 400
    
    all_points = SurveyPoint.get_by_file(current_app.config['DATABASE'], filename)
    
    line_start = None
    line_end = None
    for p in all_points:
        if p['no'] == line_start_no:
            line_start = {'y': p['y'], 'x': p['x']}
        if p['no'] == line_end_no:
            line_end = {'y': p['y'], 'x': p['x']}
    
    if not line_start or not line_end:
        return jsonify({'error': 'Line start or end point not found'}), 400
    
    ya, xa = line_start['y'], line_start['x']
    yb, xb = line_end['y'], line_end['x']
    
    dy_line = yb - ya
    dx_line = xb - xa
    md = SurveyCalculator._sqrt(dy_line * dy_line + dx_line * dx_line)
    
    if md < 0.0001:
        return jsonify({'error': 'Line too short'}), 400
    
    fnxof_y = dy_line / md
    fnxof_x = dx_line / md
    
    results = []
    for p in points_data:
        da = p.get('offset_distance', 0)
        side = p.get('side', 'LEFT')
        db = da
        if side == 'RIGHT':
            db = -db
        
        point_y = ya + fnxof_y * db + fnxof_x * da
        point_x = xa + fnxof_x * db - fnxof_y * da
        
        results.append({
            'no': p.get('no'),
            'y': round(point_y, 2),
            'x': round(point_x, 2),
            'side': side
        })
    
    return jsonify({
        'status': 'ok',
        'results': results
    })


@api_bp.route('/calculate/intersection', methods=['POST'])
def calculate_intersection():
    """Calculate intersection of two lines or circles."""
    from app.programs.mas.services.calculator import SurveyCalculator
    
    data = request.json
    intersection_type = data.get('type', 'TWO_LINES')
    p1 = data.get('p1', {'y': 0, 'x': 0})
    p2 = data.get('p2', {'y': 0, 'x': 0})
    
    result = None
    
    if intersection_type == 'TWO_LINES' or intersection_type == 'BEARING_BEARING':
        bearing1 = data.get('bearing1', 0)
        bearing2 = data.get('bearing2', 100)
        result = SurveyCalculator.calculate_intersection_two_lines(p1, bearing1, p2, bearing2)
    
    elif intersection_type == 'TWO_DISTANCES':
        d1 = data.get('distance1', 100)
        d2 = data.get('distance2', 100)
        result = SurveyCalculator.calculate_intersection_two_distances(p1, d1, p2, d2)
    
    elif intersection_type == 'LINE_DISTANCE':
        bearing1 = data.get('bearing1', 0)
        distance2 = data.get('distance2', 100)
        result = SurveyCalculator.calculate_intersection_line_distance(p1, bearing1, p2, distance2)
    
    if result is None:
        return jsonify({'error': 'Lines are parallel or no intersection'}), 400
    
    if isinstance(result, tuple):
        return jsonify({
            'status': 'ok',
            'type': intersection_type,
            'point1': {'y': round(result[0]['y'], 3), 'x': round(result[0]['x'], 3)},
            'point2': {'y': round(result[1]['y'], 3), 'x': round(result[1]['x'], 3)}
        })
    
    return jsonify({
        'status': 'ok',
        'type': intersection_type,
        'point': {'y': round(result['y'], 3), 'x': round(result['x'], 3)}
    })


@api_bp.route('/calculate/implant', methods=['POST'])
def calculate_implant():
    """Calculate implantation point - based on polar to cartesian conversion."""
    from app.programs.mas.services.calculator import SurveyCalculator
    
    data = request.json
    base_point_no = data.get('base_point_no', 1)
    distance = data.get('distance', 0)
    bearing = data.get('bearing', 0)
    height = data.get('height', 0)
    
    filename = session.get('current_file')
    base_y, base_x, base_h = 0, 0, 0
    
    if filename:
        points = SurveyPoint.get_by_file(current_app.config['DATABASE'], filename)
        for p in points:
            if p['no'] == base_point_no:
                base_y = p['y']
                base_x = p['x']
                base_h = p.get('h', 0)
                break
    
    delta_y, delta_x = SurveyCalculator.polar_to_cartesian(distance, bearing)
    
    implant_point = {
        'y': round(base_y + delta_y, 3),
        'x': round(base_x + delta_x, 3),
        'h': height if height else base_h
    }
    
    return jsonify({
        'status': 'ok',
        'base': {'y': base_y, 'x': base_x, 'h': base_h},
        'implant': implant_point,
        'distance': distance,
        'bearing': bearing
    })


@api_bp.route('/calculate/circle', methods=['POST'])
def calculate_circle():
    """Circle calculations."""
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


@api_bp.route('/calculate/interpolation', methods=['POST'])
def calculate_interpolation():
    """Calculate interpolation at vertical intervals - based on MASSAH12.BAS."""
    from app.programs.mas.services.calculator import SurveyCalculator
    
    data = request.json
    vertical_interval = float(data.get('vertical_interval', 0.5))
    lines = data.get('lines', [])
    
    filename = session.get('current_file')
    if not filename:
        return jsonify({'error': 'No file selected'}), 400
    
    points_list = SurveyPoint.get_by_file(current_app.config['DATABASE'], filename)
    points_dict = {p['no']: {'y': p['y'], 'x': p['x'], 'h': p.get('h', 0)} for p in points_list}
    
    results = SurveyCalculator.interpolation(vertical_interval, lines, points_dict)
    
    return jsonify({
        'status': 'ok',
        'vertical_interval': vertical_interval,
        'results': results
    })


@api_bp.route('/calculate/resection', methods=['POST'])
def calculate_resection():
    """Calculate resection from 2-3 known points - based on MASSAH09.BAS."""
    from app.programs.mas.services.calculator import SurveyCalculator
    
    data = request.json
    resection_type = data.get('type', '2POINTS')
    
    filename = session.get('current_file')
    if not filename:
        return jsonify({'error': 'No file selected'}), 400
    
    points_list = SurveyPoint.get_by_file(current_app.config['DATABASE'], filename)
    points_dict = {p['no']: {'y': p['y'], 'x': p['x'], 'h': p.get('h', 0)} for p in points_list}
    
    if resection_type == '2POINTS':
        p1_no = data.get('p1', 1)
        p2_no = data.get('p2', 2)
        dist1 = data.get('dist1', 0)
        dist2 = data.get('dist2', 0)
        
        p1 = points_dict.get(p1_no, {'y': 0, 'x': 0})
        p2 = points_dict.get(p2_no, {'y': 0, 'x': 0})
        
        result = SurveyCalculator.resection_simple(p1, p2, dist1, dist2)
        
        if result is None:
            return jsonify({'error': 'Cannot calculate resection'}), 400
        
        return jsonify({
            'status': 'ok',
            'type': '2POINTS',
            'point1': {'y': round(result[0]['y'], 3), 'x': round(result[0]['x'], 3)},
            'point2': {'y': round(result[1]['y'], 3), 'x': round(result[1]['x'], 3)}
        })
    
    return jsonify({'error': 'Unknown resection type'}), 400


@api_bp.route('/print/coordinates', methods=['POST'])
def print_coordinates():
    """Print coordinates - single, group, or all."""
    filename = session.get('current_file')
    if not filename:
        return jsonify({'error': 'No file selected'}), 400
    
    data = request.json
    print_type = data.get('type', 'all')
    from_no = data.get('from_no', 1)
    to_no = data.get('to_no', 1)
    
    points = SurveyPoint.get_by_file(current_app.config['DATABASE'], filename)
    if not points:
        return jsonify({'error': 'No points found'}), 400
    
    file_info = SurveyFile.get_by_name(current_app.config['DATABASE'], filename)
    
    result = {
        'header': generate_print_header(file_info),
        'points': []
    }
    
    filtered_points = points
    if print_type == 'single':
        filtered_points = [p for p in points if p['no'] == from_no]
    elif print_type == 'group':
        filtered_points = [p for p in points if from_no <= p['no'] <= to_no]
    
    for p in filtered_points:
        result['points'].append({
            'no': p['no'],
            'y': p['y'],
            'x': p['x'],
            'h': p.get('h', 0)
        })
    
    return jsonify(result)


@api_bp.route('/print/freenumbers', methods=['POST'])
def print_free_numbers():
    """Print free numbers with coordinates."""
    filename = session.get('current_file')
    if not filename:
        return jsonify({'error': 'No file selected'}), 400
    
    data = request.json
    from_no = data.get('from_no', 1)
    to_no = data.get('to_no', 10)
    
    points = SurveyPoint.get_by_file(current_app.config['DATABASE'], filename)
    if not points:
        return jsonify({'error': 'No points found'}), 400
    
    file_info = SurveyFile.get_by_name(current_app.config['DATABASE'], filename)
    
    result = {
        'header': generate_print_header(file_info),
        'from_no': from_no,
        'to_no': to_no,
        'points': []
    }
    
    filtered_points = [p for p in points if from_no <= p['no'] <= to_no]
    
    for p in filtered_points:
        result['points'].append({
            'no': p['no'],
            'y': p['y'],
            'x': p['x'],
            'h': p.get('h', 0)
        })
    
    return jsonify(result)


@api_bp.route('/print/gridlimits', methods=['GET'])
def print_grid_limits():
    """Calculate and print grid limits."""
    filename = session.get('current_file')
    if not filename:
        return jsonify({'error': 'No file selected'}), 400
    
    points = SurveyPoint.get_by_file(current_app.config['DATABASE'], filename)
    if not points:
        return jsonify({'error': 'No points found'}), 400
    
    file_info = SurveyFile.get_by_name(current_app.config['DATABASE'], filename)
    
    min_y = min_x = float('inf')
    max_y = max_x = float('-inf')
    min_y_point = max_y_point = min_x_point = max_x_point = 1
    
    for p in points:
        if p['y'] < min_y:
            min_y = p['y']
            min_y_point = p['no']
        if p['y'] > max_y:
            max_y = p['y']
            max_y_point = p['no']
        if p['x'] < min_x:
            min_x = p['x']
            min_x_point = p['no']
        if p['x'] > max_x:
            max_x = p['x']
            max_x_point = p['no']
    
    result = {
        'header': generate_print_header(file_info),
        'grid': {
            'y_west': {'value': min_y, 'point': min_y_point},
            'y_east': {'value': max_y, 'point': max_y_point},
            'x_south': {'value': min_x, 'point': min_x_point},
            'x_north': {'value': max_x, 'point': max_x_point}
        }
    }
    
    return jsonify(result)


@api_bp.route('/print/draw', methods=['GET'])
def print_draw():
    """Draw all points on printer - requires heights."""
    filename = session.get('current_file')
    if not filename:
        return jsonify({'error': 'No file selected'}), 400
    
    points = SurveyPoint.get_by_file(current_app.config['DATABASE'], filename)
    if not points:
        return jsonify({'error': 'No points found'}), 400
    
    has_heights = any(p.get('h', 0) != 0 for p in points)
    if not has_heights:
        return jsonify({'error': 'no_heights', 'message': 'YOUR FILE DOES NOT INCLUDE HEIGHTS'}), 400
    
    file_info = SurveyFile.get_by_name(current_app.config['DATABASE'], filename)
    
    result = {
        'header': generate_print_header(file_info),
        'points': []
    }
    
    for p in points:
        result['points'].append({
            'no': p['no'],
            'y': p['y'],
            'x': p['x'],
            'h': p.get('h', 0)
        })
    
    return jsonify(result)


def generate_print_header(file_info):
    """Generate standard print header."""
    if file_info:
        return {
            'name': file_info.get('name', ''),
            'date': file_info.get('date', ''),
            'place': file_info.get('place', ''),
            'no_of_points': file_info.get('no_of_points', 0)
        }
    return {'name': '', 'date': '', 'place': '', 'no_of_points': 0}
