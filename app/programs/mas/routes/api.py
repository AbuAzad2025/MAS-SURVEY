"""
API routes for MAS - tenant-scoped, PostgreSQL via SQLAlchemy.
"""
import os
import re
import struct
import math
from datetime import datetime
from flask import Blueprint, request, jsonify, session, current_app
from sqlalchemy import func

from app.services.calculator import CalculatorService, SurveyingError
from app.shared.models import db, SurveyFile, SurveyPoint, Settings
from app.shared.middleware import (
    login_required, get_current_user, get_current_tenant,
    get_plan_limits, tenant_block_reason,
)


api_bp = Blueprint('api', __name__)


# --- helpers -----------------------------------------------------------

def _error(message, status=400):
    return jsonify({'error': message}), status


def _ok(**kwargs):
    return jsonify({'status': 'ok', **kwargs})


def _current_file_id():
    """Return the SurveyFile id of the current working file (tenant-scoped)."""
    name = session.get('current_file')
    if not name:
        return None
    f = SurveyFile.query.filter_by(
        tenant_id=get_current_tenant().id, name=name
    ).first()
    return f.id if f else None


def _points_dict_for_file(file_id: int) -> dict:
    rows = SurveyPoint.query.filter_by(file_id=file_id).order_by(SurveyPoint.point_no).all()
    return {p.point_no: {'y': p.y or 0, 'x': p.x or 0, 'h': p.h or 0} for p in rows}


def _points_list_for_file(file_id: int) -> list:
    rows = SurveyPoint.query.filter_by(file_id=file_id).order_by(SurveyPoint.point_no).all()
    return [p.to_dict() for p in rows]


# --- current file ------------------------------------------------------

@api_bp.route('/set-file', methods=['POST'])
@login_required
def set_current_file():
    data = request.json or {}
    name = (data.get('filename') or '').strip()
    if not name:
        return _error('Filename required')
    f = SurveyFile.query.filter_by(tenant_id=get_current_tenant().id, name=name).first()
    if not f:
        return _error('File not found', 404)
    session['current_file'] = name
    return _ok(filename=name)


@api_bp.route('/current-file')
@login_required
def get_current_file():
    name = session.get('current_file')
    if not name:
        return jsonify({'file': None})
    f = SurveyFile.query.filter_by(tenant_id=get_current_tenant().id, name=name).first()
    return jsonify({'file': f.to_dict() if f else None})


# --- settings ----------------------------------------------------------

@api_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings_endpoint():
    tenant_id = get_current_tenant().id
    if request.method == 'POST':
        data = request.json or {}
        for key, value in data.items():
            Settings.set(tenant_id, key, value)
        session.pop('settings', None)
        return _ok()
    return jsonify(Settings.get_all(tenant_id))


# --- files -------------------------------------------------------------

@api_bp.route('/files', methods=['GET', 'POST'])
@login_required
def files_list():
    tenant = get_current_tenant()
    if tenant is None:
        return _error('No tenant found', 403)
    tenant_id = tenant.id
    if request.method == 'POST':
        reason = tenant_block_reason(tenant)
        if reason == 'suspended':
            return _error('Account suspended, contact platform owner', 403)
        if reason == 'expired':
            return _error('Subscription expired, please renew', 400)
        if reason == 'no_tenant':
            return _error('No tenant found', 403)
        try:
            limits = get_plan_limits(getattr(tenant, 'plan', 'free'))
            max_files = limits.get('max_files', 5)
        except Exception:
            max_files = 5
        if max_files is not None and max_files >= 0:
            try:
                files_count = SurveyFile.query.filter_by(
                    tenant_id=tenant.id).count()
            except Exception:
                files_count = 0
            if files_count >= max_files:
                return _error('Plan file limit reached', 400)
        data = request.json or {}
        name = (data.get('name') or '').strip()
        if not name:
            return _error('Name required')
        if SurveyFile.query.filter_by(tenant_id=tenant_id, name=name).first():
            return _error('File exists', 400)
        f = SurveyFile(tenant_id=tenant_id, name=name,
                       date=data.get('date'), place=data.get('place'))
        db.session.add(f)
        db.session.commit()
        session['current_file'] = name
        return _ok(file=f.to_dict())

    rows = SurveyFile.query.filter_by(tenant_id=tenant_id).order_by(
        SurveyFile.created_at.desc()
    ).all()
    return jsonify([r.to_dict() for r in rows])


