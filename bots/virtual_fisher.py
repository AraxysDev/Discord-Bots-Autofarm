# Import necessary modules
import time
import random
from datetime import datetime
import config_manager


class VirtualFisherBot:
    def __init__(self, framework):
        # Setup framework and retrieve settings
        self.name = 'virtual_fisher'
        self.framework = framework
        self.settings = framework.settings.get('vf_settings', {})

        # Set the ID for the Virtual Fisher bot
        self.bot_id = '574652751745777665'

        # Load persistent state or create an empty one
        self.state = framework.settings.get('vf_state', {})

        # Setup base command toggles
        self.do_fish = self.settings.get('auto_fish', True)
        self.do_daily = self.settings.get('auto_daily', True)

        # Setup execution trackers for persistence
        self.next_run_fish = self.state.get('next_run_fish', 0)
        self.next_run_daily = self.state.get('next_run_daily', 0)

        # Setup expiration trackers
        self.auto_fish_expires = self.state.get('auto_fish_expires', 0)
        self.fish_bait_expires = self.state.get('fish_bait_expires', 0)
        self.treasure_bait_expires = self.state.get('treasure_bait_expires', 0)

        # Setup target items for baits and boosters
        self.auto_type = self.settings.get('auto_type', None)
        self.fish_bait = self.settings.get('fish_bait', None)
        self.treasure_bait = self.settings.get('treasure_bait', None)

        # Setup auto-sleep trackers
        self.commands_ran = self.state.get('commands_ran', 0)
        self.sleep_until = self.state.get('sleep_until', 0)
        self.sleep_target = self.state.get('sleep_target', random.randint(80, 250))

    def _get_proportional_sleep(self, commands_ran):
        # Set minimum and maximum commands and sleep durations
        min_cmds, max_cmds = 80.0, 250.0
        min_sleep, max_sleep = 600.0, 4320.0

        # Calculate proportion of commands ran
        proportion = (commands_ran - min_cmds) / (max_cmds - min_cmds)
        proportion = max(0.0, min(1.0, proportion))

        # Calculate base sleep time
        base_sleep = min_sleep + (proportion * (max_sleep - min_sleep))

        # Add randomization jitter to sleep
        jittered_sleep = random.uniform(base_sleep * 0.9, base_sleep * 1.1)

        # Return duration bounded by max sleep
        return min(jittered_sleep, max_sleep)

    def tick(self):
        # Get the current time
        now = time.time()

        # Check if the bot is currently sleeping
        if self.settings.get('auto_sleep') and now < self.sleep_until:
            return []

        # Initialize commands list and state flag
        commands = []
        state_changed = False

        # Process daily command
        if self.do_daily and (now > self.next_run_daily):
            commands.append({'type': 'slash', 'name': 'daily', 'application_id': self.bot_id, 'kwargs': {}})
            self.next_run_daily = now + random.randint(12600, 13800)
            state_changed = True

        # Process auto fish booster
        elif self.auto_type and (now >= self.auto_fish_expires):
            commands.append(
                {'type': 'slash', 'name': 'buy', 'application_id': self.bot_id, 'kwargs': {'item': self.auto_type}})
            duration = 600 if '10m' in self.auto_type else 1800
            self.auto_fish_expires = now + duration + random.randint(300, 360)
            state_changed = True

        # Process fish booster
        elif self.fish_bait and (now >= self.fish_bait_expires):
            commands.append(
                {'type': 'slash', 'name': 'buy', 'application_id': self.bot_id, 'kwargs': {'item': self.fish_bait}})
            duration = 300 if '5m' in self.fish_bait else 1200
            self.fish_bait_expires = now + duration + random.randint(60, 120)
            state_changed = True

        # Process treasure booster
        elif self.treasure_bait and (now >= self.treasure_bait_expires):
            commands.append(
                {'type': 'slash', 'name': 'buy', 'application_id': self.bot_id, 'kwargs': {'item': self.treasure_bait}})
            duration = 300 if '5m' in self.treasure_bait else 1200
            self.treasure_bait_expires = now + duration + random.randint(60, 120)
            state_changed = True

        # Process standard fish command
        elif self.do_fish and (now > self.next_run_fish):
            commands.append({'type': 'slash', 'name': 'fish', 'application_id': self.bot_id, 'kwargs': {}})
            self.next_run_fish = now + random.uniform(2, 10)
            state_changed = True

        # Process auto sleep tracking
        if commands:
            # Increment tracking if auto sleep is enabled
            if self.settings.get('auto_sleep'):
                self.commands_ran += len(commands)

            # Send current command count to dashboard
            self.framework.dashboard_callback(
                f'{self.commands_ran}/{self.sleep_target} commands before sleep.'
            )

            # Trigger auto sleep when target is met
            if self.settings.get('auto_sleep') and self.commands_ran >= self.sleep_target:
                sleep_duration = self._get_proportional_sleep(self.commands_ran)
                self.sleep_until = now + sleep_duration

                # Alert the dashboard about sleep status
                if hasattr(self.framework, 'dashboard_callback'):
                    self.framework.dashboard_callback('VIRTUAL FISHER ALERT')
                    self.framework.dashboard_callback(
                        f'💤 Auto-Sleep triggered! Ran {self.commands_ran} cmds. Sleeping for {round(sleep_duration / 60, 1)} minutes.',
                        lb=True)

                # Reset trackers for the next sleep cycle
                self.commands_ran = 0
                self.sleep_target = random.randint(80, 250)

            state_changed = True

        # Save state if any modifications occurred
        if state_changed:
            self._save_state()

        return commands

    async def process_message(self, message):
        # Placeholder for processing incoming messages
        pass

    def _save_state(self):
        # Attempt to save current timestamps to config
        try:
            self.state.update({
                'next_run_daily': self.next_run_daily,
                'next_run_fish': self.next_run_fish,
                'auto_fish_expires': self.auto_fish_expires,
                'fish_bait_expires': self.fish_bait_expires,
                'treasure_bait_expires': self.treasure_bait_expires,
                'commands_ran': self.commands_ran,
                'sleep_until': self.sleep_until,
                'sleep_target': self.sleep_target
            })

            # Save state to the framework and update config
            self.framework.settings['vf_state'] = self.state
            config_manager.update_profile(self.framework.profile_name, self.framework.token, self.framework.settings)

        except Exception as e:
            # Report any saving errors to the dashboard
            if hasattr(self.framework, 'dashboard_callback'):
                self.framework.dashboard_callback(f'Error saving VF state: {e}')
