"""
GUI interface to control the position of the XArm6 using a ROS2 topic to communicate
with the MoveIt API.
"""

import tkinter as tk
from tkinter import ttk
import rclpy
from geometry_msgs.msg import Pose
from std_msgs.msg import String
import numpy as np


# ============================================================
#   SUB-COMPONENTES DE LA UI
# ============================================================

class PositionControlPanel(ttk.LabelFrame):
    """Panel con controles de posición y orientación."""

    def __init__(self, master, on_set_pose, on_reset, on_circle, on_square):
        super().__init__(master, text="Position and Orientation Control", padding="20")
        self.on_set_pose = on_set_pose
        self.on_reset = on_reset
        self.on_circle = on_circle
        self.on_square = on_square

        self.entries = {}
        self._build()

    def _build(self):
        # ===== Row 1: X, Y, Z =====
        axes = [("X Position", "meters"), ("Y Position", "meters"), ("Z Position", "meters")]

        for i, (label, unit) in enumerate(axes):
            ttk.Label(self, text=label, font=('Arial', 11, 'bold')).grid(row=0, column=i)
            ttk.Label(self, text=f"({unit})", font=('Arial', 9)).grid(row=1, column=i)

            entry = ttk.Entry(self, width=15, font=('Arial', 11), justify='center')
            entry.insert(0, "0.0")
            entry.grid(row=2, column=i, padx=10, pady=5)
            self.entries[label.split()[0].lower()] = entry  # x, y, z

        # ===== Row 2: Yaw, Pitch, Roll =====
        angles = [("Yaw", "degrees"), ("Pitch", "degrees"), ("Roll", "degrees")]
        for i, (label, unit) in enumerate(angles):
            ttk.Label(self, text=label, font=('Arial', 11, 'bold')).grid(row=3, column=i, pady=10)
            ttk.Label(self, text=f"({unit})", font=('Arial', 9)).grid(row=4, column=i)

            entry = ttk.Entry(self, width=15, font=('Arial', 11), justify='center')
            entry.insert(0, "0.0")
            entry.grid(row=5, column=i, padx=10, pady=5)
            self.entries[label.lower()] = entry  # yaw, pitch, roll

        ttk.Separator(self).grid(row=6, column=0, columnspan=3, pady=10, sticky="ew")

        # ===== Row 3 Buttons =====
        ttk.Button(self, text="Set Pose", command=self.on_set_pose).grid(
            row=7, column=0, columnspan=2, sticky='ew', padx=10
        )
        ttk.Button(self, text="Reset All", command=self.on_reset).grid(
            row=7, column=2, sticky='ew', padx=10
        )

        # ===== Row 4 Buttons =====
        ttk.Button(self, text="Draw Circle", command=self.on_circle).grid(
            row=8, column=0, pady=10, sticky='ew'
        )
        ttk.Button(self, text="Draw Square", command=self.on_square).grid(
            row=8, column=1, pady=10, sticky='ew'
        )

        for i in range(3):
            self.columnconfigure(i, weight=1)


class StatusPanel(ttk.LabelFrame):
    """Panel para mostrar mensajes de estado."""

    def __init__(self, master):
        super().__init__(master, text="Status", padding="15")
        ttk.Label(self, text="Current Status:", font=('Arial', 10, 'bold')).grid(row=0, sticky='w')
        self.display = ttk.Label(self, text="Ready to receive commands...", foreground="blue")
        self.display.grid(row=1, sticky='w')

    def update_status(self, text, color="black"):
        self.display.config(text=text, foreground=color)


class EmergencyPanel(ttk.LabelFrame):
    """Botón de parada de emergencia."""

    def __init__(self, master, on_stop):
        super().__init__(master, text="Other Controls", padding="20")

        tk.Button(
            self, text="STOP",
            command=on_stop,
            width=15, height=4,
            bg="red", fg="white",
            font=("Arial", 16, "bold")
        ).grid(row=0, column=0, pady=10, padx=10)

class DrawingPanel(ttk.LabelFrame):
    """Panel para dibujar una trayectoria y discretizarla para ROS."""

    def __init__(self, master, on_send_path, width=400, height=400):
        super().__init__(master, text="Drawing Panel", padding="10")

        self.on_send_path = on_send_path  # callback al main

        # Estado
        ttk.Label(self, text="Drawing Status:", font=('Arial', 10, 'bold')).grid(row=0, sticky='w')
        self.status_label = ttk.Label(self, text="Ready", foreground="green")
        self.status_label.grid(row=1, sticky='w', pady=(0, 10))

        # Canvas
        self.canvas_width = width
        self.canvas_height = height
        self.canvas = tk.Canvas(self, width=width, height=height, bg="white",
                                relief="solid", borderwidth=1)
        self.canvas.grid(row=2, column=0, padx=5, pady=5)

        self.path_points = []

        self.canvas.bind("<ButtonPress-1>", self._start_drawing)
        self.canvas.bind("<B1-Motion>", self._draw)
        self.canvas.bind("<ButtonRelease-1>", self._finish_drawing)

        # Botones
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=3, column=0, pady=10)

        ttk.Button(btn_frame, text="Clear", width=20, command=self.clear_canvas)\
            .grid(row=0, column=0, padx=5)

        ttk.Button(btn_frame, text="Send Path", width=20, command=self._send_discretized)\
            .grid(row=0, column=1, padx=5)

    # ======================= EVENTOS ==========================

    def _start_drawing(self, event):
        self.path_points = [(event.x, event.y)]
        self.last_x, self.last_y = event.x, event.y
        self.status_label.config(text="Drawing...", foreground="blue")

    def _draw(self, event):
        self.canvas.create_line(self.last_x, self.last_y, event.x, event.y,
                                fill="black", width=2)
        self.path_points.append((event.x, event.y))
        self.last_x, self.last_y = event.x, event.y

    def _finish_drawing(self, event):
        self.status_label.config(text="Done", foreground="green")

    # ======================== UTILIDADES =======================

    def clear_canvas(self):
        self.canvas.delete("all")
        self.path_points = []
        self.status_label.config(text="Ready", foreground="green")

    def get_discretized_path(self, n_points=60):
        if len(self.path_points) < 2:
            return []

        path = np.array(self.path_points)

        dist = np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))
        dist = np.insert(dist, 0, 0.0)

        target_dist = np.linspace(0, dist[-1], n_points)

        x_interp = np.interp(target_dist, dist, path[:, 0])
        y_interp = np.interp(target_dist, dist, path[:, 1])

        return list(zip(x_interp, y_interp))

    def _send_discretized(self):
        """Callback → llama al callback del programa principal."""
        if len(self.path_points) < 2:
            self.status_label.config(text="Nothing drawn!", foreground="red")
            return

        self.status_label.config(text="Sending...", foreground="purple")
        self.on_send_path(self.get_discretized_path())