@api_bp.route('/files/upload', methods=['POST'])
@login_required
def upload_file():
    tenant_id = get_current_tenant().id
    MAX_FILE_SIZE = 10 * 1024 * 1024

    if 'file' not in request.files:
        return _error('No file provided')
    file = request.files['file']
    if not file.filename:
        return _error('No file selected')

    filename = file.filename
    if not re.match(r'^[\w\s\-\.]+\.DTF$', filename, re.IGNORECASE):
        return _error('Invalid file type. Only DTF files allowed')

    file.seek(0, 2); size = file.tell(); file.seek(0)
    if size > MAX_FILE_SIZE:
        return _error('File too large. Maximum 10MB allowed')
    if size < 50:
        return _error('File is too small or corrupted')

    try:
        content = file.read()
        header_check = content[:15]
        if not header_check.decode('ascii', errors='ignore').replace(' ', '').isalnum():
            return _error('Invalid DTF file format')
        points = parse_dtf_file(content)
        if not points:
            return _error('No valid points found in file')

        base_name = os.path.splitext(filename)[0]
        safe_name = re.sub(r'[^\w\s\-]', '', base_name)[:50] or 'uploaded_file'
        original_name = safe_name
        counter = 1
        while SurveyFile.query.filter_by(tenant_id=tenant_id, name=safe_name).first():
            safe_name = f"{original_name}_{counter}"; counter += 1

        f = SurveyFile(tenant_id=tenant_id, name=safe_name,
                       date=datetime.now().strftime('%Y-%m-%d'),
                       place='Uploaded')
        db.session.add(f); db.session.flush()

        for p in points:
            db.session.add(SurveyPoint(
                tenant_id=tenant_id, file_id=f.id,
                point_no=p['no'], y=p['y'], x=p['x'], h=p['h']
            ))
        f.no_of_points = len(points)
        db.session.commit()
        session['current_file'] = safe_name
        return _ok(file=f.to_dict(), points_count=len(points), filename=safe_name)
    except Exception as e:
        db.session.rollback()
        return _error('Failed to parse file: ' + str(e), 500)


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
        points, i = [], 0
        while i + 24 <= len(binary_data):
            try:
                y = struct.unpack('<d', binary_data[i:i+8])[0]
                x = struct.unpack('<d', binary_data[i+8:i+16])[0]
                h = struct.unpack('<d', binary_data[i+16:i+24])[0]
                if (0 < abs(y) < 50_000_000 and
                    0 < abs(x) < 50_000_000 and
                    -1000 < h < 10000 and
                    not (abs(y) < 0.001 and abs(x) < 0.001 and abs(h) < 0.001)):
                    points.append({
                        'no': len(points) + 1,
                        'y': round(y, 3), 'x': round(x, 3), 'h': round(h, 3)
                    })
                i += 24
            except Exception:
                i += 24
        return points
    except Exception:
        return []


# --- guide -------------------------------------------------------------

@api_bp.route('/guide')
def get_guide():
    import os, re
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    guide_path = os.path.join(base_dir, 'USER_GUIDE.md')
    try:
        with open(guide_path, 'r', encoding='utf-8') as f:
            content = f.read()
        html = content
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        html = re.sub(r'\n\n+', r'<br><br>', html)
        html = re.sub(r'---', '<hr style="border:0;border-top:1px solid #004400;margin:15px 0;">', html)
        return html
    except Exception as e:
        return f'<p style="color:red;">Error loading guide: {str(e)}</p>'


# --- file detail -------------------------------------------------------

@api_bp.route('/files/<name>', methods=['GET', 'DELETE'])
@login_required
def file_detail(name):
    tenant_id = get_current_tenant().id
    f = SurveyFile.query.filter_by(tenant_id=tenant_id, name=name).first()
    if not f:
        return _error('File not found', 404)
    if request.method == 'DELETE':
        db.session.delete(f); db.session.commit()
        if session.get('current_file') == name:
            session.pop('current_file', None)
        return _ok()
    return jsonify(f.to_dict())


