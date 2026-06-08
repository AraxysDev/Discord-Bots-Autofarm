import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import config_manager
from datetime import datetime
import threading
import asyncio
import time
import message_renderer
import discord
from bots.owo import OwoBot
from bots.virtual_fisher import VirtualFisherBot


class ProfileWindow:
    def __init__(self, master, on_profile_selected):
        # Setup window properties
        self.master = master
        self.master.title('Phobos Client - Profiles')
        self.master.geometry('500x400')

        # Configure dark theme properties
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')
        self.bg = '#0d1117'
        self.widget_bg = '#161b22'
        self.accent = '#da3633'
        self.accent_hover = '#b62324'
        self.master.configure(fg_color=self.bg)

        # Handle callback initialization
        self.on_profile_selected = on_profile_selected

        # Initialize configurations
        config_manager.ensure_config_exists()
        self.config = config_manager.load_config()

        # Display screen header title
        ctk.CTkLabel(
            self.master, text='Select or Create Profile',
            font=('Roboto', 20, 'bold'), text_color='#f0f6fc'
        ).pack(pady=(20, 10))

        # Create profile list layout wrapper
        list_container = ctk.CTkFrame(
            self.master, width=300, height=150,
            fg_color=self.widget_bg, border_color=self.accent, border_width=2
        )
        list_container.pack(pady=10, padx=20, fill='both', expand=True)

        # Setup scrollable structure for multi-profile views
        self.profile_frame = ctk.CTkScrollableFrame(
            list_container, fg_color=self.widget_bg, corner_radius=0
        )
        self.profile_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # Parse profile mapping details
        profile_names = list(self.config.get('profiles', {}).keys())

        # Establish fallbacks for empty profiles
        default_profile = profile_names[0] if profile_names else ''

        # Populate internal choices layout components
        self.profile_var = ctk.StringVar(value=default_profile)
        for profile in self.config.get('profiles', {}):
            rb = ctk.CTkRadioButton(
                self.profile_frame, text=profile,
                variable=self.profile_var, value=profile,
                fg_color=self.accent, hover_color=self.accent_hover,
                border_color=self.accent, text_color='#c9d1d9'
            )
            rb.pack(pady=5, anchor='w', padx=20)

        # Render navigational action buttons controls
        btn_frame = ctk.CTkFrame(self.master, fg_color='transparent')
        btn_frame.pack(pady=10)

        ctk.CTkButton(
            btn_frame, text='Create New',
            fg_color=self.accent, hover_color=self.accent_hover,
            font=('Roboto', 13, 'bold'),
            command=self.create_profile
        ).pack(side='left', padx=10)

        ctk.CTkButton(
            btn_frame, text='Select Profile',
            fg_color=self.accent, hover_color=self.accent_hover,
            font=('Roboto', 13, 'bold'),
            command=self.select_profile
        ).pack(side='left', padx=10)

        # Bring window visibility to focus
        self.master.lift()
        self.master.focus_force()

    def select_profile(self):
        # Process and submit selection validation triggers
        profile_name = self.profile_var.get()
        if not profile_name:
            messagebox.showwarning('Error', 'Please select a profile.')
            return
        self.on_profile_selected(profile_name, self.config['profiles'][profile_name])

    def create_profile(self):
        # Open profile creator top layer popup window
        self.new_window = ctk.CTkToplevel(self.master)
        self.new_window.title('New Profile')
        self.new_window.geometry('400x300')
        self.new_window.attributes('-topmost', True)

        # Inherit main backdrop styles
        self.new_window.configure(fg_color=self.bg)

        # Render layout elements inside user profile setup box
        ctk.CTkLabel(
            self.new_window, text='Profile Name:',
            text_color='#c9d1d9', font=('Roboto', 14, 'bold')
        ).pack(pady=(20, 5))
        name_entry = ctk.CTkEntry(
            self.new_window, width=250,
            fg_color=self.widget_bg, border_color=self.accent,
            text_color='white'
        )
        name_entry.pack(pady=5)

        ctk.CTkLabel(
            self.new_window, text='Discord Token:',
            text_color='#c9d1d9', font=('Roboto', 14, 'bold')
        ).pack(pady=(10, 5))
        token_entry = ctk.CTkEntry(
            self.new_window, width=250, show='*',
            fg_color=self.widget_bg, border_color=self.accent,
            text_color='white'
        )
        token_entry.pack(pady=5)

        def save_new():
            # Apply and serialize freshly added user profiles data
            name = name_entry.get()
            token = token_entry.get()
            if name and token:
                default_settings = {
                    'channel_id': '',
                    'enable_owo': False,
                    'owo_settings': {
                        'auto_hunt': True,
                        'auto_battle': True,
                        'auto_daily': True,
                        'auto_cookie': False,
                        'auto_pray': False,
                        'auto_pets': False,
                        'auto_sleep': False,
                        'auto_lootbox': False,
                        'auto_crate': False,
                        'auto_gem': None
                    },
                    'owo_state': {},
                    'enable_vf': False,
                    'vf_settings': {
                        'auto_fish': True,
                        'auto_daily': True,
                        'auto_type': None,
                        'auto_sleep': False,
                        'fish_bait': None,
                        'treasure_bait': None
                    },
                    'vf_state': {}
                }
                config_manager.update_profile(name, token, default_settings)

                # Dynamically append choice option elements into view
                ctk.CTkRadioButton(
                    self.profile_frame, text=name,
                    variable=self.profile_var, value=name,
                    fg_color=self.accent, hover_color=self.accent_hover,
                    border_color=self.accent, text_color='#c9d1d9'
                ).pack(pady=5, anchor='w', padx=20)
                self.config = config_manager.load_config()
                self.new_window.destroy()

        # Place confirmation buttons widgets
        ctk.CTkButton(
            self.new_window, text='Save',
            fg_color=self.accent, hover_color=self.accent_hover,
            font=('Roboto', 14, 'bold'),
            command=save_new
        ).pack(pady=20)


