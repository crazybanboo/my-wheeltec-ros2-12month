import qwiic_vl53l1x
from qwiic_i2c.linux_i2c import LinuxI2C
import smbus2
import time

# --- 配置参数 ---
I2C_BUS = 0
TCA9548A_ADDR = 0x70
VL53L1X_ADDR = 0x29
CHANNELS = range(8)  # 0 到 7 号通道

# 初始化 I2C 总线 (用于控制 TCA9548A)
bus = smbus2.SMBus(I2C_BUS)

def select_tca_channel(channel):
    """切换 TCA9548A 的通道"""
    if channel < 0 or channel > 7:
        return
    bus.write_byte(TCA9548A_ADDR, 1 << channel)
    time.sleep(0.01)  # 短暂延迟确保切换稳定

def main():
    # 初始化传感器对象列表
    i2c_driver = LinuxI2C(I2C_BUS)
    sensors = []
    
    print("正在初始化 8 个通道上的 VL53L1X 传感器...")
    
    for ch in CHANNELS:
        select_tca_channel(ch)
        
        # 为每个通道创建一个传感器实例
        # 注意：虽然物理地址都是 0x29，但在逻辑上我们顺序初始化它们
        sensor = qwiic_vl53l1x.QwiicVL53L1X(address=VL53L1X_ADDR, i2c_driver=i2c_driver)
        
        if sensor.sensor_init():
            sensor.set_distance_mode(2)  # 设置为长距离模式 (1:短, 2:长)
            sensor.set_timing_budget_in_ms(50)
            sensor.set_inter_measurement_in_ms(60)
            sensor.start_ranging()
            sensors.append(sensor)
            print(f"通道 {ch} 初始化成功")
        else:
            sensors.append(None)
            print(f"通道 {ch} 初始化失败，请检查接线")

    print("\n开始轮询数据...\n")
    
    status_map = {0: "有效", 1: "弱信号", 2: "饱和", 4: "溢出", 7: "无效"}

    try:
        while True:
            dist_results = []
            stat_results = []
            
            for i, sensor in enumerate(sensors):
                if sensor is None:
                    dist_results.append("N/A")
                    stat_results.append("离线")
                    continue
                
                # 关键步骤：读取前必须切换通道
                select_tca_channel(i)
                
                # 等待并获取数据
                # 由于是轮询，如果上一次采样还没完成，可能需要等待
                retry = 0
                while sensor.check_for_data_ready() == 0 and retry < 10:
                    time.sleep(0.005)
                    retry += 1
                
                distance = sensor.get_distance()
                status = sensor.get_range_status()
                
                dist_results.append(f"{distance:4d}mm")
                stat_results.append(f"{status_map.get(status, str(status))}")
            
            # --- 按照要求的格式打印 ---
            # 形式：传感器0距离|传感器1距离... === 传感器0状态|传感器1状态...
            dist_str = " | ".join(dist_results)
            stat_str = " | ".join(stat_results)
            
            print(f"{dist_str} === {stat_str}")
            
            # 控制全局刷新频率
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n正在停止测距...")
        for i, sensor in enumerate(sensors):
            if sensor:
                select_tca_channel(i)
                sensor.stop_ranging()
        print("程序已退出。")

if __name__ == "__main__":
    main()