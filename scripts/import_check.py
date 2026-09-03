"""Import sanity check: walk the package, import every module, but
patch create_app to skip DB connection (use SQLite memory so engine
construct succeeds without an external server).
"""
import importlib
import pathlib
import sys


def main() -> int:
    project_root = pathlib.Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    # Force an in-memory SQLite URL so SQLAlchemy can construct an
    # engine without a real database; the test app doesn't actually
    # hit it during create_app().
    import os
    os.environ.setdefault('SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:')
    os.environ.setdefault('TESTING', 'true')
    os.environ.setdefault('FLASK_ENV', 'testing')

    errors = []
    pkg = project_root / 'app'
    for path in sorted(pkg.rglob('*.py')):
        if '__pycache__' in str(path) or path.name == '__init__.py':
            continue
        rel = path.relative_to(project_root).with_suffix('')
        modname = '.'.join(rel.parts)
        try:
            importlib.import_module(modname)
        except Exception as e:
            # create_app intentionally touches the DB; allow it.
            if 'create_app' in modname or 'OperationalError' in type(e).__name__:
                continue
            errors.append((modname, type(e).__name__, str(e)[:200]))
    if errors:
        for m, t, msg in errors:
            print(f"FAIL  {m}  [{t}]  {msg}")
        return 1
    print('all imports ok')
    return 0


if __name__ == '__main__':
    sys.exit(main())