class SettingsWindow:
    def __init__(self, master, profile_name, profile_data, on_start):
        # Initialize primary application settings window view panel context
        self.master = master
        self.master.title(f'Settings - {profile_name}')
        self.master.geometry('700x780')

        # Configure standardized theme colors variables
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')
        self.bg = '#0d1117'
        self.widget_bg = '#161b22'
        self.accent = '#da3633'
        self.accent_hover = '#b62324'
        self.text_primary = '#f0f6fc'
        self.text_secondary = '#c9d1d9'
        self.master.configure(fg_color=self.bg)

        # Store profile operational metadata definitions
        self.profile_name = profile_name
        self.token = profile_data['token']
        self.settings = profile_data.get('settings', {})
        self.on_start = on_start

        # Render clean vertical content scrolling context panels
        self.main_scroll = ctk.CTkScrollableFrame(
            self.master, fg_color='transparent'
        )
        self.main_scroll.pack(fill='both', expand=True, padx=10, pady=10)

        # Hide default native scrollbars cleanly from direct sight lines
        self.main_scroll._scrollbar.grid_forget()

        # Embed interface header display string
        ctk.CTkLabel(
            self.main_scroll, text=f'Configure Bots for {profile_name}',
            font=('Roboto', 20, 'bold'), text_color=self.accent
        ).pack(pady=15)

        # Render targets channels interactive processing controls layout fields
        ctk.CTkLabel(
            self.main_scroll, text='Target Channel IDs (comma separated):',
            font=('Roboto', 14), text_color=self.text_secondary
        ).pack()
        self.channel_entry = ctk.CTkEntry(
            self.main_scroll, width=500,
            placeholder_text='e.g., 123456789, 987654321',
            fg_color=self.widget_bg, border_color=self.accent,
            text_color='white'
        )
        self.channel_entry.pack(pady=5)

        # Fetch and verify existing layout information streams mapping keys
        saved_channels = self.settings.get('channel_id', '')
        if isinstance(saved_channels, list):
            saved_channels = ', '.join(saved_channels)
        self.channel_entry.insert(0, saved_channels)

        # Build clean stylized separators borders across segments
        sep1 = ctk.CTkFrame(self.main_scroll, height=2, fg_color=self.accent)
        sep1.pack(fill='x', padx=30, pady=(15, 5))

        # ============== OWO BOT INTERACTION SECTIONS ==============
        self.owo_var = tk.BooleanVar(value=self.settings.get('enable_owo', False))
        owo_switch = ctk.CTkSwitch(
            self.main_scroll, text='OwO Bot', variable=self.owo_var,
            font=('Roboto', 14, 'bold'),
            progress_color=self.accent, button_color=self.accent,
            button_hover_color=self.accent_hover
        )
        owo_switch.pack(pady=(10, 5))

        # Configure outer card accent panel details boundaries elements
        border_bg_owo = ctk.CTkFrame(
            self.main_scroll, fg_color=self.accent,
            corner_radius=10
        )
        border_bg_owo.pack(fill='x', padx=40, pady=5)

        # Embed internal settings alignment components box frames safely
        owo_frame = ctk.CTkFrame(
            border_bg_owo, fg_color=self.widget_bg,
            corner_radius=8
        )
        owo_frame.pack(fill='both', expand=True, padx=2, pady=2)

        owo_s = self.settings.get('owo_settings', {})

        # Track functional toggles variables states safely
        self.owo_hunt_var = tk.BooleanVar(value=owo_s.get('auto_hunt', True))
        self.owo_battle_var = tk.BooleanVar(value=owo_s.get('auto_battle', True))
        self.owo_daily_var = tk.BooleanVar(value=owo_s.get('auto_daily', True))
        self.owo_cookie_var = tk.BooleanVar(value=owo_s.get('auto_cookie', False))
        self.owo_pray_var = tk.BooleanVar(value=owo_s.get('auto_pray', False))
        self.owo_pets_var = tk.BooleanVar(value=owo_s.get('auto_pets', False))

        self.owo_sleep_var = tk.BooleanVar(value=owo_s.get('auto_sleep', False))
        self.owo_lootbox_var = tk.BooleanVar(value=owo_s.get('auto_lootbox', False))
        self.owo_crate_var = tk.BooleanVar(value=owo_s.get('auto_crate', False))

        # Track strategic drop down strings variables fields values
        self.owo_autogem_choice = ctk.StringVar(value=owo_s.get('auto_gem') or 'None')

        # Construct horizontal checkbox choice layouts rows - Sequence 1
        r1 = ctk.CTkFrame(owo_frame, fg_color='transparent')
        r1.pack(fill='x', pady=5)
        ctk.CTkCheckBox(
            r1, text='Auto Hunt', variable=self.owo_hunt_var,
            fg_color=self.accent, border_color=self.accent,
            checkmark_color='white', text_color=self.text_secondary
        ).pack(side='left', padx=20)
        ctk.CTkCheckBox(
            r1, text='Auto Battle', variable=self.owo_battle_var,
            fg_color=self.accent, border_color=self.accent,
            checkmark_color='white', text_color=self.text_secondary
        ).pack(side='left', padx=20)
        ctk.CTkCheckBox(
            r1, text='Auto Daily', variable=self.owo_daily_var,
            fg_color=self.accent, border_color=self.accent,
            checkmark_color='white', text_color=self.text_secondary
        ).pack(side='left', padx=20)

        # Construct horizontal checkbox choice layouts rows - Sequence 2
        r2 = ctk.CTkFrame(owo_frame, fg_color='transparent')
        r2.pack(fill='x', pady=5)
        ctk.CTkCheckBox(
            r2, text='Auto Cookie', variable=self.owo_cookie_var,
            fg_color=self.accent, border_color=self.accent,
            checkmark_color='white', text_color=self.text_secondary
        ).pack(side='left', padx=20)
        ctk.CTkCheckBox(
            r2, text='Auto Pray', variable=self.owo_pray_var,
            fg_color=self.accent, border_color=self.accent,
            checkmark_color='white', text_color=self.text_secondary
        ).pack(side='left', padx=20)
        ctk.CTkCheckBox(
            r2, text='Auto Pets', variable=self.owo_pets_var,
            fg_color=self.accent, border_color=self.accent,
            checkmark_color='white', text_color=self.text_secondary
        ).pack(side='left', padx=20)

        # Construct horizontal checkbox choice layouts rows - Sequence 3
        r3 = ctk.CTkFrame(owo_frame, fg_color='transparent')
        r3.pack(fill='x', pady=5)
        ctk.CTkCheckBox(
            r3, text='Auto Sleep', variable=self.owo_sleep_var,
            fg_color=self.accent, border_color=self.accent,
            checkmark_color='white', text_color=self.text_secondary
        ).pack(side='left', padx=20)
        ctk.CTkCheckBox(
            r3, text='Auto Lootbox', variable=self.owo_lootbox_var,
            fg_color=self.accent, border_color=self.accent,
            checkmark_color='white', text_color=self.text_secondary
        ).pack(side='left', padx=20)
        ctk.CTkCheckBox(
            r3, text='Auto Crates', variable=self.owo_crate_var,
            fg_color=self.accent, border_color=self.accent,
            checkmark_color='white', text_color=self.text_secondary
        ).pack(side='left', padx=20)

        # Configure automation selection dropdown widgets layout frames blocks
        ctk.CTkLabel(
            owo_frame, text='Auto Gem Strategy:', font=('Roboto', 12, 'bold'),
            text_color=self.accent
        ).pack(anchor='w', padx=20, pady=(10, 0))
        ag_combo = ctk.CTkComboBox(
            owo_frame, values=['None', 'Rarity low to high', 'Rarity high to low'],
            variable=self.owo_autogem_choice,
            width=180,
            fg_color=self.widget_bg, border_color=self.accent,
            button_color=self.accent, button_hover_color=self.accent_hover,
            dropdown_fg_color=self.widget_bg, dropdown_text_color='white',
            dropdown_hover_color=self.accent_hover
        )
        ag_combo.pack(padx=20, pady=(5, 10), anchor='w')

        # Embed a secondary section separation break element layer
        sep2 = ctk.CTkFrame(self.main_scroll, height=2, fg_color=self.accent)
        sep2.pack(fill='x', padx=30, pady=(15, 5))

        # ============== VIRTUAL FISHER SETUP INTERFACES ==============
        self.vf_var = tk.BooleanVar(value=self.settings.get('enable_vf', False))
        vf_switch = ctk.CTkSwitch(
            self.main_scroll, text='Virtual Fisher', variable=self.vf_var,
            font=('Roboto', 14, 'bold'),
            progress_color=self.accent, button_color=self.accent,
            button_hover_color=self.accent_hover
        )
        vf_switch.pack(pady=(10, 5))

        # Generate external matching container card layout frame
        border_bg_vf = ctk.CTkFrame(
            self.main_scroll, fg_color=self.accent,
            corner_radius=10
        )
        border_bg_vf.pack(fill='x', padx=40, pady=5)

        # Append structured content mapping display frame blocks safely
        vf_frame = ctk.CTkFrame(
            border_bg_vf, fg_color=self.widget_bg,
            corner_radius=8
        )
        vf_frame.pack(fill='both', expand=True, padx=2, pady=2)
        vf_s = self.settings.get('vf_settings', {})

        # Standardize parameter checkbox tracker configuration definitions
        self.vf_fish_var = tk.BooleanVar(value=vf_s.get('auto_fish', True))
        self.vf_daily_var = tk.BooleanVar(value=vf_s.get('auto_daily', True))
        self.vf_sleep_var = tk.BooleanVar(value=vf_s.get('auto_sleep', False))

        cmd_row = ctk.CTkFrame(vf_frame, fg_color='transparent')
        cmd_row.pack(fill='x', pady=(10, 5))
        ctk.CTkCheckBox(
            cmd_row, text='Auto /fish', variable=self.vf_fish_var,
            fg_color=self.accent, border_color=self.accent,
            checkmark_color='white', text_color=self.text_secondary
        ).pack(side='left', padx=20)
        ctk.CTkCheckBox(
            cmd_row, text='Auto /daily', variable=self.vf_daily_var,
            fg_color=self.accent, border_color=self.accent,
            checkmark_color='white', text_color=self.text_secondary
        ).pack(side='left', padx=20)
        ctk.CTkCheckBox(
            cmd_row, text='Auto Sleep', variable=self.vf_sleep_var,
            fg_color=self.accent, border_color=self.accent,
            checkmark_color='white', text_color=self.text_secondary
        ).pack(side='left', padx=20)

        # Map current values strings into combo drop menu controls references variables
        self.auto_fish_choice = ctk.StringVar(value=vf_s.get('auto_type') or 'None')
        self.fish_bait_choice = ctk.StringVar(value=vf_s.get('fish_bait') or 'None')
        self.treasure_bait_choice = ctk.StringVar(value=vf_s.get('treasure_bait') or 'None')

        # Establish buff combo interface configuration parameters views - Setup 1
        ctk.CTkLabel(
            vf_frame, text='Auto Fish Buff:', font=('Roboto', 12, 'bold'),
            text_color=self.accent
        ).pack(anchor='w', padx=20, pady=(10, 0))
        af_combo = ctk.CTkComboBox(
            vf_frame, values=['None', 'Auto10m', 'Auto30m'],
            variable=self.auto_fish_choice,
            fg_color=self.widget_bg, border_color=self.accent,
            width=180,
            button_color=self.accent, button_hover_color=self.accent_hover,
            dropdown_fg_color=self.widget_bg, dropdown_text_color='white',
            dropdown_hover_color=self.accent_hover
        )
        af_combo.pack(padx=20, pady=5, anchor='w')

        # Establish buff combo interface configuration parameters views - Setup 2
        ctk.CTkLabel(
            vf_frame, text='Fish Bait Buff:', font=('Roboto', 12, 'bold'),
            text_color=self.accent
        ).pack(anchor='w', padx=20, pady=(10, 0))
        fb_combo = ctk.CTkComboBox(
            vf_frame, values=['None', 'Fish5m', 'Fish20m'],
            width=180,
            fg_color=self.widget_bg, border_color=self.accent,
            button_color=self.accent, button_hover_color=self.accent_hover,
            dropdown_fg_color=self.widget_bg, dropdown_text_color='white',
            dropdown_hover_color=self.accent_hover
        )
        fb_combo.pack(padx=20, pady=5, anchor='w')

        # Establish buff combo interface configuration parameters views - Setup 3
        ctk.CTkLabel(
            vf_frame, text='Treasure Bait Buff:', font=('Roboto', 12, 'bold'),
            text_color=self.accent
        ).pack(anchor='w', padx=20, pady=(10, 0))
        tb_combo = ctk.CTkComboBox(
            vf_frame, values=['None', 'Treasure5m', 'Treasure20m'],
            width=180,
            variable=self.treasure_bait_choice,
            fg_color=self.widget_bg, border_color=self.accent,
            button_color=self.accent, button_hover_color=self.accent_hover,
            dropdown_fg_color=self.widget_bg, dropdown_text_color='white',
            dropdown_hover_color=self.accent_hover
        )
        tb_combo.pack(padx=20, pady=(5, 10), anchor='w')

        # Setup runtime execution trigger buttons widget configurations
        ctk.CTkButton(
            self.main_scroll, text='Save & Start Autofarm',
            fg_color=self.accent, hover_color=self.accent_hover,
            font=('Roboto', 16, 'bold'), height=40,
            command=self.save_and_start
        ).pack(pady=25)

    def save_and_start(self):
        # Format user inputted strings channels mappings structures lists cleanly
        raw_channels = self.channel_entry.get()
        channel_list = [c.strip() for c in raw_channels.split(',') if c.strip()]

        af_val = self.auto_fish_choice.get()
        fb_val = self.fish_bait_choice.get()
        tb_val = self.treasure_bait_choice.get()

        # Extract selected drop items strategies values definitions
        ag_val = self.owo_autogem_choice.get()

        # Build dynamic configurations state mapping definitions dictionary keys
        new_settings = {
            'channel_id': channel_list,
            'enable_owo': self.owo_var.get(),
            'owo_settings': {
                'auto_hunt': self.owo_hunt_var.get(),
                'auto_battle': self.owo_battle_var.get(),
                'auto_daily': self.owo_daily_var.get(),
                'auto_cookie': self.owo_cookie_var.get(),
                'auto_pray': self.owo_pray_var.get(),
                'auto_pets': self.owo_pets_var.get(),
                'auto_sleep': self.owo_sleep_var.get(),
                'auto_lootbox': self.owo_lootbox_var.get(),
                'auto_crate': self.owo_crate_var.get(),
                'auto_gem': None if ag_val == 'None' else ag_val
            },
            'owo_state': self.settings.get('owo_state', {}),

            'enable_vf': self.vf_var.get(),
            'vf_settings': {
                'auto_fish': self.vf_fish_var.get(),
                'auto_daily': self.vf_daily_var.get(),
                'auto_type': None if af_val == 'None' else af_val,
                'auto_sleep': self.vf_sleep_var.get(),
                'fish_bait': None if fb_val == 'None' else fb_val,
                'treasure_bait': None if tb_val == 'None' else tb_val
            },
            'vf_state': self.settings.get('vf_state', {})
        }

        # Update disk file mappings configurations rules and invoke start engine triggers
        config_manager.update_profile(self.profile_name, self.token, new_settings)
        self.on_start(self.profile_name, self.token, new_settings)


