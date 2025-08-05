#!/usr/bin/env python3
"""
Simple servo controller for SO101 robots with Feetech STS3215 motors.
Extracted from the bloated multi-arms standalone file for simplicity.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class SO101Controller:
    """Controller for SO101 robot with Feetech STS3215 motors."""
    
    # Feetech register addresses
    TORQUE_ENABLE = 40
    PRESENT_POSITION = 56
    GOAL_POSITION = 42
    PRESENT_VOLTAGE = 62
    LOCK = 55
    
    def __init__(self, port: str, motor_ids: List[int], baudrate: int = 1000000, robot_id: str = ""):
        self.port = port
        self.motor_ids = motor_ids
        self.baudrate = baudrate
        self.robot_id = robot_id  # For identification (e.g., "Leader1", "Follower1")
        self.connected = False
        self.resolution = 4096  # STS3215 has 4096 resolution (0-4095)
        
        try:
            import scservo_sdk as scs  # type: ignore
            self.scs = scs
        except ImportError:
            raise RuntimeError("scservo_sdk not installed. Please install from Feetech SDK")
            
        self.port_handler: Any = None
        self.packet_handler: Any = None
        
    def connect(self) -> None:
        """Connect to the robot."""
        self.port_handler = self.scs.PortHandler(self.port)
        self.packet_handler = self.scs.PacketHandler(0)  # Protocol 0
        
        if not self.port_handler.openPort():
            raise RuntimeError(f"Failed to open port '{self.port}'")
            
        if not self.port_handler.setBaudRate(self.baudrate):
            raise RuntimeError(f"Failed to set baudrate to {self.baudrate}")
            
        # Test connection by pinging motors
        for motor_id in self.motor_ids:
            try:
                ping_result = self.packet_handler.ping(self.port_handler, motor_id)
                # Handle different return formats from Feetech SDK
                if isinstance(ping_result, tuple) and len(ping_result) >= 2:
                    if len(ping_result) >= 3:
                        model_number, result, error = ping_result[:3]
                    else:
                        model_number, result = ping_result[:2]
                    
                    if result != self.scs.COMM_SUCCESS:
                        raise RuntimeError(f"Failed to ping motor {motor_id}: {self.packet_handler.getTxRxResult(result)}")
                else:
                    raise RuntimeError(f"Unexpected ping result: {ping_result}")
            except Exception as e:
                raise RuntimeError(f"Failed to ping motor {motor_id}: {str(e)}")
                
        self.connected = True
        logger.info(f"Connected to {self.robot_id} at {self.port}")
        
    def disconnect(self) -> None:
        """Disconnect from the robot."""
        if self.port_handler:
            self.port_handler.closePort()
        self.connected = False
        
    def read_positions(self) -> Dict[int, int]:
        """Read current positions from all motors."""
        positions = {}
        for motor_id in self.motor_ids:
            try:
                read_result = self.packet_handler.read2ByteTxRx(
                    self.port_handler, motor_id, self.PRESENT_POSITION)
                
                # Handle different return formats
                if len(read_result) >= 3:
                    position, result, error = read_result
                elif len(read_result) == 2:
                    position, result = read_result
                    error = 0
                else:
                    logger.warning(f"Unexpected read result format from motor {motor_id} on {self.robot_id}: {read_result}")
                    continue
                    
                if result == self.scs.COMM_SUCCESS:
                    positions[motor_id] = position
                else:
                    logger.warning(f"Failed to read position from motor {motor_id} on {self.robot_id}")
            except Exception as e:
                logger.warning(f"Exception reading position from motor {motor_id} on {self.robot_id}: {e}")
        return positions