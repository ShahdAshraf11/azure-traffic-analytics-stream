#This file manages the Kafka producer so it stays connected and can send messages anytime

# Note : Kafka only accepts bytes so we will convert Python dict to JSON string and then to bytes
# Note: The consumer will convert the bytes back to a dict

import json
import logging
from kafka import KafkaProducer
# KafkaError is the specific error type Kafka raises when something goes wrong e.g. Kafka down
from kafka.errors import KafkaError
from config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC
# Create a logger for this file
logger = logging.getLogger(__name__)
class KafkaClient:

    def __init__(self):
        self.producer = None
        self._create_producer()

    def _create_producer(self):
        '''
        Creates the KafkaProducer and stores it in self.producer
        '''
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                # value_serializer is a function  automatically converts a dict to JSON bytes so Kafka can send it
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                # wait for Kafka to confirm the message is saved
                acks="all",
                #If a send fails automatically retry up to 3 times
                retries=3,
                # linger_ms=10 means wait up to 10 milliseconds before sending in case more messages arrive to batch together
                linger_ms=10,
            )
            logger.info(f"Connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
            logger.info(f'Messages will go to topic: "{KAFKA_TOPIC}"')

        except KafkaError as e:
            # This happens if Kafka is not running or the address is wrong
            logger.error(f"Could not connect to Kafka: {e}")
            logger.error("Is Docker running? Try: docker compose up -d")
            # Note:
                # self.producer stays None
                # The producer will continue but Kafka sends will be skipped

    def send_message(self, record, location_name):
        '''
        Sends Data record as a message to the Kafka topic
        '''
        if self.producer is None:
            logger.warning("No Kafka producer : skipping send")
            return False
        
        message = {
            **record,
            "location_name": location_name,
        }

        try:
            # Send the message asynchronously to Kafka, automatically converting it to bytes, and return a Future to confirm delivery
            future = self.producer.send(KAFKA_TOPIC, value=message)
            # waits for Kafka to confirm the message, returning partition , and offset
            result = future.get(timeout=10) 
            logger.info(
                f"Sent to Kafka: {location_name} | "
                f"topic={KAFKA_TOPIC} | "
                f"partition={result.partition} | "
                f"offset={result.offset}"
            )
            return True

        except KafkaError as e:
            logger.error(f"Failed to send {location_name} to Kafka: {e}")
            return False

        except Exception as e:
            # Catch any other unexpected error
            logger.error(f"Unexpected error sending to Kafka: {e}")
            return False

    def close_producer(self):
        '''
        Close the Kafka producer
        '''
        if self.producer is None:
            return
        
        #sends all messages still in the buffer with a timeout to avoid waiting
        self.producer.flush(timeout=10)

        # close() disconnects from Kafka and frees up memory
        self.producer.close()

        logger.info("Kafka producer closed cleanly.")
