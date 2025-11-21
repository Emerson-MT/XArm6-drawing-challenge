from tkinter import ttk

class StatusPanel(ttk.LabelFrame):
    def __init__(self, master):
        super().__init__(master, text="Status", padding="15")
        
        # Etiqueta para pose actual
        ttk.Label(self, text="Current Pose:").grid(row=0, sticky='w')
        self.pose_label = ttk.Label(self, text="---", foreground="black")
        self.pose_label.grid(row=3, sticky='w')

        # Etiqueta para Status 
        ttk.Label(self, text="Status:").grid(row=2, sticky='w')
        self.status_label = ttk.Label(self, text="Ready", foreground="blue")
        self.status_label.grid(row=1, sticky='w')

    def update_pose(self, pose_text):
        self.pose_label.config(text=pose_text)
    
    def update_status(self, msg, color):
        self.status_label.config(text=msg, foreground=color)
