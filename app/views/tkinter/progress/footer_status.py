class FooterStatusController:
    def __init__(self, speed_label, eta_label):
        self.speed_label = speed_label
        self.eta_label = eta_label

    def set_speed(self, speed_text: str):
        if self.speed_label and self.speed_label.winfo_exists():
            self.speed_label.configure(text=speed_text)

    def set_eta(self, eta_text: str):
        if self.eta_label and self.eta_label.winfo_exists():
            self.eta_label.configure(text=eta_text)

    def set_status(self, status_text: str, duration_ms: int = 5000):
        if not self.eta_label or not self.eta_label.winfo_exists():
            return

        original = self.eta_label.cget("text")
        base_eta = original.split(" | ")[0]
        self.eta_label.configure(text=f"{base_eta} | STATUS:{status_text}")
        self.eta_label.after(duration_ms, lambda: self._restore_eta(base_eta))

    def reset(self):
        if self.speed_label and self.speed_label.winfo_exists():
            self.speed_label.configure(text="Speed: 0 KB/s")

        if self.eta_label and self.eta_label.winfo_exists():
            self.eta_label.configure(text="ETA: N/A")

    def _restore_eta(self, eta_text: str):
        if self.eta_label and self.eta_label.winfo_exists():
            self.eta_label.configure(text=eta_text)