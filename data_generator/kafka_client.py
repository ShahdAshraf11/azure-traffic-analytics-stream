# ============================================================
#  kafka_client.py
#  This file sends messages to Kafka.
#
#  We wrote it as a CLASS because it needs to REMEMBER
#  the KafkaProducer object between every send call.
#
#  Without a class, we would pass 'producer' into every
#  function — just like the connection problem in db_client.
#  With a class, we create the producer ONCE in __init__
#  and every method uses it through 'self'.
#
#  HOW TO USE THIS FILE IN producer.py:
#
#    from kafka_client import KafkaClient
#
#    kafka = KafkaClient()              # connects to Kafka once
#    kafka.send(record, location_name)  # sends one message
#    kafka.close()                      # closes when done
# ============================================================


# --- Import the libraries we need ---------------------------

# json converts Python dictionaries to JSON strings.
# Kafka only understands BYTES — not Python objects.
# So we convert: dict -> JSON string -> bytes before sending.
import json

# logging saves messages to our log file and terminal
import logging

# KafkaProducer is the class from kafka-python library
# that actually sends messages to Kafka
from kafka import KafkaProducer

# KafkaError is the specific error type Kafka raises
# when something goes wrong (Kafka down, wrong address, etc.)
from kafka.errors import KafkaError

# Import our Kafka settings from config.py
from config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC


# Create a logger for this file
logger = logging.getLogger(__name__)


# ============================================================
#  CLASS: KafkaClient
# ============================================================
# This class wraps the KafkaProducer from kafka-python.
# It stores the producer in self.producer and provides
# two simple methods: send() and close().
#
# We named it KafkaClient (not KafkaProducer) to avoid
# confusion with the KafkaProducer class we import above.
# ============================================================

