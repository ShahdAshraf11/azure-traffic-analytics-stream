# stream_processor/config.py
# Consumer-specific configuration
# Imports shared settings from data_generator/config.py and adds consumer-specific ones

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add data_generator to path so we can import shared config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data_generator"))
from config import DB_CONFIG, KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC

# Consumer-specific settings
CONSUMER_GROUP_ID = os.getenv("CONSUMER_GROUP_ID", "traffic-consumer-group")

# Window aggregation: group messages into 5-minute windows
WINDOW_SIZE_MINUTES = int(os.getenv("WINDOW_SIZE_MINUTES", 5))

# Paths to model files
MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
