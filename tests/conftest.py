import os
import sys

# Make the package importable as ``PlotKit`` when running the tests from a checkout.
_REPO_PARENT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _REPO_PARENT not in sys.path:
    sys.path.insert(0, _REPO_PARENT)
