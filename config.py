# config.py
# Configuration variables for InstaSpider

from dotenv import load_dotenv
import os

load_dotenv()

INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')


# Instagram profiles
PROFILES = ["wesserschweiz"]

# Scheduler settings
SCHEDULE_INTERVAL_MINUTES = 2

# Instagram API settings
INSTAGRAM_API_URL = 'https://www.instagram.com/api/v1/users/web_profile_info/?username='

# Other constants like database settings, file paths, etc. can be added here
