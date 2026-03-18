class ProgressSectionHelper:
    def __init__(self, app):
        self.app = app

    def update_progress(self, downloaded, total, file_id=None, file_path=None, speed=None, eta=None, status=None):
        self.app.progress_manager.update_progress(
            downloaded, total, file_id, file_path, speed, eta, status=status
        )

    def remove_progress_bar(self, file_id):
        self.app.progress_manager.remove_progress_bar(file_id)

    def update_global_progress(self, completed_files, total_files):
        self.app.progress_manager.update_global_progress(completed_files, total_files)

    def toggle_progress_details(self):
        self.app.progress_manager.toggle_progress_details()

    def center_progress_details_frame(self):
        self.app.progress_manager.center_progress_details_frame()

    def clear_progress_bars(self):
        for file_id in list(self.app.progress_bars.keys()):
            self.remove_progress_bar(file_id)