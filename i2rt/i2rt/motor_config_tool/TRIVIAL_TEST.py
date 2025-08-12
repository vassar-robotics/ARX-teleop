import numpy as np
from i2rt.robots.get_robot import get_yam_robot

robot = get_yam_robot("can1")
robot.command_joint_pos(np.zeros(7))
