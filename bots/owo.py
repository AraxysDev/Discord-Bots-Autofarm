# Import necessary modules
import time
import random
import re
import config_manager


class OwoBot:
    def __init__(self, framework):
        # Setup framework and retrieve settings
        self.framework = framework
        self.name = 'OwO'
        self.settings = framework.settings.get('owo_settings', {})

        # Load persistent state or create an empty one
        self.state = framework.settings.get('owo_state', {})

        # Set the ID for the OwO bot
        self.owo_bot_id = 408785106942164992

        # Setup isolated anti-captcha state
        self.captcha_detected = False

        # Initialize internal trackers from state
        self.next_run = {
            'hunt': self.state.get('next_hunt', 0),
            'battle': self.state.get('next_battle', 0),
            'daily': self.state.get('next_daily', 0),
            'cookie': self.state.get('next_cookie', 0),
            'pray': self.state.get('next_pray', 0),
            'pets': self.state.get('next_pets', 0),
            'inv': self.state.get('next_inv', 0)
        }

        # Setup auto-sleep trackers
        self.commands_ran = self.state.get('commands_ran', 0)
        self.sleep_until = self.state.get('sleep_until', 0)
        self.sleep_target = self.state.get('sleep_target', random.randint(32, 600))

        # Setup queue for priority actions
        self.injected_commands = []

        # Setup variables for text debouncing
        self.last_processed_text = ''
        self.last_processed_time = 0

    def _save_state(self):
        # Update state with current timestamps and sleep tracking
        self.state.update({
            'next_hunt': self.next_run['hunt'],
            'next_battle': self.next_run['battle'],
            'next_daily': self.next_run['daily'],
            'next_cookie': self.next_run['cookie'],
            'next_pray': self.next_run['pray'],
            'next_pets': self.next_run['pets'],
            'commands_ran': self.commands_ran,
            'sleep_until': self.sleep_until,
            'sleep_target': self.sleep_target
        })

        # Save state to the framework and update config
        self.framework.settings['owo_state'] = self.state
        config_manager.update_profile(self.framework.profile_name, self.framework.token, self.framework.settings)

    def _get_proportional_sleep(self, commands_since_sleep):
        # Clamp bounds between 32 and 300 as per strategy
        cmds = max(32.0, min(float(commands_since_sleep), 300.0))

        # Calculate linear ratio
        ratio = (cmds - 32.0) / (300.0 - 32.0)

        # Set min and max sleep times in milliseconds
        min_sleep = 8 * 60 * 1000
        max_sleep = 90 * 60 * 1000

        # Calculate base sleep duration
        sleep_ms = min_sleep + ratio * (max_sleep - min_sleep)

        # Add randomization variance
        variance = random.uniform(0.65, 1.35)
        final_sleep_ms = sleep_ms * variance

        # Return duration in seconds
        return final_sleep_ms / 1000.0

    def tick(self):
        # Get the current time
        now = time.time()

        # Check if the bot is frozen by captcha
        if self.captcha_detected:
            return []

        # Check if we are currently sleeping
        if self.settings.get('auto_sleep') and now < self.sleep_until:
            return []

        # Initialize variables and limits
        commands = []
        state_changed = False
        batch_count = 0
        batch_limit = 3

        # Define all commands and their cooldowns in a clean, easily editable list
        action_configs = [
            ('auto_hunt', 'hunt', ['owo hunt'], 18.0, 25.0),
            ('auto_battle', 'battle', ['owo battle'], 18.0, 24.0),
            ('auto_daily', 'daily', ['owo daily'], 86400.0, 87000.0),
            ('auto_cookie', 'cookie', ['owo cookie'], 86400.0, 87000.0),
            ('auto_pray', 'pray', ['owo pray'], 600.0, 1200.0),
            ('auto_pets', 'pets', ['owo pup', 'owo piku', 'owo run'], 120.0, 700.0)
        ]

        # Dynamically process all actions
        for setting, key, cmds, min_cd, max_cd in action_configs:
            if self.settings.get(setting) and now > self.next_run[key]:
                if batch_count >= batch_limit:
                    # Delay for overflow
                    self.next_run[key] = now + random.uniform(30.0, 60.0)
                else:
                    # Add to queue and set standard cooldown
                    commands.extend(cmds)
                    self.next_run[key] = now + random.uniform(min_cd, max_cd)
                    batch_count += len(cmds)

                state_changed = True

        # Randomize execution order to prevent patterns
        if commands:
            random.shuffle(commands)

        # Inject priority commands into the queue
        if self.injected_commands:
            commands.extend(self.injected_commands)
            self.injected_commands = []
            state_changed = True

        # Process auto sleep tracking
        if commands:
            # Increment tracking if auto sleep is enabled
            if self.settings.get('auto_sleep'):
                self.commands_ran += len(commands)

            # Send current command count to dashboard
            self.framework.dashboard_callback(
                f'OwO: {self.commands_ran}/{self.sleep_target} commands before sleep.'
            )

            # Trigger auto sleep when target is met
            if self.settings.get('auto_sleep') and self.commands_ran >= self.sleep_target:
                sleep_duration = self._get_proportional_sleep(self.commands_ran)
                self.sleep_until = now + sleep_duration

                # Alert the dashboard about sleep status
                self.framework.dashboard_callback('OWO BOT ALERT')
                self.framework.dashboard_callback(
                    f'💤 Auto-Sleep triggered! Ran {self.commands_ran} cmds. Sleeping for {round(sleep_duration / 60, 1)} minutes.',
                    lb=True)

                # Reset trackers for the next sleep cycle
                self.commands_ran = 0
                self.sleep_target = random.randint(32, 300)
                state_changed = True

        # Save state if any modifications occurred
        if state_changed:
            self._save_state()

        return commands

    async def process_message(self, message):
        # Process messages originating from the OwO bot
        if message.author.id == self.owo_bot_id:

            # Extract the initial text content
            full_text = message.content or ''

            # Append any text found within embeds
            for embed in message.embeds:
                if embed.title:
                    full_text += f' {embed.title}'
                if embed.description:
                    full_text += f' {embed.description}'
                for field in embed.fields:
                    if field.name:
                        full_text += f' {field.name}'
                    if field.value:
                        full_text += f' {field.value}'
                if embed.footer and getattr(embed.footer, 'text', None):
                    full_text += f' {embed.footer.text}'

            if not getattr(self.framework, 'client', None) or not self.framework.client.user:
                return

            # Curl user info
            user_id = str(self.framework.client.user.id)
            user_name = self.framework.client.user.name.lower()
            user_display = self.framework.client.user.display_name.lower()
            text_lower = full_text.lower()

            # Check if message was directed towards the user
            if not (user_id in text_lower or user_name in text_lower or user_display in text_lower):
                return

            # Check if this text was just processed within 5 seconds
            current_time = time.time()
            if full_text == getattr(self, 'last_processed_text', '') and (
                    current_time - getattr(self, 'last_processed_time', 0)) < 5.0:
                return

            # Save the current text and time for the next check
            self.last_processed_text = full_text
            self.last_processed_time = current_time

            # Search the text for captcha warnings
            captcha_pattern = re.compile(r'are you a real human|(check|verify) that you are.{1,3}human!', re.IGNORECASE)
            if captcha_pattern.search(full_text):
                self.captcha_detected = True
                self.framework.dashboard_callback('🚨OWO CAPTCHA DETECTED! 🚨')
                self.framework.dashboard_callback(
                    '⏸️ OwO Bot PAUSED. Virtual Fisher will continue running independently.')
                self.framework.dashboard_callback(
                    '👉 Please solve the captcha manually in Discord, then restart the bot.', lb=True)
                return

            # Check for hunt notifications and track missing gems
            if 'You found:' in full_text or 'hunt is empowered by' in full_text:
                if 'Inventory' not in full_text:
                    equipped_gems = re.findall(r'<a?:[a-z]+(gem[134]):\d+>', full_text)

                    present_types = set(equipped_gems)
                    all_types = {'gem1', 'gem3', 'gem4'}
                    missing = list(all_types - present_types)

                    self.state['missing_gems'] = missing
                    self._save_state()

                    # Queue an inventory scan if cooldown has expired
                    if missing:
                        if time.time() > self.next_run['inv']:
                            self.injected_commands.append('owo inv')
                            self.next_run['inv'] = time.time() + 300.0
                            self._save_state()

            # Process inventory scans
            if 'Inventory ======' in full_text:
                super_trans = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹', '0123456789')

                # Function to parse quantity values
                def parse_qty(qty_str):
                    return int(qty_str.translate(super_trans)) if qty_str else 1

                # Find gem, box, and crate matches
                gem_matches = re.findall(r'`(\d{3})`<a?:([a-z]+)(gem[134]):\d+>([⁰¹²³⁴⁵⁶⁷⁸⁹]*)', full_text)
                box_matches = re.findall(r'<a?:box:\d+>([⁰¹²³⁴⁵⁶⁷⁸⁹]*)', full_text)
                crate_matches = re.findall(r'<a?:crate:\d+>([⁰¹²³⁴⁵⁶⁷⁸⁹]*)', full_text)

                # Calculate totals
                total_boxes = sum(parse_qty(q) for q in box_matches)
                total_crates = sum(parse_qty(q) for q in crate_matches)
                total_gems = 0

                # Sort gems into their respective dictionaries
                inv_gems = {'gem1': [], 'gem3': [], 'gem4': []}
                for item_id, rarity, gem_type, qty_str in gem_matches:
                    qty = parse_qty(qty_str)
                    total_gems += qty
                    inv_gems[gem_type].append((int(item_id), rarity))

                self.state['inventory_gems'] = inv_gems
                self._save_state()

                # Print inventory details to dashboard
                self.framework.dashboard_callback('🎒 --- Inventory Scan Complete ---')
                self.framework.dashboard_callback(f'📦 Lootboxes: {total_boxes} | 🧰 Crates: {total_crates}')
                self.framework.dashboard_callback(f'💎 Total Gems: {total_gems}')

                # Print individual gem availability
                for gem_type in ['gem1', 'gem3', 'gem4']:
                    available = inv_gems.get(gem_type, [])

                    if not available:
                        self.framework.dashboard_callback(f'👉 {gem_type}: You have 0 in inventory.')
                    else:
                        available.sort(key=lambda x: x[0])
                        lowest = available[0]
                        highest = available[-1]

                        self.framework.dashboard_callback(
                            f'👉 {gem_type} | Lowest: {lowest[1]}{gem_type} (`{lowest[0]:03}`) | Highest: {highest[1]}{gem_type} (`{highest[0]:03}`)'
                        )

                # Check missing gems and gem strategy
                missing = self.state.get('missing_gems', [])
                auto_gem_strat = self.settings.get('auto_gem', 'None')

                # Automatically trigger missing gems logic
                if missing:
                    separator = ', '
                    joined_missing = separator.join(missing)
                    self.framework.dashboard_callback(f'⚠️ Gems missing from Hunt: {joined_missing}', lb=True)

                    if auto_gem_strat != 'None':
                        gems_to_use = []
                        for m_type in missing:
                            available = inv_gems.get(m_type, [])
                            if available:
                                available.sort(key=lambda x: x[0])
                                if auto_gem_strat == 'Rarity low to high':
                                    chosen_id = available[0][0]
                                elif auto_gem_strat == 'Rarity high to low':
                                    chosen_id = available[-1][0]

                                gems_to_use.append(str(chosen_id))

                        # Queue gem usage command
                        if gems_to_use:
                            separator_space = ' '
                            use_command = f'owo use {separator_space.join(gems_to_use)}'
                            self.injected_commands.append(use_command)

                            # Clear missing state so it doesn't loop
                            self.state['missing_gems'] = []
                            self._save_state()

                            self.framework.dashboard_callback(f'💎 Auto Gem: \'{use_command}\'',
                                                              lb=True)
                else:
                    self.framework.dashboard_callback('✅ All gem buffs are active!', lb=True)

                # Process auto lootbox opening
                if self.settings.get('auto_lootbox', False) and total_boxes > 0:
                    self.injected_commands.append('owolb all')
                    self.framework.dashboard_callback('📦 Auto Lootbox: \'owolb all\'', lb=True)

                # Process auto crate opening
                if self.settings.get('auto_crate', False) and total_crates > 0:
                    self.injected_commands.append('owowc all')
                    self.framework.dashboard_callback('🗳️Auto Crate: \'owowc all\'', lb=True)
