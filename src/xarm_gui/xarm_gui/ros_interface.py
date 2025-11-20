import rclpy
from geometry_msgs.msg import Pose
from std_msgs.msg import String

class RosInterface:
    def __init__(self, on_status_update=None):
        self.on_status = on_status_update

        rclpy.init(args=None)
        self.node = rclpy.create_node("xarm_gui_node")

        self.pub_pose = self.node.create_publisher(Pose, "/xarm/target_pose", 10)
        self.pub_cmd = self.node.create_publisher(String, "/xarm/shape_command", 10)
        self.pub_path = self.node.create_publisher(Pose, "/xarm/drawing_path", 10)

        self._report("ROS2 initialized.", "green")

    def _report(self, msg, color):
        if self.on_status:
            self.on_status(msg, color)

    # ---------------- POSE ----------------
    def send_pose(self, pose_dict):
        msg = Pose()
        msg.position.x = pose_dict["x"]
        msg.position.y = pose_dict["y"]
        msg.position.z = pose_dict["z"]

        msg.orientation.x = pose_dict["roll"]
        msg.orientation.y = pose_dict["pitch"]
        msg.orientation.z = pose_dict["yaw"]
        msg.orientation.w = 1.0

        self.pub_pose.publish(msg)
        self._report("Pose sent.", "green")

    # ---------------- COMMANDS -------------
    def send_command(self, cmd: str):
        msg = String()
        msg.data = cmd
        self.pub_cmd.publish(msg)
        self._report(f"Command: {cmd}", "purple")

    # ---------------- PATH -----------------
    def send_path(self, points):
        for x, y in points:
            msg = Pose()
            msg.position.x = float(x)
            msg.position.y = float(y)
            msg.position.z = 0.0
            msg.orientation.w = 1.0
            self.pub_path.publish(msg)

        self._report(f"Sent {len(points)} path points.", "green")