# ============================================================
#   APLICACIÓN PRINCIPAL
# ============================================================

class RobotPositionControlGrid:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("XArm6 - Position and Orientation Control")
        self.root.geometry("1000x900")

        self._build_layout()
        self._init_ros()

    # ------------------------------- UI Layout -------------------------------------

    def _build_layout(self):
        ttk.Label(
            self.root,
            text="XArm6 Position and Orientation Control",
            font=('Arial', 16, 'bold')
        ).grid(row=0, column=0, columnspan=4, pady=15)

        # Panel de posición
        self.position_panel = PositionControlPanel(
            master=self.root,
            on_set_pose=self.set_pose,
            on_reset=self.reset_all,
            on_circle=self.send_circle_command,
            on_square=self.send_square_command
        )
        self.position_panel.grid(row=1, column=0, columnspan=2, sticky='ew', padx=20)

        # Panel de estado
        self.status_panel = StatusPanel(self.root)
        self.status_panel.grid(row=2, column=0, columnspan=2, sticky='ew', padx=20, pady=10)

        # Canvas para dibujo
        self.drawing_canvas = DrawingPanel(
            self.root,
            on_send_path=self.send_drawing_path,
            width=600,
            height=600
        )
        self.drawing_canvas.grid(row=1, column=6, rowspan=2, columnspan= 3, padx=20, sticky='nsew')

        # Panel STOP
        self.emergency_panel = EmergencyPanel(self.root, on_stop=self.send_emergency_stop)
        self.emergency_panel.grid(row=1, column=9, padx=20, sticky='n')

        

    # ------------------------------- ROS -------------------------------------------

    def _init_ros(self):
        rclpy.init(args=None)
        self.node = rclpy.create_node("xarm_gui_node")

        self.pub_pose = self.node.create_publisher(Pose, "/xarm/target_pose", 10)
        self.pub_cmd = self.node.create_publisher(String, "/xarm/shape_command", 10)
        self.pub_path = self.node.create_publisher(Pose, "/xarm/drawing_path", 10)

    # ------------------------------- Logic -----------------------------------------

    def _publish_status(self, msg, color):
        self.status_panel.update_status(msg, color)

    def set_pose(self):
        try:
            pose_values = {k: float(v.get()) for k, v in self.position_panel.entries.items()}

            msg = Pose()
            msg.position.x = pose_values['x']
            msg.position.y = pose_values['y']
            msg.position.z = pose_values['z']
            msg.orientation.x = pose_values['roll']
            msg.orientation.y = pose_values['pitch']
            msg.orientation.z = pose_values['yaw']
            msg.orientation.w = 1.0

            self.pub_pose.publish(msg)

            self._publish_status("Pose sent successfully", "green")

        except ValueError:
            self._publish_status("ERROR: Invalid input, numbers only.", "red")

    def reset_all(self):
        for entry in self.position_panel.entries.values():
            entry.delete(0, tk.END)
            entry.insert(0, "0.0")

        self._publish_status("All fields reset.", "blue")

    def _send_shape(self, cmd, text, color):
        msg = String()
        msg.data = cmd
        self.pub_cmd.publish(msg)
        self._publish_status(text, color)

    def send_circle_command(self):
        self._send_shape("circle", "Drawing circle...", "purple")

    def send_square_command(self):
        self._send_shape("square", "Drawing square...", "purple")

    def send_drawing_path(self, path_points):
        """
        path_points = [(x,y), (x,y), ...] ya discretizados.
        Se enviará un Pose por cada punto al tópico /xarm/drawing_path.
        """

        if len(path_points) == 0:
            self._publish_status("Empty path, nothing sent.", "red")
            return

        for (x, y) in path_points:
            msg = Pose()
            msg.position.x = float(x)
            msg.position.y = float(y)
            msg.position.z = 0.0  # Puedes aplicar scaling aquí

            msg.orientation.w = 1.0
            self.pub_path.publish(msg)

        self._publish_status(f"Sent {len(path_points)} points.", "green")

    def send_emergency_stop(self):
        self._send_shape("stop", "!!! EMERGENCY STOP SENT !!!", "red")

    def run(self):
        self.root.mainloop()


# ============================================================
#   MAIN
# ============================================================

def main():
    app = RobotPositionControlGrid()
    app.run()


if __name__ == "__main__":
    main()
