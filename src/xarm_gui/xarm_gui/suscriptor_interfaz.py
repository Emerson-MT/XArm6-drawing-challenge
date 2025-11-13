import math
import threading
import time
from copy import deepcopy
from typing import Callable, List

import rclpy
from geometry_msgs.msg import Pose
from rclpy.node import Node
from std_msgs.msg import String
from xarm_msgs.srv import PlanExec, PlanPose, PlanSingleStraight


def quaternion_from_euler(roll: float, pitch: float, yaw: float):
    """Return quaternion tuple (x, y, z, w) from roll, pitch, yaw in radians."""
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


class ShapeListener(Node):
    """Listens to GUI commands and drives MoveIt plans to draw shapes."""

    def __init__(self):
        super().__init__('shape_listener')

        # Parameters to describe the drawing workspace.
        center_xy = self.declare_parameter('drawing_center_xy', [0.4, 0.0]).value
        self.center_x = float(center_xy[0])
        self.center_y = float(center_xy[1])
        self.drawing_height = float(self.declare_parameter('drawing_height', 0.25).value)
        self.circle_radius = float(self.declare_parameter('circle_radius', 0.08).value)
        self.circle_resolution = int(self.declare_parameter('circle_resolution', 24).value)
        self.square_side_length = float(self.declare_parameter('square_side_length', 0.12).value)
        self.approach_offset = float(self.declare_parameter('approach_offset', 0.05).value)
        rpy_deg = self.declare_parameter('tool_orientation_rpy_deg', [180.0, 0.0, 0.0]).value
        roll = math.radians(float(rpy_deg[0]))
        pitch = math.radians(float(rpy_deg[1]))
        yaw = math.radians(float(rpy_deg[2]))
        qx, qy, qz, qw = quaternion_from_euler(roll, pitch, yaw)
        self.tool_orientation = (qx, qy, qz, qw)

        # ROS interfaces.
        self.sub = self.create_subscription(String, '/xarm/shape_command', self._on_command, 10)
        self.status_pub = self.create_publisher(String, '/xarm/shape_status', 10)
        self.pose_plan_client = self.create_client(PlanPose, '/xarm_pose_plan')
        self.straight_plan_client = self.create_client(PlanSingleStraight, '/xarm_straight_plan')
        self.exec_plan_client = self.create_client(PlanExec, '/xarm_exec_plan')
        self._wait_for_services()

        self._worker_thread: threading.Thread | None = None
        self._stop_requested = False
        self._lock = threading.Lock()
        self._handlers: dict[str, Callable[[], bool]] = {
            'circle': self._draw_circle,
            'square': self._draw_square,
        }

        self.get_logger().info('ShapeListener listo, esperando comandos de la GUI...')

    def _wait_for_services(self):
        for client, name in (
            (self.pose_plan_client, '/xarm_pose_plan'),
            (self.straight_plan_client, '/xarm_straight_plan'),
            (self.exec_plan_client, '/xarm_exec_plan'),
        ):
            while not client.wait_for_service(timeout_sec=1.0):
                self.get_logger().warn(f'Esperando servicio {name}...')

    def _on_command(self, msg: String):
        command = msg.data.strip().lower()
        self.get_logger().info(f'Recibido comando: {command}')

        if command == 'stop':
            self._stop_requested = True
            self._publish_status('stop command received')
            return

        handler = self._handlers.get(command)
        if handler is None:
            self._publish_status(f'unknown command received: {command}')
            return

        with self._lock:
            if self._worker_thread and self._worker_thread.is_alive():
                self.get_logger().warn(f'Ya hay un dibujo en progreso, ignorando: {command}')
                self._publish_status('Robot ocupado, espera a que termine el trazo actual')
                return
            self._stop_requested = False
            self._worker_thread = threading.Thread(
                target=self._run_shape, args=(command, handler), daemon=True
            )
            self._worker_thread.start()

    def _run_shape(self, command: str, handler: Callable[[], bool]):
        self._publish_status(f'Iniciando trayectoria: {command}')
        success = False
        try:
            success = handler()
        except Exception as exc:  # pylint: disable=broad-except
            self.get_logger().exception(f'Error ejecutando {command}: {exc}')
            self._publish_status(f'Error al ejecutar {command}')
        finally:
            if self._stop_requested and not success:
                self._publish_status(f'{command} cancelado por STOP')
            elif success:
                self._publish_status(f'{command} completado')
            else:
                self._publish_status(f'No se pudo completar {command}')
            with self._lock:
                self._worker_thread = None
            self._stop_requested = False

    def _draw_circle(self) -> bool:
        if self.circle_resolution < 3:
            self.get_logger().error('circle_resolution debe ser >= 3')
            return False
        waypoints = []
        for idx in range(self.circle_resolution):
            angle = 2.0 * math.pi * idx / self.circle_resolution
            x = self.center_x + self.circle_radius * math.cos(angle)
            y = self.center_y + self.circle_radius * math.sin(angle)
            waypoints.append(self._make_pose(x, y, self.drawing_height))
        waypoints.append(deepcopy(waypoints[0]))
        return self._execute_waypoints(waypoints)

    def _draw_square(self) -> bool:
        half = self.square_side_length / 2.0
        corners = [
            (self.center_x - half, self.center_y - half),
            (self.center_x + half, self.center_y - half),
            (self.center_x + half, self.center_y + half),
            (self.center_x - half, self.center_y + half),
        ]
        waypoints = [self._make_pose(x, y, self.drawing_height) for x, y in corners]
        waypoints.append(deepcopy(waypoints[0]))
        return self._execute_waypoints(waypoints)

    def _execute_waypoints(self, waypoints: List[Pose]) -> bool:
        if not waypoints:
            return False
        start_pose = waypoints[0]
        approach_pose = self._offset_pose(start_pose, self.approach_offset)

        if not self._plan_pose_and_execute(approach_pose):
            return False
        if self._stop_requested:
            return False
        if not self._plan_straight_and_execute(start_pose):
            return False

        for target in waypoints[1:]:
            if self._stop_requested:
                return False
            if not self._plan_straight_and_execute(target):
                return False

        retreat_pose = self._offset_pose(waypoints[-1], self.approach_offset)
        if self._stop_requested:
            return False
        return self._plan_straight_and_execute(retreat_pose)

    def _plan_pose_and_execute(self, pose: Pose) -> bool:
        request = PlanPose.Request()
        request.target = pose
        result = self._call_service(self.pose_plan_client, request, 'pose plan')
        if not (result and result.success):
            self.get_logger().error('Falló el planeamiento cartesiano a la pose solicitada')
            return False
        return self._execute_last_plan()

    def _plan_straight_and_execute(self, pose: Pose) -> bool:
        request = PlanSingleStraight.Request()
        request.target = pose
        result = self._call_service(self.straight_plan_client, request, 'straight plan')
        if not (result and result.success):
            self.get_logger().error('Falló el cálculo de trayectoria recta')
            return False
        return self._execute_last_plan()

    def _execute_last_plan(self) -> bool:
        if self._stop_requested:
            return False
        request = PlanExec.Request()
        request.wait = True
        result = self._call_service(self.exec_plan_client, request, 'plan execution')
        if not (result and result.success):
            self.get_logger().error('Falló la ejecución del plan generado')
            return False
        return True

    def _call_service(self, client, request, label: str):
        if not client.service_is_ready():
            self.get_logger().warn(f'Servicio {label} no disponible, reintentando...')
            if not client.wait_for_service(timeout_sec=5.0):
                self.get_logger().error(f'Servicio {label} no responde')
                return None
        future = client.call_async(request)
        while rclpy.ok():
            if future.done():
                if future.result() is not None:
                    return future.result()
                self.get_logger().error(f'Servicio {label} devolvió excepción: {future.exception()}')
                return None
            if self._stop_requested:
                self.get_logger().warn(f'Se solicitó STOP; se aborta la espera por {label}')
                return None
            time.sleep(0.05)
        return None

    def _make_pose(self, x: float, y: float, z: float) -> Pose:
        pose = Pose()
        pose.position.x = x
        pose.position.y = y
        pose.position.z = z
        pose.orientation.x = self.tool_orientation[0]
        pose.orientation.y = self.tool_orientation[1]
        pose.orientation.z = self.tool_orientation[2]
        pose.orientation.w = self.tool_orientation[3]
        return pose

    @staticmethod
    def _offset_pose(pose: Pose, dz: float) -> Pose:
        new_pose = deepcopy(pose)
        new_pose.position.z += dz
        return new_pose

    def _publish_status(self, text: str):
        status_msg = String()
        status_msg.data = text
        self.status_pub.publish(status_msg)
        self.get_logger().info(text)


def main():
    rclpy.init()
    node = ShapeListener()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
