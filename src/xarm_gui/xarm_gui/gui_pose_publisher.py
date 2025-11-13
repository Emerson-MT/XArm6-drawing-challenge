"""
GUI interface to control the position of the XArm6 using a ROS2 topic to communicate
with the MoveIt api
"""

import tkinter as tk
from tkinter import ttk
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Pose
from std_msgs.msg import String   # Para comandos de figuras / parada


class RobotPositionControlGrid:
    def __init__(self):
        """Constructor - creates the window and widgets"""
        # Create main window
        self.root = tk.Tk()
        self.root.title("XArm6 - Position and Orientation Control")
        self.root.geometry("875x900")

        # Create widgets
        self.create_widgets()

        # Create ROS2 publisher node
        rclpy.init(args=None)
        self.node = rclpy.create_node('xarm_gui_node')

        # Publicador de pose
        self.pose_pub = self.node.create_publisher(Pose, '/xarm/target_pose', 10)

        # Publicador para comandos de forma / parada
        # Otros nodos solo necesitan suscribirse a este tópico (std_msgs/String)
        self.shape_cmd_pub = self.node.create_publisher(String, '/xarm/shape_command', 10)

    def create_widgets(self):
        """Create all GUI elements using GRID layout"""
        # Main title
        self.title_label = ttk.Label(
            self.root,
            text="XArm6 Position and Orientation Control",
            font=('Arial', 16, 'bold')
        )
        self.title_label.grid(row=0, column=0, columnspan=3, pady=15, padx=20, sticky='ew')

        # Frame: Position Control - organized in 2 rows and 3 columns
        self.position_frame = ttk.LabelFrame(
            self.root,
            text="Position and Orientation Control",
            padding="20"
        )
        self.position_frame.grid(row=1, column=0, columnspan=3, pady=10, padx=20, sticky='ew')

        # ===== Row 1: X, Y, Z =====
        axes = [("X Position", "meters"), ("Y Position", "meters"), ("Z Position", "meters")]
        self.entries = {}

        for i, (label, unit) in enumerate(axes):
            ttk.Label(
                self.position_frame,
                text=label,
                font=('Arial', 11, 'bold')
            ).grid(row=0, column=i, pady=5, padx=10)

            ttk.Label(
                self.position_frame,
                text=f"({unit})",
                font=('Arial', 9)
            ).grid(row=1, column=i, pady=2)

            entry = ttk.Entry(
                self.position_frame,
                width=15,
                font=('Arial', 11),
                justify='center'
            )
            entry.insert(0, "0.0")
            entry.grid(row=2, column=i, pady=5, padx=10)
            self.entries[label.split()[0].lower()] = entry  # keys: x, y, z

        # ===== Row 2: Yaw, Pitch, Roll =====
        angles = [("Yaw", "degrees"), ("Pitch", "degrees"), ("Roll", "degrees")]
        for i, (label, unit) in enumerate(angles):
            ttk.Label(
                self.position_frame,
                text=label,
                font=('Arial', 11, 'bold')
            ).grid(row=3, column=i, pady=10, padx=10)

            ttk.Label(
                self.position_frame,
                text=f"({unit})",
                font=('Arial', 9)
            ).grid(row=4, column=i, pady=2)

            entry = ttk.Entry(
                self.position_frame,
                width=15,
                font=('Arial', 11),
                justify='center'
            )
            entry.insert(0, "0.0")
            entry.grid(row=5, column=i, pady=5, padx=10)
            self.entries[label.lower()] = entry  # keys: yaw, pitch, roll

        # Separator line
        ttk.Separator(self.position_frame, orient='horizontal').grid(
            row=6, column=0, columnspan=3, sticky='ew', pady=15
        )

        # ===== Row 3: Botones principales =====
        self.set_position_btn = ttk.Button(
            self.position_frame,
            text="Set Pose",
            command=self.set_pose
        )
        self.set_position_btn.grid(row=7, column=0, columnspan=2, pady=5, padx=10, sticky='ew')

        self.reset_btn = ttk.Button(
            self.position_frame,
            text="Reset All",
            command=self.reset_all
        )
        self.reset_btn.grid(row=7, column=2, pady=5, padx=10, sticky='ew')

        # ===== Row 4: Botones de figuras y emergencia =====
        self.circle_btn = ttk.Button(
            self.position_frame,
            text="Draw Circle",
            command=self.send_circle_command
        )
        self.circle_btn.grid(row=8, column=0, pady=8, padx=10, sticky='ew')

        self.square_btn = ttk.Button(
            self.position_frame,
            text="Draw Square",
            command=self.send_square_command
        )
        self.square_btn.grid(row=8, column=1, pady=8, padx=10, sticky='ew')

        self.emergency_btn = ttk.Button(
            self.position_frame,
            text="Emergency Stop",
            command=self.send_emergency_stop
        )
        self.emergency_btn.grid(row=8, column=2, pady=8, padx=10, sticky='ew')

        # Configure column weights for even distribution
        for i in range(3):
            self.position_frame.columnconfigure(i, weight=1)

        # ===== Status Frame =====
        self.status_frame = ttk.LabelFrame(
            self.root,
            text="Status",
            padding="15"
        )
        self.status_frame.grid(row=2, column=0, columnspan=3, pady=10, padx=20, sticky='nsew')

        ttk.Label(
            self.status_frame,
            text="Current Status:",
            font=('Arial', 10, 'bold')
        ).grid(row=0, column=0, sticky='w', pady=5)

        self.status_display = ttk.Label(
            self.status_frame,
            text="Ready to receive commands...",
            font=('Arial', 10),
            foreground='blue'
        )
        self.status_display.grid(row=1, column=0, columnspan=3, sticky='w', pady=5)

    def set_pose(self):
        """Handle Set Pose button"""
        try:
            pose_data = {k: float(v.get()) for k, v in self.entries.items()}
            formatted_pose = "\n".join([f"{k}: {v:.3f}" for k, v in pose_data.items()])

            # Create Pose type msg
            msg = Pose()
            msg.position.x = pose_data['x']
            msg.position.y = pose_data['y']
            msg.position.z = pose_data['z']
            # Yaw, pitch y roll aún no se usan en la orientación

            # PUBLICAR pose al topic
            self.pose_pub.publish(msg)

            self.status_display.config(
                text=f"Pose set successfully:\n{formatted_pose}",
                foreground='green'
            )
        except ValueError:
            self.status_display.config(
                text="ERROR: Invalid input. Please enter numeric values only.",
                foreground='red'
            )

    def reset_all(self):
        """Reset all fields"""
        for entry in self.entries.values():
            entry.delete(0, tk.END)
            entry.insert(0, "0.0")

        self.status_display.config(
            text="All fields reset. Ready for new commands...",
            foreground='blue'
        )

    # ===== MÉTODOS PARA ENVIAR COMANDOS DE TEXTO =====
    def send_shape_command(self, shape_name: str, status_text: str, color: str):
        """
        Helper para enviar comandos de forma al topic /xarm/shape_command.
        shape_name es un string sencillo que otros nodos podrán leer.
        """
        msg = String()
        msg.data = shape_name
        self.shape_cmd_pub.publish(msg)
        self.status_display.config(text=status_text, foreground=color)

    def send_circle_command(self):
        """Enviar comando para que el robot dibuje un círculo"""
        self.send_shape_command(
            shape_name="circle",          # <--- string publicado
            status_text="Command sent: circle",
            color='purple'
        )

    def send_square_command(self):
        """Enviar comando para que el robot dibuje un cuadrado"""
        self.send_shape_command(
            shape_name="square",          # <--- string publicado
            status_text="Command sent: square",
            color='purple'
        )

    def send_emergency_stop(self):
        """Enviar comando de parada de emergencia"""
        self.send_shape_command(
            shape_name="stop",            # <--- string publicado
            status_text="EMERGENCY STOP sent to robot! (stop)",
            color='red'
        )

    def run(self):
        """Start the application"""
        self.root.mainloop()


def main():
    app = RobotPositionControlGrid()
    app.run()


if __name__ == "__main__":
    main()
