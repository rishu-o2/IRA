import pathlib, sys

# Add the backend/ira directory to this package's __path__
backend_path = pathlib.Path(__file__).resolve().parent.parent / "backend" / "ira"
if backend_path.is_dir():
    __path__.append(str(backend_path))
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
        # Alias backend submodules to top-level ira package for consistent imports
        import importlib, pkgutil, pathlib, sys as _sys
        _backend_pkg = 'backend.ira'
        _backend_path = pathlib.Path(__file__).resolve().parent.parent / 'backend' / 'ira'
        for _, _modname, _ispkg in pkgutil.iter_modules([str(_backend_path)]):
            try:
                _full_name = f"{_backend_pkg}.{_modname}"
                _module = importlib.import_module(_full_name)
                _sys.modules[f"ira.{_modname}"] = _module
                setattr(_sys.modules[__name__], _modname, _module)  # expose as attribute
            except Exception:
                pass
        # Ensure essential submodules are importable as attributes
        import importlib as _il
        _il.import_module('.actions', __name__)
        _il.import_module('.assistant', __name__)
        sys.path.insert(0, str(backend_path))
        # Explicitly expose key submodules
        from . import actions, assistant  # noqa: F401

else:
    raise RuntimeError(f"Expected backend path not found: {backend_path}")
