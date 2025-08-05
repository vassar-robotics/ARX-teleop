#!/bin/bash
# Run tank drive with dummy video driver for headless operation
export SDL_VIDEODRIVER=dummy
python tank_drive_canopen.py "$@"