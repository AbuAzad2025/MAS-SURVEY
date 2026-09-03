"""
MAS - Surveying Computerized System
Entry point for running the application.
"""
import sys

# Handle --help / --version BEFORE touching the DB so they work even
# when the database is unreachable (e.g. fresh CI without mas_survey yet).
if __name__ == '__main__':
    if '--help' in sys.argv or '-h' in sys.argv:
        print("Usage: python run.py [--help] [--version]")
        print("  Run without arguments to start the MAS web server.")
        sys.exit(0)
    if '--version' in sys.argv:
        print("MAS Web Application v1.0")
        sys.exit(0)

from app import create_app  # noqa: E402  -- intentional: after flag handling

app = create_app('development')

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  MAS - Surveying Computerized System")
    print("  Web Application v1.0")
    print("  Alrafideen Surveying Office")
    print("=" * 60)
    print("\n  URL: http://localhost:5000\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
