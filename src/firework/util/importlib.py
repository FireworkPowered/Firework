import sys

if sys.version_info <= (3, 9):
    import importlib.resources as pkg_resources  # noqa: F401
elif (3, 10) <= sys.version_info <= (3, 11):
    import importlib_resources as pkg_resources  # noqa: F401
else:
    import importlib.resources as pkg_resources  # noqa: F401
