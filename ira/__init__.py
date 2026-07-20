# ira/__init__.py
#
# This package provides the top-level `ira` namespace.
#
# Historical note: a previous version of this file extended __path__ to include
# backend/ira/ and pre-registered backend.ira.* modules under the ira.* names in
# sys.modules.  That caused a RuntimeWarning when running `python -m ira.server`
# because Python's -m runner found "ira.server" already in sys.modules with a
# __spec__.name of "backend.ira.server" — a loader mismatch.
#
# The real submodules that belong to this package (actions, assistant) have their
# own files directly in ira/ and need no path-manipulation to be importable.
# backend.ira.server is imported under its own canonical name by the entry points
# that need it; it must NOT be aliased here.
