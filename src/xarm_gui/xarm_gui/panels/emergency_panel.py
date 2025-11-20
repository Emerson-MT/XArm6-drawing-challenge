import tkinter as tk
from tkinter import ttk

class EmergencyPanel(ttk.LabelFrame):
    def __init__(self, master, on_stop):
        super().__init__(master, text="Emergency", padding="15")

        b = tk.Button(
            self,
            text="STOP",
            bg="red",
            fg="white",
            font=("Arial", 16, "bold"),
            width=10,
            height=3,
            command=on_stop
        )
        b.grid(row=0, column=0, pady=10)
