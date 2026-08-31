"""
MAS - Surveying Computerized System
Entry point for running the application.
"""
from app import create_app

app = create_app('development')

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  MAS - Surveying Computerized System")
    print("  Web Application v1.0")
    print("  Alrafideen Surveying Office")
    print("=" * 60)
    print("\n  URL: http://localhost:5000\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