class DashboardWindow:
    def __init__(self, master, bot_framework, go_back_callback):
        # Configure layout properties data records parameters trackers
        self.master = master
        self.master.title('Live Dashboard')
        self.master.geometry('850x750')
        self.bot_framework = bot_framework
        self.go_back_callback = go_back_callback

        # Verify tracking framework mappings contexts connections
        if self.bot_framework:
            self.bot_framework.dashboard = self

        # Display dashboard panel status headers
        ctk.CTkLabel(self.master, text='Autofarm Live Progress', font=('Roboto', 24, 'bold')).pack(pady=15)

        # Build clean real time activity notification display textbox
        self.log_text = ctk.CTkTextbox(self.master, height=120, width=750, fg_color='#0d1117', text_color='#c9d1d9')
        self.log_text.pack(pady=5)

        # Embed operational shutdown abort controllers switches variables
        ctk.CTkButton(self.master, text='Stop & Return to Settings', fg_color='#da3633', hover_color='#b62324',
                      font=('Roboto', 14, 'bold'), command=self.stop_bot).pack(pady=5)

        # Append separate secondary intercepted streams sections titles labels
        ctk.CTkLabel(self.master, text='Live Discord Intercept Feed', font=('Roboto', 14, 'bold'),
                     text_color='#58a6ff').pack(pady=(10, 2))

        # Build clean dynamic scroll targets wrappers for output feeds text payloads
        self.feed_frame = ctk.CTkScrollableFrame(self.master, width=750, height=380, fg_color='#313338',
                                                 corner_radius=8)
        self.feed_frame.pack(pady=5, fill='both', expand=True, padx=40)

        # Track and keep images asset records local references mappings cached
        self.image_cache = {}

    def start_dashboard_loop(self):
        # Fire monitoring loop validation checks configurations
        self.update_dashboard()

    def log(self, message, lb=False):
        # Handle string message log additions onto target visual display boards safe layers
        if hasattr(self, 'log_text') and self.log_text.winfo_exists():
            self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n" + ('\n' if lb else ''))
            self.log_text.see(tk.END)

    def render_discord_message(self, author_name, author_avatar_url, content, attachments=None, embeds=None):
        # Call abstract visual module engine renderer methods components to draw feeds elements
        message_renderer.render_discord_message(
            self,
            author_name,
            author_avatar_url,
            content,
            attachments,
            embeds
        )

    def update_dashboard(self):
        # Keep background data loops pipelines context maps current safely
        if self.bot_framework:
            self.bot_framework.dashboard = self
            if self.bot_framework.is_running:
                self.master.after(2000, self.update_dashboard)

    def stop_bot(self):
        # Shutdown runtime activity processors frameworks and return focus cleanly back
        if self.bot_framework:
            self.bot_framework.stop()
        self.log('Operations halted. Returning to settings...')
        self.bot_framework = None
        self.master.after(1000, self.go_back_callback)


