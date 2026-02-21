import Hobot.GPIO as GPIO
import qwiic_vl53l1x
from qwiic_i2c.linux_i2c import LinuxI2C
import smbus2
import time

# --- 配置参数 ---
I2C_BUS = 0
TCA9548A_ADDR = 0x70
VL53L1X_ADDR = 0x29
CHANNELS = range(8)

# XSHUT 引脚列表 (使用 BOARD 编码)
XSHUT_PINS = [38, 26, 24, 22, 18, 12, 10, 8]

# --- GPIO 初始化与复位 ---

def power_cycle_sensors(pins):
    """
    使用 Hobot.GPIO 对所有传感器进行硬件复位
    """
    print("正在通过 GPIO 进行硬件复位...")
    
    # 设置引脚模式为 BOARD
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)
    
    # 初始化所有引脚为输出
    for pin in pins:
        GPIO.setup(pin, GPIO.OUT)
    
    # 1. 逐个拉低 (关闭所有传感器)
    for pin in pins:
        GPIO.output(pin, GPIO.LOW)
    print("XSHUT 已拉低，传感器已进入复位状态...")
    time.sleep(0.3) # 稍微延长复位时间确保彻底断电
    
    # 2. 逐个拉高 (启动所有传感器)
    for pin in pins:
        GPIO.output(pin, GPIO.HIGH)
    print("XSHUT 已拉高，传感器启动中...")
    time.sleep(0.3) 

# --- I2C 通道切换 ---

bus = smbus2.SMBus(I2C_BUS)

def select_tca_channel(channel):
    """切换 TCA9548A 的通道"""
    if 0 <= channel <= 7:
        bus.write_byte(TCA9548A_ADDR, 1 << channel)
        time.sleep(0.01)

# --- 主程序 ---

def main():
    # 步骤 1: 硬件复位
    power_cycle_sensors(XSHUT_PINS)

    # 步骤 2: 初始化 I2C 驱动
    i2c_driver = LinuxI2C(I2C_BUS)
    sensors = []
    
    print("\n正在初始化 VL53L1X 传感器集群...")
    
    for ch in CHANNELS:
        select_tca_channel(ch)
        
        # 创建传感器实例
        sensor = qwiic_vl53l1x.QwiicVL53L1X(address=VL53L1X_ADDR, i2c_driver=i2c_driver)
        
        # 尝试初始化（带重试机制）
        init_success = False
        for retry in range(3):
            if sensor.sensor_init() == None:
                init_success = True
                break
            time.sleep(0.5)

        if init_success:
            sensor.set_distance_mode(2)  # 2: 长距离模式 1: 短距离模式
            sensor.set_timing_budget_in_ms(50)
            sensor.set_inter_measurement_in_ms(60)
            sensor.start_ranging()
            sensors.append(sensor)
            print(f"通道 {ch}: [OK]")
        else:
            sensors.append(None)
            print(f"通道 {ch}: [FAILED]")

    print("\n" + "="*80)
    print("开始实时读取数据 (Ctrl+C 退出)")
    print("格式: 通道0 | 通道1 | 通道2 | 通道3 | 通道4 | 通道5 | 通道6 | 通道7")
    print("="*80 + "\n")
    
    status_map = {0: "有效", 1: "弱信号", 2: "饱和", 4: "溢出", 7: "无效"}

    try:
        while True:
            dist_results = []
            stat_results = []
            
            for i, sensor in enumerate(sensors):
                if sensor is None:
                    dist_results.append(" N/A  ")
                    stat_results.append("离线")
                    continue
                
                # 切换到对应通道
                select_tca_channel(i)
                
                # 等待数据就绪
                retry = 0
                while sensor.check_for_data_ready() == 0 and retry < 10:
                    time.sleep(0.005)
                    retry += 1
                
                distance = sensor.get_distance()
                status = sensor.get_range_status()
                
                dist_results.append(f"{distance:4d}mm")
                stat_results.append(f"{status_map.get(status, '错误')}")
            
            # 格式化打印
            print(f"{' | '.join(dist_results)} === {' | '.join(stat_results)}")
            
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n\n程序正在安全退出...")
    finally:
        # 停止所有传感器的测距并清理 GPIO
        for i, sensor in enumerate(sensors):
            if sensor:
                try:
                    select_tca_channel(i)
                    sensor.stop_ranging()
                except:
                    pass
        
        GPIO.cleanup() # 释放 GPIO 资源
        print("GPIO 已清理，程序已退出。")

if __name__ == "__main__":
    main()