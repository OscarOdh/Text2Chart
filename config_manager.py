import configparser
import os

CONFIG_FILE = 'settings.ini'

def load_config():
    """Load configuration from settings.ini or return defaults."""
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    
    # Ensure sections exist
    if 'SQL' not in config:
        config['SQL'] = {}
    if 'AI' not in config:
        config['AI'] = {}
        
    # SQL Defaults
    if 'server' not in config['SQL']: config['SQL']['server'] = 'localhost'
    if 'port' not in config['SQL']: config['SQL']['port'] = '1433'
    if 'database' not in config['SQL']: config['SQL']['database'] = 'MyData'
    if 'username' not in config['SQL']: config['SQL']['username'] = 'sa'
    if 'password' not in config['SQL']: config['SQL']['password'] = ''
    
    # AI Defaults
    if 'base_url' not in config['AI']: config['AI']['base_url'] = 'http://localhost:1234/v1/'
    if 'model' not in config['AI']: config['AI']['model'] = 'local-model' # LM Studio often ignores this or you can use "god"
    
    return config

def save_config(config):
    """Save configuration to settings.ini."""
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)
