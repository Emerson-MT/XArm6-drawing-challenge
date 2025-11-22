import rclpy
from geometry_msgs.msg import PoseArray, Pose
from std_msgs.msg import String
import math

class RosInterface:
    def __init__(self, on_status_update=None):
        self.on_status = on_status_update

        rclpy.init(args=None)
        self.node = rclpy.create_node("xarm_gui_node")

        self.pub_pose = self.node.create_publisher(Pose, "/xarm/target_pose", 10)
        self.pub_cmd = self.node.create_publisher(String, "/xarm/shape_command", 10)
        self.pub_path = self.node.create_publisher(PoseArray, "/xarm/drawing_path", 10)

        self._report("ROS2 initialized.", "green")

    def _report(self, msg, color):
        if self.on_status:
            self.on_status(msg, color)
    
      # ----------------- quaternion helper -----------------
    @staticmethod
    def quaternion_from_euler(roll: float, pitch: float, yaw: float):
        """
        Return quaternion (x, y, z, w) from roll, pitch, yaw (radians).
        """
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)

        w = cr * cp * cy + sr * sp * sy
        x = sr * cp * cy - cr * sp * sy
        y = cr * sp * cy + sr * cp * sy
        z = cr * cp * sy - sr * sp * cy
        return x, y, z, w


    # ---------------- POSE ----------------
    def send_pose(self, pose_dict):
        """
        pose_dict expected keys: "x","y","z","roll","pitch","yaw".
        roll/pitch/yaw may be in degrees or radians: if abs(val) > 2*pi we treat it as degrees.
        """
        # read translations
        x = float(pose_dict.get("x", 0.0))
        y = float(pose_dict.get("y", 0.0))
        z = float(pose_dict.get("z", 0.0))

        # read rotations
        roll = float(pose_dict.get("roll", 0.0))
        pitch = float(pose_dict.get("pitch", 0.0))
        yaw = float(pose_dict.get("yaw", 0.0))

        # Heuristic: if angles appear to be in degrees (large magnitude), convert to radians
        if any(abs(a) > 2 * math.pi for a in (roll, pitch, yaw)):
            roll = math.radians(roll)
            pitch = math.radians(pitch)
            yaw = math.radians(yaw)

        qx, qy, qz, qw = self.quaternion_from_euler(roll, pitch, yaw)

        msg = Pose()
        msg.position.x = x
        msg.position.y = y
        msg.position.z = z

        msg.orientation.x = qx
        msg.orientation.y = qy
        msg.orientation.z = qz
        msg.orientation.w = qw

        self.pub_pose.publish(msg)
        self._report("Pose sent (with quaternion).", "green")

    # ---------------- COMMANDS -------------
    def send_command(self, cmd: str):
        msg = String()
        msg.data = cmd
        self.pub_cmd.publish(msg)
        self._report(f"Command: {cmd}", "purple")

    # ---------------- PATH -----------------
    def send_path(self, points, canvas_width=1000, canvas_height=1000):
        """
        points: lista de tuplas (x, y) desde el canvas
        Los ángulos roll, pitch, yaw se definen dentro de la función en radianes.
        Transformaciones aplicadas:
        - Sistema de coordenadas: origen en centro del límite inferior, x arriba, y izquierda
        - Offset en x para alejar del robot
        - Altura fija z = 0.1
        """
        msg = PoseArray()
        msg.header.frame_id = "world"

        factor = 0.0004  # Escala para 80 cm x 80 cm
        x_offset = 0.2   # Offset en x final para alejar del robot

        # ----------------- Ángulos definidos internamente -----------------
        roll = 0.0
        pitch = math.pi   # 180 grados
        yaw = 0.0         # 0 grados

        qx, qy, qz, qw = self.quaternion_from_euler(roll, pitch, yaw)

        for x_canvas, y_canvas in points:
            # ----------------- Traslación al nuevo origen -----------------
            #x_t = x_canvas - canvas_width
            x_t = x_canvas
            y_t = canvas_height - y_canvas

            # ----------------- Rotación 90° antihoraria -----------------
            x_r = y_t
            y_r = -x_t

            # ----------------- Escalado y offset final -----------------
            x_b = x_r * factor + x_offset
            y_b = y_r * factor
            z_b = 0.1

            # ---------------- Crear pose ----------------
            p = Pose()
            p.position.x = x_b
            p.position.y = y_b
            p.position.z = z_b

            p.orientation.x = qx
            p.orientation.y = qy
            p.orientation.z = qz
            p.orientation.w = qw

            msg.poses.append(p)

        self.pub_path.publish(msg)
        self._report(f"Sent {len(points)} path points with quaternion orientation.", "green")