# --- points ------------------------------------------------------------

@api_bp.route('/points', methods=['GET'])
@login_required
def get_points():
    fid = _current_file_id()
    if not fid:
        return jsonify([])
    return jsonify(_points_list_for_file(fid))


@api_bp.route('/points', methods=['POST'])
@login_required
def save_points():
    tenant = get_current_tenant()
    if tenant is None:
        return _error('No tenant found', 403)
    tenant_id = tenant.id
    reason = tenant_block_reason(tenant)
    if reason == 'suspended':
        return _error('Account suspended, contact platform owner', 403)
    if reason == 'no_tenant':
        return _error('No tenant found', 403)
    fid = _current_file_id()
    if not fid:
        return _error('No file selected')
    data = request.json or {}
    new_points = data.get('points', [])

    f = SurveyFile.query.get(fid)
    if not f:
        return _error('No file selected')

    # Plan points cap: total_after = existing count + new unique point_nos
    # not already present. -1 (or negative) means unlimited.
    try:
        limits = get_plan_limits(getattr(tenant, 'plan', 'free'))
        max_points = limits.get('max_points', 500)
    except Exception:
        max_points = 500
    if max_points is not None and max_points >= 0:
        try:
            existing_count = SurveyPoint.query.filter_by(file_id=fid).count()
        except Exception:
            existing_count = 0
        try:
            existing_rows = SurveyPoint.query.filter_by(
                file_id=fid).with_entities(SurveyPoint.point_no).all()
            existing_nos = {r[0] for r in existing_rows}
        except Exception:
            existing_nos = set()
        incoming_nos = set()
        for p in new_points:
            try:
                no = p.get('no') if p.get('no') is not None else p.get('point_no')
            except Exception:
                continue
            if no is None:
                continue
            incoming_nos.add(no)
        new_unique = len(incoming_nos - existing_nos)
        total_after = existing_count + new_unique
        if total_after > max_points:
            return _error('Plan points limit reached', 400)

    # Append/upsert strategy (back-compat): insert new numbers, update existing.
    for p in new_points:
        no = p.get('no') if p.get('no') is not None else p.get('point_no')
        if no is None:
            continue
        existing = SurveyPoint.query.filter_by(file_id=fid, point_no=no).first()
        if existing:
            existing.y = p.get('y', 0)
            existing.x = p.get('x', 0)
            existing.h = p.get('h', 0)
            existing.code = p.get('code', '')
        else:
            db.session.add(SurveyPoint(
                tenant_id=tenant_id, file_id=fid, point_no=no,
                y=p.get('y', 0), x=p.get('x', 0), h=p.get('h', 0),
                code=p.get('code', ''),
            ))
    db.session.flush()
    f.no_of_points = SurveyPoint.query.filter_by(file_id=fid).count()
    db.session.commit()
    return _ok(count=len(new_points))


# --- calculations ------------------------------------------------------

@api_bp.route('/calculate/area', methods=['POST'])
def calculate_area():
    data = request.json or {}
    points = data.get('points', [])
    if len(points) < 3:
        return _error('Need at least 3 points')
    try:
        area = CalculatorService.calculate_area(points)
        perimeter = CalculatorService.calculate_perimeter(points)
        return jsonify({'area': round(area, 3),
                        'perimeter': round(perimeter, 3),
                        'formatted': f"{area:.2f} m²"})
    except SurveyingError as e:
        return _error(str(e))


@api_bp.route('/calculate/perimeter', methods=['POST'])
def calculate_perimeter():
    data = request.json or {}
    points = data.get('points', [])
    try:
        perimeter = CalculatorService.calculate_perimeter(points)
        return jsonify({'perimeter': round(perimeter, 3),
                        'formatted': f"{perimeter:.2f} m"})
    except SurveyingError as e:
        return _error(str(e))


