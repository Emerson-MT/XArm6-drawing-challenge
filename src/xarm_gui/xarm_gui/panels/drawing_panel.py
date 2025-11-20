import tkinter as tk
from tkinter import ttk
from xarm_gui.utils.path_discretizer import discretize_path

class DrawingPanel(ttk.LabelFrame):
    def __init__(self, master, on_send_path, width=500, height=500):
        super().__init__(master, text="Drawing Canvas", padding="10")

        self.on_send_path = on_send_path
        self.points = []

        self.canvas = tk.Canvas(self, bg="white", width=width, height=height)
        self.canvas.grid(row=0, column=0, columnspan=3)

        self.canvas.bind("<Button-1>", self._start)
        self.canvas.bind("<B1-Motion>", self._draw)

        ttk.Button(self, text="Send Path", command=self._send).grid(
            row=1, column=0, sticky='ew', pady=10
        )

        ttk.Button(self, text="Clear", command=self._clear).grid(
            row=1, column=1, sticky='ew', pady=10
        )

    def _start(self, e):
        self.points.append((e.x, e.y))

    def _draw(self, e):
        last = self.points[-1]
        self.canvas.create_line(last[0], last[1], e.x, e.y)
        self.points.append((e.x, e.y))

    def _send(self):
        if not self.points:
            return

        path = discretize_path(self.points, step=10)
        self.on_send_path(path)

    def _clear(self):
        self.canvas.delete("all")
        self.points.clear()
