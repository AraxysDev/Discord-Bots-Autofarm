# Import necessary modules
import os
import json
from datetime import datetime

# Set configuration directory and file paths
CONFIG_DIR = '/Applications/PhobosClient/data'
CONFIG_FILE = os.path.join(CONFIG_DIR, 'DiscordBotAutofarm.json')


def ensure_config_exists():
    # Check if the configuration directory exists
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)

    # Create a default configuration file if it does not exist
    if not os.path.exists(CONFIG_FILE):
        default_data = {
            'profiles': {},
            'stats': {}
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(default_data, f, indent=4)


def load_config():
    # Ensure the configuration file is present
    ensure_config_exists()

    # Attempt to load and return the JSON configuration
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Return an empty default structure if decoding fails
        return {'profiles': {}, 'stats': {}}


def save_config(data):
    # Ensure the configuration directory is present before saving
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)

    # Write the provided data to the configuration file
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)


def update_profile(profile_name, token, settings):
    # Load the existing configuration data
    data = load_config()

    # Update or create the specified profile entry
    data['profiles'][profile_name] = {
        'token': token,
        'settings': settings,
        'last_login': str(datetime.now())
    }

    # Save the updated configuration to disk
    save_config(data)


def log_command(profile_name, bot_name, command_type):
    # Load the existing configuration data
    data = load_config()

    # Ensure the nested stats dictionary structure exists
    if 'stats' not in data:
        data['stats'] = {}
    if profile_name not in data['stats']:
        data['stats'][profile_name] = {}
    if bot_name not in data['stats'][profile_name]:
        data['stats'][profile_name][bot_name] = {'total_commands': 0, 'history': []}

    # Increment command total and append to history
    data['stats'][profile_name][bot_name]['total_commands'] += 1
    data['stats'][profile_name][bot_name]['history'].append({
        'cmd': command_type,
        'time': str(datetime.now().strftime('%H:%M:%S'))
    })

    # Cap history list at 100 entries to prevent infinite growth
    if len(data['stats'][profile_name][bot_name]['history']) > 100:
        data['stats'][profile_name][bot_name]['history'].pop(0)

    # Save the updated configuration to disk
    save_config(data)