@api_bp.route('/calculate/polar', methods=['POST'])
def calculate_polar():
    data = request.json or {}
    polar_type = data.get('type', 'DISTOMAT')
    back_azimuth = data.get('back_azimuth', 0)
    observations = data.get('observations', [])
    results = []
    for obs in observations:
        distance = obs.get('distance', 0)
        angle = obs.get('angle', 0)
        h = obs.get('h', 0)
        bearing = (back_azimuth + angle) % 400
        delta_y, delta_x = CalculatorService.polar_to_cartesian(distance, bearing)
        results.append({'no': obs.get('no'),
                        'y': round(delta_y, 3), 'x': round(delta_x, 3),
                        'h': h, 'bearing': round(bearing, 4)})
    return jsonify({'status': 'ok', 'type': polar_type, 'results': results})


@api_bp.route('/calculate/offsets', methods=['POST'])
def calculate_offsets():
    data = request.json or {}
    line_start = data.get('line_start', {'y': 0, 'x': 0})
    line_end = data.get('line_end', {'y': 100, 'x': 100})
    points = data.get('points', [])
    results = []
    for p in points:
        offset_dist = p.get('offset_distance', 0)
        side = p.get('side', 'LEFT')
        try:
            r = CalculatorService.calculate_offset_point(line_start, line_end, offset_dist, side)
            results.append({'no': p.get('no'),
                            'y': round(r['y'], 3), 'x': round(r['x'], 3),
                            'side': side})
        except SurveyingError as e:
            results.append({'no': p.get('no'), 'error': str(e), 'side': side})
    return jsonify({'status': 'ok', 'results': results})


@api_bp.route('/calculate/intersection', methods=['POST'])
def calculate_intersection():
    data = request.json or {}
    intersection_type = data.get('type', 'TWO_LINES')
    p1 = data.get('p1', {'y': 0, 'x': 0})
    p2 = data.get('p2', {'y': 0, 'x': 0})
    try:
        if intersection_type in ('TWO_LINES', 'BEARING_BEARING'):
            b1 = data.get('bearing1', 0); b2 = data.get('bearing2', 100)
            r = CalculatorService.intersection_two_lines(p1, b1, p2, b2)
            if r is None: return _error('Lines are parallel or nearly parallel')
            return jsonify({'status': 'ok', 'type': intersection_type,
                            'point': {'y': round(r['y'], 3), 'x': round(r['x'], 3)}})
        elif intersection_type == 'TWO_DISTANCES':
            d1 = data.get('distance1', 100); d2 = data.get('distance2', 100)
            r = CalculatorService.intersection_two_distances(p1, d1, p2, d2)
            if r is None: return _error('Circles do not intersect')
            return jsonify({'status': 'ok', 'type': intersection_type,
                            'point1': {'y': round(r[0]['y'], 3), 'x': round(r[0]['x'], 3)},
                            'point2': {'y': round(r[1]['y'], 3), 'x': round(r[1]['x'], 3)}})
        elif intersection_type == 'LINE_DISTANCE':
            b1 = data.get('bearing1', 0); d2 = data.get('distance2', 100)
            r = CalculatorService.intersection_line_distance(p1, b1, p2, d2)
            if r is None: return _error('Line and circle do not intersect')
            return jsonify({'status': 'ok', 'type': intersection_type,
                            'point1': {'y': round(r[0]['y'], 3), 'x': round(r[0]['x'], 3)},
                            'point2': {'y': round(r[1]['y'], 3), 'x': round(r[1]['x'], 3)}})
        return _error('Unknown intersection type')
    except SurveyingError as e:
        return _error(str(e))


@api_bp.route('/calculate/implant', methods=['POST'])
def calculate_implant():
    data = request.json or {}
    base = data.get('base_point', {'y': 0, 'x': 0, 'h': 0})
    distance = data.get('distance', 0)
    bearing = data.get('bearing', 0)
    height = data.get('height', 0)
    delta_y, delta_x = CalculatorService.polar_to_cartesian(distance, bearing)
    implant_point = {'y': round(base['y'] + delta_y, 3),
                     'x': round(base['x'] + delta_x, 3),
                     'h': height if height else base.get('h', 0)}
    return jsonify({'status': 'ok', 'base': base, 'implant': implant_point,
                    'distance': distance, 'bearing': bearing})


