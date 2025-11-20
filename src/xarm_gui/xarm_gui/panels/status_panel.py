from tkinter import ttk

class StatusPanel(ttk.LabelFrame):
    def __init__(self, master):
        super().__init__(master, text="Status", padding="15")
        ttk.Label(self, text="Status:").grid(row=0, sticky='w')

        self.label = ttk.Label(self, text="Ready", foreground="blue")
        self.label.grid(row=1, sticky='w')

    def update_status(self, msg, color):
        self.label.config(text=msg, foreground=color)
