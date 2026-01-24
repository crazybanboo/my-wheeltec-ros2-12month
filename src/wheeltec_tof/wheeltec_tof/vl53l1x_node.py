#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
# from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Range
from std_msgs.msg import Bool
import qwiic_vl53l1x
from qwiic_i2c.linux_i2c import LinuxI2C
import time

class VL53L1XNode(Node):
    def __init__(self):
        super().__init__('vl53l1x_node')
        
        # Declare parameters
        self.declare_parameter('i2c_bus', 0)
        self.declare_parameter('i2c_address', 0x29)
        self.declare_parameter('frame_id', 'tof_link')
        self.declare_parameter('min_range', 0.01) # meters
        self.declare_parameter('max_range', 4.0)  # meters
        self.declare_parameter('collision_threshold', 0.2) # meters
        self.declare_parameter('range_mode', 1)   # 1=Short, 2=Long
        self.declare_parameter('timing_budget', 50)
        self.declare_parameter('inter_measurement', 100)
        self.declare_parameter('publish_rate', 10.0)

        # Get parameters
        self.i2c_bus = self.get_parameter('i2c_bus').value
        self.i2c_address = self.get_parameter('i2c_address').value
        self.frame_id = self.get_parameter('frame_id').value
        self.min_range = self.get_parameter('min_range').value
        self.max_range = self.get_parameter('max_range').value
        self.collision_threshold = self.get_parameter('collision_threshold').value
        self.range_mode = self.get_parameter('range_mode').value
        self.timing_budget = self.get_parameter('timing_budget').value
        self.inter_measurement = self.get_parameter('inter_measurement').value
        self.publish_rate = self.get_parameter('publish_rate').value

        # Publishers
        # qos_profile = QoSProfile(depth=10)
        # qos_profile.reliability = ReliabilityPolicy.BEST_EFFORT # 改为 Best Effort 匹配 Nav2
        self.range_pub = self.create_publisher(Range, '/tof/range', 10)
        self.collision_pub = self.create_publisher(Bool, '/tof/collision_warning', 10)

        # Initialize sensor
        self.get_logger().info(f"Initializing VL53L1X on I2C Bus {self.i2c_bus}...")
        try:
            self.i2c_driver = LinuxI2C(self.i2c_bus)
            self.sensor = qwiic_vl53l1x.QwiicVL53L1X(address=self.i2c_address, i2c_driver=self.i2c_driver)
            
            if self.sensor.get_sensor_id() == 0:
                self.get_logger().error("Sensor not detected!")
                raise RuntimeError("Sensor not detected")
                
            self.sensor.sensor_init()
            self.sensor.set_distance_mode(self.range_mode)
            self.sensor.set_timing_budget_in_ms(self.timing_budget)
            self.sensor.set_inter_measurement_in_ms(self.inter_measurement)
            self.sensor.start_ranging()
            self.get_logger().info("VL53L1X initialization successful.")
        except Exception as e:
            self.get_logger().error(f"Failed to initialize sensor: {str(e)}")
            raise e

        # Timer
        self.timer = self.create_timer(1.0 / self.publish_rate, self.timer_callback)

    def timer_callback(self):
        try:
            if self.sensor.check_for_data_ready():
                distance_mm = self.sensor.get_distance()
                status = self.sensor.get_range_status()
                self.sensor.clear_interrupt()

                # Convert to meters
                distance_m = distance_mm / 1000.0

                # Create Range message
                range_msg = Range()
                range_msg.header.stamp = self.get_clock().now().to_msg()
                range_msg.header.frame_id = self.frame_id
                range_msg.radiation_type = Range.INFRARED
                range_msg.field_of_view = 0.4712 # 27 degrees in radians
                range_msg.min_range = self.min_range
                range_msg.max_range = self.max_range
                
                # Check status
                # 0: Valid, 1: Sigma Fail, 2: Signal Fail, 4: Out of Bounds, 7: Wrap Around
                if status == 0:
                    range_msg.range = distance_m
                elif status in [2, 4, 7]:
                    # Signal Fail (2), Out of Bounds (4), or Wrap Around (7)
                    # Treat as "no obstacle detected within max_range"
                    range_msg.range = self.max_range
                else:
                    # Hardware fail (5) or other errors
                    range_msg.range = float('nan')

                self.range_pub.publish(range_msg)

                # Collision warning
                collision_msg = Bool()
                collision_msg.data = (status == 0 and distance_m < self.collision_threshold)
                self.collision_pub.publish(collision_msg)

        except Exception as e:
            self.get_logger().warn(f"Error reading sensor: {str(e)}")

    def stop(self):
        if hasattr(self, 'sensor'):
            self.sensor.stop_ranging()

def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = VL53L1XNode()
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
