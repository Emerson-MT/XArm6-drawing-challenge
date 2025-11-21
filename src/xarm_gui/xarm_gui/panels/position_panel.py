import tkinter as tk
from tkinter import ttk

class PositionControlPanel(ttk.LabelFrame):
    def __init__(self, master, on_set_pose, on_reset, on_circle, on_square):
        super().__init__(master, text="Position Control", padding="20")

        self.on_set_pose = on_set_pose

        # Entradas
        axes = ["x", "y", "z", "yaw", "pitch", "roll"]
        self.entries = {}

        for i, ax in enumerate(axes):
            ttk.Label(self, text=ax.upper()).grid(row=0, column=i)
            entry = ttk.Entry(self, width=10, justify="center")
            entry.insert(0, "0.0")
            entry.grid(row=1, column=i, padx=5)
            self.entries[ax] = entry

        # Botones principales
        ttk.Button(self, text="Set Pose", command=self._call_set).grid(
            row=2, column=0, columnspan=2, sticky='ew', pady=10
        )

        ttk.Button(self, text="Reset", command=on_reset).grid(
            row=2, column=2, sticky='ew', pady=10
        )

        ttk.Button(self, text="Circle", command=on_circle).grid(
            row=2, column=3, sticky='ew', pady=10
        )

        ttk.Button(self, text="Square", command=on_square).grid(
            row=2, column=4, sticky='ew', pady=10
        )

    def _call_set(self):
        #pose = {k: float(v.get()) for k, v in self.entries.items()}
        self.on_set_pose()