@api_bp.route('/calculate/circle', methods=['POST'])
def calculate_circle():
    data = request.json or {}
    calc_type = data.get('type', 'AREA')
    v1 = data.get('value1', 0); v2 = data.get('value2', 0)
    result = 0; result_unit = ''
    if calc_type == 'ARC':
        result = (v1 / 200) * math.pi * v2; result_unit = 'm'
    elif calc_type == 'CIRCUMFERENCE':
        result = 2 * math.pi * v1; result_unit = 'm'
    elif calc_type == 'AREA':
        result = math.pi * v1 * v1; result_unit = 'm²'
    elif calc_type == 'CENTER':
        p1 = data.get('p1', {'y': 0, 'x': 0})
        p2 = data.get('p2', {'y': 0, 'x': 0})
        p3 = data.get('p3', {'y': 0, 'x': 0})
        c = CalculatorService.circle_center_3points(p1, p2, p3)
        if c is None: return _error('Points are collinear - cannot calculate circle center')
        return jsonify({'status': 'ok', 'type': calc_type,
                        'center': {'y': round(c['y'], 3), 'x': round(c['x'], 3)},
                        'radius': round(c['radius'], 3)})
    elif calc_type == 'RADIUS':
        result = math.sqrt(v1 / math.pi) if v2 > 0 else v1 / (2 * math.pi); result_unit = 'm'
    elif calc_type == 'CHORD':
        result = 2 * v1 * math.sin((v2 * math.pi / 200) / 2); result_unit = 'm'
    return jsonify({'status': 'ok', 'type': calc_type,
                    'result': round(result, 3), 'unit': result_unit})


@api_bp.route('/calculate/resection', methods=['POST'])
def calculate_resection():
    data = request.json or {}
    resection_type = data.get('type', '3POINTS')
    try:
        if resection_type == '3POINTS':
            station = CalculatorService.resection_3point(
                data.get('p1', {'y': 0, 'x': 0}), data.get('angle1', 0),
                data.get('p2', {'y': 0, 'x': 0}), data.get('angle2', 0),
                data.get('p3', {'y': 0, 'x': 0}), data.get('angle3', 0),
            )
            if station is None: return _error('Resection calculation failed - check angles')
            return jsonify({'status': 'ok', 'type': '3POINTS',
                            'point': {'y': round(station['y'], 3), 'x': round(station['x'], 3)}})
        elif resection_type == '2POINTS':
            r = CalculatorService.resection_2point(
                data.get('p1', {'y': 0, 'x': 0}), data.get('dist1', 0),
                data.get('p2', {'y': 0, 'x': 0}), data.get('dist2', 0),
            )
            if r is None: return _error('2-point resection failed - check distances')
            return jsonify({'status': 'ok', 'type': '2POINTS',
                            'point1': {'y': round(r[0]['y'], 3), 'x': round(r[0]['x'], 3)},
                            'point2': {'y': round(r[1]['y'], 3), 'x': round(r[1]['x'], 3)}})
        return _error('Unknown resection type')
    except SurveyingError as e:
        return _error(str(e))


@api_bp.route('/calculate/interpolation', methods=['POST'])
@login_required
def calculate_interpolation():
    data = request.json or {}
    vertical_interval = data.get('vertical_interval', 0.5)
    lines = data.get('lines', [])
    if vertical_interval <= 0:
        return _error('Vertical interval must be positive')
    if not lines:
        return _error('No lines specified')
    fid = _current_file_id()
    if not fid:
        return _error('No file selected')
    try:
        points_dict = _points_dict_for_file(fid)
        results = CalculatorService.interpolate_points(points_dict, lines, vertical_interval)
        return jsonify({'status': 'ok', 'vertical_interval': vertical_interval, 'results': results})
    except SurveyingError as e:
        return _error(str(e))
    except Exception as e:
        return _error('Interpolation failed: ' + str(e))


