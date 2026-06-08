# Import necessary modules
import customtkinter as ctk
from ui_windows import ProfileWindow, SettingsWindow, DashboardWindow
from bot_framework import SelfBotFramework

# Set modern GitHub-style defaults
ctk.set_appearance_mode('dark')
ctk.set_default_color_theme('blue')


class App:
    def __init__(self):
        # Initialize root window and base variables
        self.root = ctk.CTk()
        self.current_window = None
        self.bot_framework = None
        self.show_profiles()

    def show_profiles(self):
        # Clear window and display the profile selection screen
        self._clear_window()
        self.current_window = ProfileWindow(self.root, self.on_profile_selected)

    def on_profile_selected(self, profile_name, profile_data):
        # Clear window and display the settings screen for the selected profile
        self._clear_window()
        self.current_window = SettingsWindow(self.root, profile_name, profile_data, self.on_start_bot)

    def on_start_bot(self, profile_name, token, settings):
        # Clear window to prepare for dashboard rendering
        self._clear_window()

        # Create a function to handle returning to the settings screen
        def go_back():
            if self.bot_framework:
                self.bot_framework.stop()

            # Pass the data back as a dictionary just like the profile selector does
            self.on_profile_selected(profile_name, {'token': token, 'settings': settings})

        # Pass the callback function to the DashboardWindow
        self.dashboard_ui = DashboardWindow(self.root, None, go_back)

        def log_to_dashboard(msg, **kwargs):
            self.root.after(0, lambda: self.dashboard_ui.log(msg, **kwargs))

        log_to_dashboard(f'Connecting to {profile_name}...')

        # Initialize Framework with selected profile details
        self.bot_framework = SelfBotFramework(profile_name, token, settings, log_to_dashboard)

        # Attach framework to dashboard and start execution loops
        self.dashboard_ui.bot_framework = self.bot_framework
        self.dashboard_ui.start_dashboard_loop()
        self.bot_framework.start()

    def _clear_window(self):
        # Destroy all active widgets within the root window
        for widget in self.root.winfo_children():
            widget.destroy()

    def run(self):
        # Bind closing protocol and start main application loop
        self.root.protocol('WM_DELETE_WINDOW', self.on_closing)
        self.root.mainloop()

    def on_closing(self):
        # Stop the bot framework safely before destroying the root window
        if self.bot_framework:
            self.bot_framework.stop()
        self.root.destroy()


if __name__ == '__main__':
    # Instantiate and run the application
    app = App()
    app.run()