class SelfBotClient(discord.Client):
    def __init__(self, framework, *args, **kwargs):
        # Set up framework properties hooks safely onto discord clients context definitions
        super().__init__(*args, **kwargs)
        self.framework = framework

    async def on_ready(self):
        # Report back layout connection confirmations states cleanly
        self.framework.dashboard_callback(f'Logged in as {self.user.name}')
        self.loop.create_task(self.command_loop())

    async def on_message(self, message):
        # Drop and discard tracking signals from foreign unrelated discord data slots channels
        if str(message.channel.id) not in self.framework.channels:
            return

        # Core hook: Render interception payload directly onto the live feed layout
        if self.framework.dashboard:
            # Reconstruct basic flat dictionaries representing attachments and embed payloads
            serialized_attachments = [a.url for a in message.attachments] if message.attachments else None
            serialized_embeds = []
            if message.embeds:
                for e in message.embeds:
                    embed_payload = {}
                    if e.title:
                        embed_payload['title'] = e.title
                    if e.description:
                        embed_payload['description'] = e.description
                    if e.image and e.image.url:
                        embed_payload['image'] = {'url': e.image.url}
                    serialized_embeds.append(embed_payload)

            # Offload UI manipulation execution directly into main layout worker thread safely
            self.framework.dashboard.feed_frame.after(0, lambda: self.framework.dashboard.render_discord_message(
                message.author.name,
                message.author.avatar.url if message.author.avatar else None,
                message.content,
                attachments=serialized_attachments,
                embeds=serialized_embeds if serialized_embeds else None
            ))

        # Push payload objects information safely down to targeted backend bots loops configurations
        for bot in self.framework.active_bots:
            if hasattr(bot, 'process_message'):
                await bot.process_message(message)

    async def command_loop(self):
        # Spin up main core background asynchronous processing task execution routines
        self.framework.dashboard_callback(f'Started. Cycling between {len(self.framework.channels)} channels.')
        while not self.is_closed():
            if not self.framework.is_running:
                break

            # Poll active child processing scripts automation steps rules definitions safely
            for bot in self.framework.active_bots:
                commands_to_send = bot.tick()
                for cmd in commands_to_send:
                    channel_id = int(self.framework.channels[self.framework.channel_index])
                    self.framework.channel_index = (self.framework.channel_index + 1) % len(self.framework.channels)
                    channel = self.get_channel(channel_id)
                    if channel:
                        try:
                            await channel.send(cmd)
                            self.framework.dashboard_callback(f"[Ch: {str(channel_id)[-4:]}] Sent: {cmd}")
                            config_manager.log_command(self.framework.profile_name, bot.name, cmd)
                            await asyncio.sleep(4)
                        except Exception as e:
                            self.framework.dashboard_callback(f'Error sending to {channel_id}: {e}')
            await asyncio.sleep(0.5)


