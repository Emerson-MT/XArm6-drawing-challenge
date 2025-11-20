import tkinter as tk
from tkinter import ttk

from xarm_gui.panels.position_panel import PositionControlPanel
from xarm_gui.panels.status_panel import StatusPanel
from xarm_gui.panels.emergency_panel import EmergencyPanel
from xarm_gui.panels.drawing_panel import DrawingPanel
from xarm_gui.ros_interface import RosInterface


class RobotPositionControlGrid:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("XArm6 - Position and Orientation Control")
        self.root.geometry("1400x900")

        # GUI primero
        self._build_layout()

        # ROS después (así status_panel ya existe)
        self._init_ros()

    # ----------------------------------------------------------------------
    def _build_layout(self):

        ttk.Label(
            self.root,
            text="XArm6 Position and Orientation Control",
            font=('Arial', 16, 'bold')
        ).grid(row=0, column=0, columnspan=10, pady=15)

        # Panel de posición
        self.position_panel = PositionControlPanel(
            master=self.root,
            on_set_pose=self.set_pose,                # ✔ GUI -> GUI
            on_reset=self.reset_all,
            on_circle=self.send_circle_command,      # ✔ GUI -> GUI
            on_square=self.send_square_command
        )
        self.position_panel.grid(row=1, column=0, columnspan=3, sticky='nsew', padx=20)

        # Panel de estado
        self.status_panel = StatusPanel(self.root)
        self.status_panel.grid(row=2, column=0, columnspan=3, sticky='ew', padx=20, pady=10)

        # Panel de dibujo
        self.drawing_canvas = DrawingPanel(
            master=self.root,
            on_send_path=self.send_drawing_path,      # ✔ GUI -> GUI
            width=600,
            height=600
        )
        self.drawing_canvas.grid(row=1, column=3, rowspan=2, columnspan=5, padx=20, sticky='nsew')

        # Panel STOP
        self.emergency_panel = EmergencyPanel(
            master=self.root,
            on_stop=self.send_emergency_stop          # ✔ GUI -> GUI
        )
        self.emergency_panel.grid(row=1, column=8, padx=20, sticky='n')

        for i in range(10):
            self.root.columnconfigure(i, weight=1)

    # ----------------------------------------------------------------------
    def _init_ros(self):
        """Crear RosInterface después que la UI está lista."""
        self.ros = RosInterface(on_status_update=self._publish_status)

    # ----------------------------------------------------------------------
    def _publish_status(self, msg, color):
        self.status_panel.update_status(msg, color)

    # --------------------------- POSE --------------------------------------
    def set_pose(self):
        try:
            pose_values = {k: float(v.get()) for k, v in self.position_panel.entries.items()}
            self.ros.send_pose(pose_values)       # ✔ GUI → ROSInterface
        except ValueError:
            self._publish_status("Invalid input numbers.", "red")

    # --------------------------- RESET -------------------------------------
    def reset_all(self):
        for entry in self.position_panel.entries.values():
            entry.delete(0, tk.END)
            entry.insert(0, "0.0")
        self._publish_status("All fields reset.", "blue")

    # --------------------------- SHAPES ------------------------------------
    def send_circle_command(self):
        self.ros.send_command("circle")

    def send_square_command(self):
        self.ros.send_command("square")

    # --------------------------- PATH DRAWING ------------------------------
    def send_drawing_path(self, points):
        self.ros.send_path(points)

    # --------------------------- EMERGENCY STOP ----------------------------
    def send_emergency_stop(self):
        self.ros.send_command("stop")

    # ----------------------------------------------------------------------
    def run(self):
        self.root.mainloop()
