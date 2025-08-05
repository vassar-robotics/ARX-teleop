from typing import List, Tuple, Union, Optional, Dict, Any
import numpy as np
import os
import sys


def quaternion_to_euler(quat: np.ndarray) -> Tuple[float, float, float]:
    """
    Convert quaternion to euler angles (roll, pitch, yaw)
    Args:
        quat: np.ndarray, length 4 array [w, x, y, z]
    Returns:
        roll, pitch, yaw: euler angles in radians
    """
    w, x, y, z = quat

    # Calculate roll (x-axis rotation)
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    roll = np.arctan2(sinr_cosp, cosr_cosp)

    # Calculate pitch (y-axis rotation)
    sinp = 2 * (w * y - z * x)
    if abs(sinp) >= 1:
        pitch = np.pi / 2 * np.sign(sinp)  # Use 90 degree limit
    else:
        pitch = np.arcsin(sinp)

    # Calculate yaw (z-axis rotation)
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = np.arctan2(siny_cosp, cosy_cosp)

    return roll, pitch, yaw


def euler_to_quaternion(roll: float, pitch: float, yaw: float) -> np.ndarray:
    """
    Convert euler angles (roll, pitch, yaw) to quaternion.
    
    Args:
        roll: rotation around x-axis (radians)
        pitch: rotation around y-axis (radians) 
        yaw: rotation around z-axis (radians)
    
    Returns:
        np.ndarray: length 4 quaternion array [w, x, y, z]
    """
    cy = np.cos(yaw * 0.5)
    sy = np.sin(yaw * 0.5)
    cp = np.cos(pitch * 0.5)
    sp = np.sin(pitch * 0.5)
    cr = np.cos(roll * 0.5)
    sr = np.sin(roll * 0.5)

    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy

    return np.array([w, x, y, z])