@api_bp.route('/calculate/traverse', methods=['POST'])
def calculate_traverse():
    data = request.json or {}
    points = data.get('points', [])
    known_start = data.get('known_start')
    known_end = data.get('known_end')
    if len(points) < 2:
        return _error('Need at least 2 points for traverse')
    try:
        tps = []
        for p in points:
            az = p.get('azimuth', 0); dist = p.get('distance', 0)
            dy, dx = CalculatorService.polar_to_cartesian(dist, az)
            tps.append({'no': p.get('no'),
                        'y': p.get('y', 0), 'x': p.get('x', 0), 'h': p.get('h', 0),
                        'delta_y': dy, 'delta_x': dx, 'distance': dist})
        result = CalculatorService.bowditch_traverse(tps, known_start, known_end)
        return jsonify({'status': 'ok',
                        'total_distance': result.total_distance,
                        'closure_error_y': result.closure_error_y,
                        'closure_error_x': result.closure_error_x,
                        'linear_misclosure': result.linear_misclosure,
                        'precision_ratio': result.precision_ratio,
                        'adjusted_points': result.adjusted_points})
    except SurveyingError as e:
        return _error(str(e))


@api_bp.route('/calculate/freenumbers', methods=['POST'])
@login_required
def calculate_freenumbers():
    data = request.json or {}
    from_no = data.get('from_no', 1)
    to_no = data.get('to_no', 9999)
    fid = _current_file_id()
    if not fid:
        return _error('No file selected')
    try:
        all_points = _points_list_for_file(fid)
        free_points = CalculatorService.get_free_numbers(all_points, from_no, to_no)
        return jsonify({'status': 'ok', 'points': free_points, 'count': len(free_points)})
    except SurveyingError as e:
        return _error(str(e))


# --- print endpoints ---------------------------------------------------

@api_bp.route('/print/coordinates', methods=['POST'])
@login_required
def print_coordinates():
    data = request.json or {}
    print_type = data.get('type', 'all')
    from_no = data.get('from_no', 1)
    to_no = data.get('to_no', 9999)
    fid = _current_file_id()
    if not fid:
        return _error('No file selected')
    all_points = _points_list_for_file(fid)
    f = SurveyFile.query.get(fid)
    if print_type == 'single':
        filtered = [p for p in all_points if p.get('no') == from_no]
    elif print_type == 'group':
        filtered = [p for p in all_points if from_no <= p.get('no', 0) <= to_no]
    else:
        filtered = all_points
    return jsonify({'points': filtered, 'header': f.to_dict() if f else None})


@api_bp.route('/print/freenumbers', methods=['POST'])
@login_required
def print_freenumbers():
    data = request.json or {}
    from_no = data.get('from_no', 1)
    to_no = data.get('to_no', 9999)
    fid = _current_file_id()
    if not fid:
        return _error('No file selected')
    all_points = _points_list_for_file(fid)
    free_points = CalculatorService.get_free_numbers(all_points, from_no, to_no)
    f = SurveyFile.query.get(fid)
    return jsonify({'points': free_points, 'header': f.to_dict() if f else None})


@api_bp.route('/print/gridlimits', methods=['GET'])
@login_required
def print_gridlimits():
    fid = _current_file_id()
    if not fid:
        return _error('No file selected')
    points = _points_list_for_file(fid)
    f = SurveyFile.query.get(fid)
    if not points:
        return _error('No points in file')
    ys = [p.get('y', 0) for p in points]
    xs = [p.get('x', 0) for p in points]
    return jsonify({
        'grid': {
            'y_west': {'value': min(ys)}, 'y_east': {'value': max(ys)},
            'x_south': {'value': min(xs)}, 'x_north': {'value': max(xs)},
        },
        'header': f.to_dict() if f else None,
    })


@api_bp.route('/print/draw', methods=['GET'])
@login_required
def print_draw():
    fid = _current_file_id()
    if not fid:
        return _error('No file selected')
    points = _points_list_for_file(fid)
    f = SurveyFile.query.get(fid)
    has_heights = any(p.get('h', 0) != 0 for p in points)
    if not has_heights:
        return jsonify({'error': 'no_heights'})
    return jsonify({'points': points, 'header': f.to_dict() if f else None})
