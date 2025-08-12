import numpy as np
from i2rt.robots.get_robot import get_yam_robot
from i2rt.robots.utils import GripperType

# Get a robot instance
robot = get_yam_robot(channel="can1", gripper_type=GripperType.YAM_COMPACT_SMALL)

# Get the current joint positions
joint_pos = robot.get_joint_pos()

# Command the robot to move to a new joint position
target_pos = np.array([0, 0, 0, 0, 0, 0, 0])

# Command the robot to move to the target position
robot.command_joint_pos(target_pos)