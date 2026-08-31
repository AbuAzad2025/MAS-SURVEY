"""
Sample DTF file fixture for testing.
"""
import struct
from pathlib import Path


def create_sample_dtf(output_path: Path, num_points: int = 4):
    """Create a sample DTF file for testing.
    
    Args:
        output_path: Path where the DTF file will be saved
        num_points: Number of sample points to include
    """
    header = b'SAMPLE          '
    marker = b'\xDC\x05\x00\x00'
    date_str = b'31-8-2026     '
    
    # Sample points data
    points = [
        (1000.0, 2000.0, 50.0),
        (1100.0, 2000.0, 55.0),
        (1100.0, 2100.0, 60.0),
        (1000.0, 2100.0, 58.0),
        (1050.0, 2050.0, 52.5),
    ]
    
    data = b''
    for i in range(min(num_points, len(points))):
        y, x, h = points[i]
        data += struct.pack('<d', y)
        data += struct.pack('<d', x)
        data += struct.pack('<d', h)
    
    content = header + marker + date_str + header + data
    
    output_path.write_bytes(content)
    return output_path


def create_large_dtf(output_path: Path, num_points: int = 100):
    """Create a large DTF file for performance testing.
    
    Args:
        output_path: Path where the DTF file will be saved
        num_points: Number of sample points to include
    """
    header = b'LARGEFILE       '
    marker = b'\xDC\x05\x00\x00'
    date_str = b'31-8-2026     '
    
    data = b''
    for i in range(num_points):
        y = 1000.0 + i * 10
        x = 2000.0 + i * 5
        h = 50.0 + i * 0.5
        data += struct.pack('<d', y)
        data += struct.pack('<d', x)
        data += struct.pack('<d', h)
    
    content = header + marker + date_str + header + data
    
    output_path.write_bytes(content)
    return output_path