class ARXArm:
    """
    ARX R5 single robot arm controller.
    
    Args:
        config (Dict[str, Any]): Configuration dictionary for the robot arm
            - can_port (str): CAN interface port (e.g., "can0")
            - type (int): Robot type (0 for X5lite, 1 for R5)
            - num_joints (int): Number of joints (default: 7)
            - dt (float): Control frequency time step (default: 0.05)
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.num_joints = config.get("num_joints", 7)
        self.dt = config.get("dt", 0.05)

        # Import the C++ library
        try:
            import arx_r5_python as arx
        except ImportError:
            raise ImportError("Failed to import arx_r5_python. Make sure the library is built and accessible.")

        # Get URDF path based on robot type
        current_dir = os.path.dirname(os.path.abspath(__file__))
        robot_type = config.get("type", 0)
        if robot_type == 0:
            urdf_path = os.path.join(current_dir, "X5liteaa0.urdf")
        else:
            urdf_path = os.path.join(current_dir, "R5_master.urdf")

        # Initialize the arm interface
        can_port = config.get("can_port", "can0")
        
        # Suppress ARX library output (Chinese characters)
        import sys
        from contextlib import redirect_stdout, redirect_stderr
        with open(os.devnull, 'w') as devnull:
            with redirect_stdout(devnull), redirect_stderr(devnull):
                self.arm = arx.InterfacesPy(urdf_path, can_port, robot_type)
                self.arm.arx_x(500, 2000, 10)

    def go_home(self) -> bool:
        """
        Move the robot arm to a pre-defined home pose.
        
        Returns:
            bool: True if successful
        """
        self.arm.set_arm_status(1)
        return True

    def gravity_compensation(self) -> bool:
        """
        Enable gravity compensation mode.
        
        Returns:
            bool: True if successful
        """
        self.arm.set_arm_status(3)
        return True

    def protect_mode(self) -> bool:
        """
        Enable protect mode.
        
        Returns:
            bool: True if successful
        """
        self.arm.set_arm_status(2)
        return True

    def set_joint_positions(
        self,
        positions: Union[float, List[float], np.ndarray],
        **kwargs
    ) -> bool:
        """
        Move the arm to the given joint positions.
        
        Args:
            positions: Desired joint positions. Shape: (6,)
            **kwargs: Additional arguments
        """
        self.arm.set_joint_positions(positions)
        self.arm.set_arm_status(5)
        return True

    def set_ee_pose(
        self,
        pos: Optional[Union[List[float], np.ndarray]] = None,
        quat: Optional[Union[List[float], np.ndarray]] = None,
        **kwargs
    ) -> bool:
        """
        Move the end effector to the given pose.
        
        Args:
            pos: Desired position [x, y, z]. Shape: (3,)
            quat: Desired orientation (quaternion). Shape: (4,) [w, x, y, z]
            **kwargs: Additional arguments
        """
        pose = [pos[0], pos[1], pos[2], quat[0], quat[1], quat[2], quat[3]]
        self.arm.set_ee_pose(pose)
        self.arm.set_arm_status(4)
        return True

    def set_ee_pose_xyzrpy(
        self,
        xyzrpy: Optional[Union[List[float], np.ndarray]] = None,
        **kwargs
    ) -> bool:
        """
        Move the end effector to the given pose using XYZ + Roll/Pitch/Yaw.
        
        Args:
            xyzrpy: Desired position and orientation [x, y, z, roll, pitch, yaw]. Shape: (6,)
            **kwargs: Additional arguments
        """
        quat = euler_to_quaternion(xyzrpy[3], xyzrpy[4], xyzrpy[5])
        pose = [xyzrpy[0], xyzrpy[1], xyzrpy[2], quat[0], quat[1], quat[2], quat[3]]
        self.arm.set_ee_pose(pose)
        self.arm.set_arm_status(4)
        return True

    def set_catch_pos(self, pos: float):
        """
        Set gripper position.
        
        Args:
            pos: Gripper position (-1.0 to 1.0, negative = close, positive = open)
        """
        self.arm.set_catch(pos)

    def get_joint_positions(
        self, joint_names: Optional[Union[str, List[str]]] = None
    ) -> Union[float, List[float]]:
        """
        Get the current joint positions of the arm.
        
        Args:
            joint_names: Joint names (not used in current implementation)
            
        Returns:
            List of joint positions
        """
        return self.arm.get_joint_positions()

    def get_joint_velocities(
        self, joint_names: Optional[Union[str, List[str]]] = None
    ) -> Union[float, List[float]]:
        """
        Get the current joint velocities of the arm.
        
        Args:
            joint_names: Joint names (not used in current implementation)
            
        Returns:
            List of joint velocities
        """
        return self.arm.get_joint_velocities()

    def get_joint_currents(
        self, joint_names: Optional[Union[str, List[str]]] = None
    ) -> Union[float, List[float]]:
        """
        Get the current joint currents of the arm.
        
        Args:
            joint_names: Joint names (not used in current implementation)
            
        Returns:
            List of joint currents
        """
        return self.arm.get_joint_currents()

    def get_ee_pose(self) -> List[float]:
        """
        Get the current end effector pose of the arm.
        
        Returns:
            List containing [x, y, z, qw, qx, qy, qz]
        """
        return self.arm.get_ee_pose()

    def get_ee_pose_xyzrpy(self) -> np.ndarray:
        """
        Get the current end effector pose as XYZ + Roll/Pitch/Yaw.
        
        Returns:
            np.ndarray: [x, y, z, roll, pitch, yaw]
        """
        xyzwxyz = self.arm.get_ee_pose()
        
        # Extract quaternion [w, x, y, z]
        quat = np.array([xyzwxyz[3], xyzwxyz[4], xyzwxyz[5], xyzwxyz[6]])
        
        # Convert to euler angles
        roll, pitch, yaw = quaternion_to_euler(quat)
        
        # Return as [x, y, z, roll, pitch, yaw]
        return np.array([xyzwxyz[0], xyzwxyz[1], xyzwxyz[2], roll, pitch, yaw])

    def __del__(self):
        """Destructor for cleanup"""
        pass