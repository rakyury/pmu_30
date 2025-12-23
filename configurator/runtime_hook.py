"""
Runtime hook for PyInstaller
Ensures proper path handling for portable execution
"""

import os
import sys

# When running as frozen app, set working directory to app location
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    app_dir = os.path.dirname(sys.executable)
    os.chdir(app_dir)

    # Add internal paths for module resolution
    internal_path = os.path.join(app_dir, '_internal')
    if os.path.exists(internal_path):
        sys.path.insert(0, internal_path)
