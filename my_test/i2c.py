# TCA9548A驱动
import smbus2

bus = smbus2.SMBus(0) # 假设使用 I2C-1
TCA9548A_ADDR = 0x70

def select_channel(channel):
    if channel < 0 or channel > 7:
        return
    # 写入一个位，比如开启通道 3 就是 1 << 3
    bus.write_byte(TCA9548A_ADDR, 1 << channel)

# 开启第 2 号通道
select_channel(7)