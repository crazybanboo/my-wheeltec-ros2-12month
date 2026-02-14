#!/usr/bin/env python3
"""VL53L1X 8-sensor array driver with TCA9548A I2C multiplexer support."""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Range
from std_msgs.msg import Bool
import qwiic_vl53l1x
from qwiic_i2c.linux_i2c import LinuxI2C
import smbus2
import time

# Optional GPIO import - may not be available on all platforms
try:
    import Hobot.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False


class VL53L1XArrayNode(Node):
    """ROS2 node for controlling 8 VL53L1X sensors via TCA9548A multiplexer."""

    # XSHUT pin mapping (BOARD encoding) for each sensor channel
    DEFAULT_XSHUT_PINS = [38, 26, 24, 22, 18, 12, 10, 8]

    # Default sensor positions based on circular layout
    DEFAULT_FRAME_IDS = [
        "tof_link_0", "tof_link_1", "tof_link_2", "tof_link_3",
        "tof_link_4", "tof_link_5", "tof_link_6", "tof_link_7"
    ]

    # Status code mapping
    STATUS_MAP = {
        0: "valid",      # Valid measurement
        1: "sigma_fail", # Weak signal
        2: "signal_fail",# Signal failure
        4: "out_of_bounds",# Out of bounds
        7: "wrap_around",  # Invalid/wrap around
    }

    def __init__(self):
        super().__init__('vl53l1x_array_node')

        # Declare parameters
        self.declare_parameter('i2c_bus', 0)
        self.declare_parameter('tca9548a_addr', 0x70)
        self.declare_parameter('vl53l1x_addr', 0x29)
        self.declare_parameter('xshut_pins', self.DEFAULT_XSHUT_PINS)
        self.declare_parameter('frame_ids', self.DEFAULT_FRAME_IDS)
        self.declare_parameter('min_range', 0.01)  # meters
        self.declare_parameter('max_range', 4.0)   # meters
        self.declare_parameter('collision_threshold', 0.2)  # meters
        self.declare_parameter('range_mode', 1)    # 1=Short, 2=Long
        self.declare_parameter('timing_budget', 50)  # ms
        self.declare_parameter('inter_measurement', 100)  # ms - sync with 10Hz publish rate
        self.declare_parameter('publish_rate', 10.0)  # Hz
        self.declare_parameter('power_cycle_on_init', True)
        self.declare_parameter('field_of_view', 0.4712)  # 27 degrees in radians

        # Get parameters
        self.i2c_bus = self.get_parameter('i2c_bus').value
        self.tca9548a_addr = self.get_parameter('tca9548a_addr').value
        self.vl53l1x_addr = self.get_parameter('vl53l1x_addr').value
        self.xshut_pins = self.get_parameter('xshut_pins').value
        self.frame_ids = self.get_parameter('frame_ids').value
        self.min_range = self.get_parameter('min_range').value
        self.max_range = self.get_parameter('max_range').value
        self.collision_threshold = self.get_parameter('collision_threshold').value
        self.range_mode = self.get_parameter('range_mode').value
        self.timing_budget = self.get_parameter('timing_budget').value
        self.inter_measurement = self.get_parameter('inter_measurement').value
        self.publish_rate = self.get_parameter('publish_rate').value
        self.power_cycle_on_init = self.get_parameter('power_cycle_on_init').value
        self.field_of_view = self.get_parameter('field_of_view').value

        # Validate parameters
        if len(self.xshut_pins) != 8:
            self.get_logger().warn(f"Expected 8 XSHUT pins, got {len(self.xshut_pins)}")
        if len(self.frame_ids) != 8:
            self.get_logger().warn(f"Expected 8 frame_ids, got {len(self.frame_ids)}")

        # Initialize I2C bus for TCA9548A control
        try:
            self.smbus = smbus2.SMBus(self.i2c_bus)
        except Exception as e:
            self.get_logger().error(f"Failed to open I2C bus {self.i2c_bus}: {e}")
            raise

        # Power cycle sensors if requested and GPIO available
        if self.power_cycle_on_init:
            if GPIO_AVAILABLE:
                self.power_cycle_sensors()
            else:
                self.get_logger().warn("GPIO not available, skipping power cycle. "
                                      "Install Hobot.GPIO for hardware reset support.")

        # Initialize I2C driver for VL53L1X library
        self.i2c_driver = LinuxI2C(self.i2c_bus)

        # Sensor instances (None if initialization failed)
        self.sensors = [None] * 8
        self.sensor_status = [False] * 8  # Track which sensors are active

        # Initialize all sensors
        self.initialize_sensors()

        # Create publishers for each sensor
        self.range_pubs = []
        for i in range(8):
            topic_name = f'/tof/range_{i}'
            pub = self.create_publisher(Range, topic_name, 10)
            self.range_pubs.append(pub)

        # Collision warning publisher
        self.collision_pub = self.create_publisher(Bool, '/tof/collision_warning', 10)

        # Create timer for periodic readings
        self.timer = self.create_timer(1.0 / self.publish_rate, self.timer_callback)

        active_count = sum(self.sensor_status)
        self.get_logger().info(f"VL53L1X array node initialized. "
                              f"Active sensors: {active_count}/8")

    def power_cycle_sensors(self):
        """Perform hardware reset of all sensors using XSHUT pins."""
        if not GPIO_AVAILABLE:
            return

        self.get_logger().info("Power cycling sensors via GPIO...")

        try:
            GPIO.setmode(GPIO.BOARD)
            GPIO.setwarnings(False)

            # Initialize all pins as output
            for pin in self.xshut_pins:
                GPIO.setup(pin, GPIO.OUT)

            # Pull all XSHUT low (reset)
            for pin in self.xshut_pins:
                GPIO.output(pin, GPIO.LOW)
            time.sleep(0.3)

            # Pull all XSHUT high (enable)
            for pin in self.xshut_pins:
                GPIO.output(pin, GPIO.HIGH)
            time.sleep(0.3)

            self.get_logger().info("Power cycle complete")

        except Exception as e:
            self.get_logger().error(f"GPIO power cycle failed: {e}")

    def select_tca_channel(self, channel):
        """Select active channel on TCA9548A multiplexer.

        Args:
            channel: Channel number (0-7)
        """
        if 0 <= channel <= 7:
            try:
                self.smbus.write_byte(self.tca9548a_addr, 1 << channel)
                time.sleep(0.01)
            except Exception as e:
                self.get_logger().warn(f"Failed to select TCA channel {channel}: {e}")

    def initialize_sensors(self):
        """Initialize all 8 sensors through TCA9548A."""
        self.get_logger().info("Initializing VL53L1X sensor array...")

        for ch in range(8):
            self.select_tca_channel(ch)

            try:
                sensor = qwiic_vl53l1x.QwiicVL53L1X(
                    address=self.vl53l1x_addr,
                    i2c_driver=self.i2c_driver
                )

                if sensor.sensor_init():
                    sensor.set_distance_mode(self.range_mode)
                    sensor.set_timing_budget_in_ms(self.timing_budget)
                    sensor.set_inter_measurement_in_ms(self.inter_measurement)
                    sensor.start_ranging()

                    self.sensors[ch] = sensor
                    self.sensor_status[ch] = True
                    self.get_logger().info(f"  Channel {ch}: [OK] - {self.frame_ids[ch]}")
                else:
                    self.sensors[ch] = None
                    self.sensor_status[ch] = False
                    self.get_logger().warn(f"  Channel {ch}: [FAILED] - init failed")

            except Exception as e:
                self.sensors[ch] = None
                self.sensor_status[ch] = False
                self.get_logger().warn(f"  Channel {ch}: [FAILED] - {e}")

        active = sum(self.sensor_status)
        self.get_logger().info(f"Sensor initialization complete: {active}/8 active")

    def generate_range_msg(self, ch, stamp, distance_m, status):
        """Generate Range message from sensor reading."""
        range_msg = Range()
        range_msg.header.stamp = stamp
        range_msg.header.frame_id = self.frame_ids[ch]
        range_msg.radiation_type = Range.INFRARED
        range_msg.field_of_view = self.field_of_view
        range_msg.min_range = self.min_range
        range_msg.max_range = self.max_range

        if status == 0:
            # Valid measurement
            range_msg.range = distance_m
        elif status in [1, 2, 4, 7]:
            # Weak signal, saturation, or overflow - treat as max range
            range_msg.range = self.max_range
        else:
            # Invalid status
            range_msg.range = float('nan')

        return range_msg

    def timer_callback(self):
        """
        优化后的回调：
        1. 移除 while 循环和 time.sleep
        2. 每个通道仅进行一次查询，降低 I2C 负载
        """
        collision_detected = False
        current_time = self.get_clock().now().to_msg()

        for ch in range(8):
            if not self.sensor_status[ch]:
                continue

            sensor = self.sensors[ch]
            try:
                # 切换通道
                self.select_tca_channel(ch)

                # --- 关键优化：只检查一次，不迭代等待 ---
                # 如果硬件还没准备好，直接跳过这一帧，不阻塞 CPU
                if sensor.check_for_data_ready() != 0:
                    distance_mm = sensor.get_distance()
                    status = sensor.get_range_status()
                    sensor.clear_interrupt()

                    distance_m = distance_mm / 1000.0

                    # 发布数据逻辑
                    range_msg = self.generate_range_msg(ch, current_time, distance_m, status)
                    self.range_pubs[ch].publish(range_msg)

                    if status == 0 and distance_m < self.collision_threshold:
                        collision_detected = True
                else:
                    # 如果数据没好，直接跳过
                    pass

            except Exception as e:
                self.get_logger().debug(f"Channel {ch} read error: {e}")

        # Publish collision warning
        collision_msg = Bool()
        collision_msg.data = collision_detected
        self.collision_pub.publish(collision_msg)

    def stop(self):
        """Stop ranging on all sensors."""
        self.get_logger().info("Stopping sensors...")
        for ch, sensor in enumerate(self.sensors):
            if sensor is not None:
                try:
                    self.select_tca_channel(ch)
                    sensor.stop_ranging()
                except Exception as e:
                    self.get_logger().debug(f"Error stopping channel {ch}: {e}")

        if GPIO_AVAILABLE:
            try:
                GPIO.cleanup()
            except Exception:
                pass


def main(args=None):
    """Main entry point."""
    rclpy.init(args=args)
    node = None

    try:
        node = VL53L1XArrayNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Node execution failed: {e}")
    finally:
        if node:
            node.stop()
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