class SelfBotFramework:
    def __init__(self, profile_name, token, settings, dashboard_callback):
        # Store automation environment profile configurations references properties fields keys
        self.profile_name = profile_name
        self.token = token
        self.settings = settings
        self.dashboard_callback = dashboard_callback
        self.dashboard = None

        # Build channels parsing filters rules variables mapping logic structures cleanly
        raw_channels = settings.get('channel_id', [])
        if isinstance(raw_channels, str):
            self.channels = [c.strip() for c in raw_channels.split(',') if c.strip()]
        else:
            self.channels = [str(c) for c in raw_channels]

        self.channel_index = 0
        self.is_running = False
        self.loop = None
        self.client = None

        # Conditionally map backend sub-bot processing scripts units safely from parameters records
        self.active_bots = []
        if self.settings.get('enable_owo'):
            self.active_bots.append(OwoBot(self))
        if self.settings.get('enable_vf'):
            self.active_bots.append(VirtualFisherBot(self))

    def start(self):
        # Activate processing execution tasks cleanly alongside separate thread operations layouts
        self.is_running = True
        self.thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.thread.start()

    def stop(self):
        # Command active engine systems sequences closures operations directly
        self.is_running = False
        self.dashboard_callback('Shutting down Discord client...')
        if self.loop and self.client:
            asyncio.run_coroutine_threadsafe(self.client.close(), self.loop)

            def force_kill():
                time.sleep(0.5)
                if self.loop.is_running():
                    self.loop.call_soon_threadsafe(self.loop.stop)

            threading.Thread(target=force_kill, daemon=True).start()
        self.client = None
        self.loop = None

    def _run_async_loop(self):
        # Configure internal thread task runner loops structures cleanly below safely
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.client = SelfBotClient(self)
        try:
            self.client.run(self.token)
        except Exception as e:
            self.dashboard_callback(f'Login Failed: {e}')
