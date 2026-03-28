from kafka import KafkaProducer
import json
import os
from dotenv import load_dotenv

load_dotenv()
print("KAFKA_BOOTSTRAP_SERVERS =", os.getenv("KAFKA_BOOTSTRAP_SERVERS"))

producer = KafkaProducer(
    bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS"),
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)

producer.send("test-topic", {"message": "hello from producer"})
producer.flush()
print("Message sent to test-topic")
