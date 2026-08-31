"""
Test fixtures package.
"""
from pathlib import Path


def get_fixture_path(fixture_name: str) -> Path:
    """Get path to a test fixture.
    
    Args:
        fixture_name: Name of the fixture file
        
    Returns:
        Path to the fixture file
    """
    return Path(__file__).parent / fixture_name