class KafkaClient:


    # --------------------------------------------------------
    #  __init__  (the constructor)
    # --------------------------------------------------------
    # Runs automatically when you write: kafka = KafkaClient()
    # Opens the connection to Kafka and stores the producer
    # in self.producer so send() can use it.
    # --------------------------------------------------------

    def __init__(self):

        # self.producer will hold our KafkaProducer object.
        # We set it to None first as a safe starting value.
        # If connecting to Kafka fails it stays None and
        # send() will check for None and skip gracefully.
        self.producer = None

        # Try to connect to Kafka
        self._create_producer()


    # --------------------------------------------------------
    #  _create_producer  (private helper)
    # --------------------------------------------------------
    # Creates the KafkaProducer and stores it in self.producer.
    # Private method — only called inside this class.
    # --------------------------------------------------------

    def _create_producer(self):

        try:
            # Create a KafkaProducer with our settings.
            self.producer = KafkaProducer(

                # Tell Kafka where our server is.
                # From our .env: KAFKA_BOOTSTRAP_SERVERS=localhost:9092
                # localhost = this same computer
                # 9092 = the port Kafka listens on (set in docker-compose.yml)
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,

                # value_serializer is a function that runs AUTOMATICALLY
                # every time we call send(). It converts our message
                # from a Python dict into bytes that Kafka can understand.
                #
                # 'lambda v:' means "a small function that takes v as input"
                # json.dumps(v) converts dict to JSON string: '{"speed": 45}'
                # .encode('utf-8') converts string to bytes: b'{"speed": 45}'
                #
                # Why bytes? Kafka is a message broker — it stores raw bytes.
                # It does not know or care about Python objects.
                # The consumer will convert the bytes back to a dict.
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),

                # acks='all' means "wait for Kafka to confirm the message
                # was saved before moving on."
                # Without this, we send and immediately move on — fast but
                # we might lose the message if Kafka has a problem.
                # 'all' = slower but safe. We know every message was received.
                acks='all',

                # If a send fails, automatically retry up to 3 times.
                # This handles temporary Kafka hiccups without crashing.
                retries=3,

                # linger_ms=10 means "wait up to 10 milliseconds before
                # sending, in case more messages arrive to batch together."
                # This makes sending slightly more efficient.
                # 10ms is tiny — you won't notice the delay.
                linger_ms=10,
            )

            logger.info(f'Connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}')
            logger.info(f'Messages will go to topic: "{KAFKA_TOPIC}"')

        except KafkaError as e:
            # This happens if Kafka is not running or the address is wrong
            logger.error(f'Could not connect to Kafka: {e}')
            logger.error('Is Docker running? Try: docker compose up -d')

            # self.producer stays None
            # The producer will continue but Kafka sends will be skipped


    # --------------------------------------------------------
    #  send_message
    # --------------------------------------------------------
    # Sends ONE traffic record as a message to the Kafka topic.
    #
    # Parameters:
    #   record        = dictionary of traffic data from api_client.py
    #   location_name = the road name e.g. "Tahrir Square"
    #
    # Returns True if sent successfully, False if it failed.
    # --------------------------------------------------------

    def send_message(self, record, location_name):

        # If producer is None we never connected to Kafka.
        # Skip the send and return False immediately.
        if self.producer is None:
            logger.warning('No Kafka producer — skipping send.')
            return False

        # Build the message we will send to Kafka.
        # {**record} copies all fields from the traffic record.
        # We add location_name into the message so the consumer
        # knows which road this data belongs to.
        # We create a COPY ({**record}) instead of modifying the
        # original record — good habit to avoid unexpected side effects.
        message = {
            **record,
            'location_name': location_name,
        }

        try:
            # producer.send() puts the message into Kafka.
            #
            # topic=KAFKA_TOPIC tells Kafka which channel to put it in.
            # Our topic is 'traffic-data' (from config.py).
            #
            # value=message is the data to send.
            # Remember: value_serializer we set in __init__ automatically
            # converts this dict to bytes before it is actually sent.
            #
            # producer.send() does NOT send immediately — it returns a
            # "Future" object. A Future is a promise: "I will have a
            # result for you later." We store it to wait for confirmation.
            future = self.producer.send(KAFKA_TOPIC, value=message)

            # .get(timeout=10) WAITS until Kafka confirms the message.
            # It blocks here (pauses our code) until either:
            #   a) Kafka says "got it" (success) — returns a Recordresult
            #   b) 10 seconds pass with no reply (timeout error)
            #
            # Recordresult contains:
            #   .partition = which partition (bucket) inside the topic
            #   .offset    = the message's sequential position number
            # These are useful for debugging if you need to find a message.
            result = future.get(timeout=10)

            logger.info(
                f'Sent to Kafka: {location_name} | '
                f'topic={KAFKA_TOPIC} | '
                f'partition={result.partition} | '
                f'offset={result.offset}'
            )
            return True

        except KafkaError as e:
            logger.error(f'Failed to send {location_name} to Kafka: {e}')
            return False

        except Exception as e:
            # Catch any other unexpected error (timeout, etc.)
            logger.error(f'Unexpected error sending to Kafka: {e}')
            return False


    # --------------------------------------------------------
    #  close_producer
    # --------------------------------------------------------
    # Cleanly shuts down the Kafka producer when the script stops.
    # Called in the finally block of producer.py.
    #
    # Why do we need this?
    # KafkaProducer has an internal BUFFER — a small queue of
    # messages waiting to be sent. If we just kill the script,
    # those buffered messages are LOST forever.
    # flush() forces all buffered messages to be sent first.
    # Then close() disconnects cleanly.
    # --------------------------------------------------------

    def close_producer(self):

        # Only close if we actually have a producer
        if self.producer is None:
            return

        # flush() sends any messages still waiting in the buffer.
        # Like "send all drafts before closing the email app."
        # We pass a timeout so it does not wait forever.
        self.producer.flush(timeout=10)

        # close() disconnects from Kafka and frees up memory
        self.producer.close()

        logger.info('Kafka producer closed cleanly.')
