
# BRING down left arm
sudo ip link set can1 down

# BRING UP left arm
sudo ip link set can1 up type can bitrate 1000000

# RUN I2RT
python3 i2rt/test_i2rt_via_keyboard.py