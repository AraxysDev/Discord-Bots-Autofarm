# Import necessary modules
import asyncio
import threading
import time
import discord
import random
from bots.owo import OwoBot
from bots.virtual_fisher import VirtualFisherBot
import config_manager

# Set bot IDs for OwO Bot and Virtual Fisher Bot
bot_ids = [408785106942164992, 574652751745777665]


class SelfBotClient(discord.Client):
    def __init__(self, framework, *args, **kwargs):
        # Setup framework and initialize client
        super().__init__(*args, **kwargs)
        self.framework = framework

        # Cache commands to prevent API spam
        self.cached_slash_commands = {}

    async def on_ready(self):
        # Alert dashboard of successful login
        self.framework.dashboard_callback(f'Logged in as {self.user.name}')
        self.loop.create_task(self.command_loop())

    async def on_message(self, message):
        # Ignore messages outside of configured channels
        if str(message.channel.id) not in self.framework.channels:
            return

        # Render interception payload directly onto the live feed layout
        if self.framework.dashboard and message.author.id in bot_ids:

            # Reconstruct basic flat dictionaries for attachments and embeds
            serialized_attachments = [a.url for a in message.attachments] if message.attachments else None
            serialized_embeds = []

            if message.embeds:
                for e in message.embeds:
                    embed_payload = {}
                    if e.title: embed_payload['title'] = e.title
                    if e.description: embed_payload['description'] = e.description
                    if e.image and e.image.url: embed_payload['image'] = {'url': e.image.url}
                    serialized_embeds.append(embed_payload)

            # Offload UI manipulation execution into the main layout worker thread
            author_avatar = message.author.avatar.url if message.author.avatar else None
            self.framework.dashboard.feed_frame.after(0, lambda: self.framework.dashboard.render_discord_message(
                message.author.name,
                author_avatar,
                message.content,
                serialized_attachments,
                serialized_embeds
            ))

        # Process messages through active bots
        for bot in self.framework.active_bots:
            if hasattr(bot, 'process_message'):
                await bot.process_message(message)

    async def command_loop(self):
        # Alert dashboard of loop start and channel count
        self.framework.dashboard_callback(f'Started. Cycling between {len(self.framework.channels)} channels.')

        # Process continuous command loop while client is active
        while not self.is_closed():
            if not self.framework.is_running:
                break

            commands_sent_this_tick = False

            # Process commands for each active bot
            for bot in self.framework.active_bots:
                commands_to_send = bot.tick()

                for cmd in commands_to_send:
                    # Rotate through configured channels
                    channel_id = int(self.framework.channels[self.framework.channel_index])
                    self.framework.channel_index = (self.framework.channel_index + 1) % len(self.framework.channels)

                    channel = self.get_channel(channel_id)
                    if channel:
                        try:
                            # Process slash command handling
                            if isinstance(cmd, dict) and cmd.get('type') == 'slash':
                                target_cmd = None
                                target_app_id = str(cmd.get('application_id'))

                                if target_app_id == 'None':
                                    self.framework.dashboard_callback(
                                        f'Error: Command /{cmd["name"]} is missing an application_id.')
                                    continue

                                # Retrieve channel application commands if not cached
                                if channel_id not in self.cached_slash_commands:
                                    self.cached_slash_commands[channel_id] = await channel.application_commands()

                                # Function to match command name and application ID
                                def find_command(cmd_name, app_target, cmd_list):
                                    for slash_cmd in cmd_list:
                                        if slash_cmd.name == cmd_name:
                                            app_id = getattr(slash_cmd, 'application_id', None)
                                            if str(app_id) == app_target:
                                                return slash_cmd
                                    return None

                                # Search for the specific slash command
                                target_cmd = find_command(cmd['name'], target_app_id,
                                                          self.cached_slash_commands[channel_id])

                                # Refresh cache and search again if not found
                                if not target_cmd:
                                    self.cached_slash_commands[channel_id] = await channel.application_commands()
                                    target_cmd = find_command(cmd['name'], target_app_id,
                                                              self.cached_slash_commands[channel_id])

                                # Execute slash command and log the action
                                if target_cmd:
                                    await target_cmd(channel, **cmd.get('kwargs', {}))
                                    cmd_str = f'/{cmd["name"]} {cmd.get("kwargs", {})}'
                                    self.framework.dashboard_callback(
                                        f'[Ch: {str(channel_id)[-4:]}] Sent Slash: {cmd_str}', lb=True)
                                    config_manager.log_command(self.framework.profile_name, bot.name, cmd_str)
                                    commands_sent_this_tick = True
                                else:
                                    self.framework.dashboard_callback(
                                        f'Error: Could not find slash command /{cmd["name"]} for bot ID {target_app_id}.')

                            # Process standard text command handling
                            else:
                                await channel.send(cmd)
                                self.framework.dashboard_callback(f'[Ch: {str(channel_id)[-4:]}] Sent: {cmd}', lb=True)
                                config_manager.log_command(self.framework.profile_name, bot.name, str(cmd))
                                commands_sent_this_tick = True

                            # Process between feature delay matching strategy document
                            await asyncio.sleep(random.uniform(1.0, 3.0))

                        except Exception as e:
                            # Alert dashboard of any transmission errors
                            self.framework.dashboard_callback(f'Error sending to {channel_id}: {e}')

            # Process iteration delay to prevent CPU thrashing
            if not commands_sent_this_tick:
                await asyncio.sleep(random.uniform(1.0, 7.5))


class SelfBotFramework:
    def __init__(self, profile_name, token, settings, dashboard_callback):
        # Setup framework variables and settings
        self.profile_name = profile_name
        self.token = token
        self.settings = settings
        self.dashboard_callback = dashboard_callback

        # Parse and store channel IDs
        raw_channels = settings.get('channel_id', [])
        if isinstance(raw_channels, str):
            self.channels = [c.strip() for c in raw_channels.split(',') if c.strip()]
        else:
            self.channels = [str(c) for c in raw_channels]

        # Initialize connection and loop states
        self.channel_index = 0
        self.is_running = False
        self.loop = None
        self.client = None

        # Setup active bots based on configuration
        self.active_bots = []
        if self.settings.get('enable_owo'):
            self.active_bots.append(OwoBot(self))
        if self.settings.get('enable_vf'):
            self.active_bots.append(VirtualFisherBot(self))

    def start(self):
        # Start the Discord bot in a background thread
        self.is_running = True
        self.thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.thread.start()

    def stop(self):
        # Safely shut down the asyncio loop and client
        self.is_running = False
        self.dashboard_callback('Shutting down Discord client...')

        if self.loop and self.client:
            # Save a local reference to the loop
            loop_ref = self.loop

            asyncio.run_coroutine_threadsafe(self.client.close(), loop_ref)

            def force_kill():
                time.sleep(0.5)
                # Use the local reference to stop the loop
                if loop_ref.is_running():
                    loop_ref.call_soon_threadsafe(loop_ref.stop)

            threading.Thread(target=force_kill, daemon=True).start()

        self.client = None
        self.loop = None

    def _run_async_loop(self):
        # Setup and run the asynchronous event loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self.client = SelfBotClient(self)
        try:
            self.client.run(self.token)
        except Exception as e:
            # Alert dashboard of login failure
            self.dashboard_callback(f'Login Failed. Bad token? Error: {e}')
