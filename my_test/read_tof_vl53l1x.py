import qwiic_vl53l1x
from qwiic_i2c.linux_i2c import LinuxI2C
import time
import sys

def main():
    """
    使用 SparkFun Qwiic VL53L1X 库读取激光测距传感器数据的示例
    """
    print("正在初始化 VL53L1X 传感器 (I2C Bus 0)...")
    
    try:
        # 显式指定 I2C 总线 0
        i2c_driver = LinuxI2C(0)
        sensor = qwiic_vl53l1x.QwiicVL53L1X(address=0x29, i2c_driver=i2c_driver)
        
        # 检查传感器 ID
        sensor_id = sensor.get_sensor_id()
        if sensor_id == 0:
            print("未检测到传感器，请检查 I2C 总线和地址 (当前 Bus 0, Address 0x29)。")
            return
            
        print(f"检测到传感器，ID: {hex(sensor_id)}")
        
        # 初始化传感器
        sensor.sensor_init()
        
        # 设置距离模式
        # 1 = Short (最高约 1.3米)
        # 2 = Long (最高约 4米，受环境光影响)
        sensor.set_distance_mode(1)
        
        print("开始测距 (按 Ctrl+C 退出)...")
        
        # 开始连续测距
        sensor.start_ranging()
        
        while True:
            # 等待数据就绪
            while sensor.check_for_data_ready() == 0:
                time.sleep(0.01)
            
            # 读取距离，单位为毫米 (mm)
            distance = sensor.get_distance()
            
            # 清除中断以便下一次测量
            sensor.clear_interrupt()
            
            print(f"当前距离: {distance} mm")
            
            # 控制打印频率
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n检测到 Ctrl+C，程序退出。")
    except Exception as e:
        print(f"\n运行时发生错误: {e}")
    finally:
        if 'sensor' in locals():
            sensor.stop_ranging()
            print("已停止测距。")

if __name__ == "__main__":
    main()
