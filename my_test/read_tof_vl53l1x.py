import qwiic_vl53l1x
from qwiic_i2c.linux_i2c import LinuxI2C
import time
import sys

def main():
    """
    带诊断信息的 VL53L1X 测距脚本，用于分析数值异常问题
    """
    print("正在初始化 VL53L1X 传感器 (I2C Bus 0)...")
    
    try:
        i2c_driver = LinuxI2C(0)
        sensor = qwiic_vl53l1x.QwiicVL53L1X(address=0x29, i2c_driver=i2c_driver)
        
        sensor_id = sensor.get_sensor_id()
        if sensor_id == 0:
            print("未检测到传感器。")
            return
            
        print(f"检测到传感器，ID: {hex(sensor_id)}")
        sensor.sensor_init()
        
        # 模式 1 = Short Range (短距离模式)
        # 如果需要测更远，可以改为 2 (Long Range)
        sensor.set_distance_mode(1)
        
        # 设置定时预算 (Timing Budget) 和 测量间隔
        # 增加定时预算可以提高精度和最大距离稳定性
        sensor.set_timing_budget_in_ms(50)
        sensor.set_inter_measurement_in_ms(100)
        
        print("开始测距 (按 Ctrl+C 退出)...")
        print("-" * 70)
        print(f"{'距离(mm)':<10} | {'状态':<15} | {'信号强度':<10} | {'环境光':<10}")
        print("-" * 70)
        
        sensor.start_ranging()
        
        while True:
            # 等待数据就绪
            while sensor.check_for_data_ready() == 0:
                time.sleep(0.01)
            
            distance = sensor.get_distance()
            
            # 获取诊断信息
            # 状态 0: 有效数据
            # 状态 1: 信号太弱 (Sigma Failure)
            # 状态 2: 信号饱和 (Signal saturation)
            # 状态 4: 包裹错误 (Wrap around) - 意味着测到了比量程更远的东西
            status = sensor.get_range_status()
            signal = sensor.get_signal_rate()
            ambient = sensor.get_ambient_rate()
            
            sensor.clear_interrupt()
            

            # 状态码,处理逻辑
            # 0,接受：直接使用数据。
            # 1 / 2,可疑：如果对精度要求不高，可以经过低通滤波后使用；若要求高，则视为无效。
            # 4 / 7,丢弃：数据完全错误，应过滤掉，避免导致机器人避障或定位发生“闪变”。
            # 状态映射
            status_map = {
                0: "有效 (Valid)",
                1: "信号弱 (Sigma)", # 含义：测距值的标准差（Sigma）超过了预设阈值。解读：这通常发生在距离太远或目标反射率太低（如深色吸光物体）的情况下。传感器虽然收到了回波，但因为信号太弱，背景噪声的影响太大，导致测出来的距离上下波动剧烈，准确性较差。
                2: "信号饱和 (Saturat)", # 含义：接收器检测到的光强度超过了传感器的处理极限。 解读：这通常发生在目标物距离太近或目标物反射率极高（如镜面、白色强反光物体）时。就像强光晃眼一样，传感器被“晒晕”了，无法准确分辨反射的时间点。
                4: "溢出 (Wrap)", # 含义：发生了“相位卷绕”或超出了测量量程。 解读：Phase Wrapping：这是 ToF 传感器的物理特性。如果物体远在量程之外（例如在 10 米外），反射回来的光子可能在“第二个周期”才到达，传感器会误以为它非常近。VL53L1X 的固件通常会尝试检测并屏蔽这种错误，返回状态 4 表示该点不可信。
                7: "无效数据 (Invalid)"
            }
            status_msg = status_map.get(status, f"代码:{status}")
            
            print(f"{distance:<10d} | {status_msg:<15} | {signal:<10.1f} | {ambient:<10.1f}")
            
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
