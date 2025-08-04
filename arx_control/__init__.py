"""
ARX Control Module

Simple interface for controlling ARX R5 robotic arms.
"""

import os
import sys

# Add the library paths to ensure the compiled libraries can be found
current_dir = os.path.dirname(os.path.abspath(__file__))

# Add potential library paths (you may need to adjust these based on your setup)
lib_paths = [
    os.path.join(current_dir, "../arx_local_control_example/ARX_R5_python/bimanual/lib"),
    os.path.join(current_dir, "../arx_local_control_example/ARX_R5_python/bimanual/lib/arx_r5_src"),
    os.path.join(current_dir, "../arx_local_control_example/ARX_R5_python/bimanual/api"),
    os.path.join(current_dir, "../arx_local_control_example/ARX_R5_python/bimanual/api/arx_r5_python"),
]

for path in lib_paths:
    if os.path.exists(path):
        sys.path.insert(0, path)

# Import the main classes
from .single_arm import SingleArm

__all__ = ['SingleArm']