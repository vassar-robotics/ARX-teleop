"""
ARX Control Module

Simple interface for controlling ARX R5 robotic arms.
"""

import os
import sys

# Add the library paths to ensure the compiled libraries can be found
current_dir = os.path.dirname(os.path.abspath(__file__))

# Updated paths for reorganized structure
lib_paths = [
    os.path.join(current_dir, "lib"),
    os.path.join(current_dir, "lib/arx_r5_src"),
    os.path.join(current_dir, "lib/arx_r5_python"),
]

for path in lib_paths:
    if os.path.exists(path):
        sys.path.insert(0, path)

# Import the main classes
from .single_arm import SingleArm

__all__ = ['SingleArm']