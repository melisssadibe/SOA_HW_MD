# consumer.py
from kafka import KafkaConsumer
import json
from clickhouse_driver import Client
from datetime import datetime

client = Client(host='clickhouse', user='admin', password='admin123', database='default')

def create_tables():
    client.execute("""
        CREATE TABLE IF NOT EXISTS post_views (
            user_id String,
            post_id String,
            viewed_at DateTime
        ) ENGINE = MergeTree()
        ORDER BY (post_id, viewed_at)
    """)
    client.execute("""
        CREATE TABLE IF NOT EXISTS post_likes (
            user_id String,
            post_id String,
            liked_at DateTime
        ) ENGINE = MergeTree()
        ORDER BY (post_id, liked_at)
    """)
    client.execute("""
        CREATE TABLE IF NOT EXISTS post_comments (
            user_id String,
            post_id String,
            comment String,
            commented_at DateTime
        ) ENGINE = MergeTree()
        ORDER BY (post_id, commented_at)
    """)

def run_kafka_consumer():
    consumer = KafkaConsumer(
        'post_viewed', 'post_liked', 'post_commented',
        bootstrap_servers='kafka:9092',
        value_deserializer=lambda v: json.loads(v.decode('utf-8'))
    )

    print("📥 Kafka consumer started...")

    for msg in consumer:
        event = msg.value
        topic = msg.topic

        if topic == 'post_viewed':
            client.execute(
                "INSERT INTO post_views (user_id, post_id, viewed_at) VALUES",
                [(event['user_id'], event['post_id'], datetime.fromisoformat(event['viewed_at']))]
            )

        elif topic == 'post_liked':
            client.execute(
                "INSERT INTO post_likes (user_id, post_id, liked_at) VALUES",
                [(event['user_id'], event['post_id'], datetime.fromisoformat(event['liked_at']))]
            )

        elif topic == 'post_commented':
            client.execute(
                "INSERT INTO post_comments (user_id, post_id, comment, commented_at) VALUES",
                [(event['user_id'], event['post_id'], event['comment'], datetime.fromisoformat(event['commented_at']))]
            )
