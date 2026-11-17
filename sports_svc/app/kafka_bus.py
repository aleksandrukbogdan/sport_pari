import json
import logging
import os
import time

logger = logging.getLogger(__name__)


def kafka_servers() -> list[str]:
    raw = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def topic_name() -> str:
    return os.getenv("KAFKA_TOPIC", "sports.matches")


def publish_event(event: dict) -> None:
    servers = kafka_servers()
    if not servers:
        return
    try:
        _send(servers, [event])
    except Exception:
        logger.warning("sports event %s was saved but not published", event.get("event_id"), exc_info=True)


def publish_saved_events(events: list[dict]) -> None:
    servers = kafka_servers()
    if not servers or not events:
        return
    deadline = time.monotonic() + 120
    while True:
        try:
            _send(servers, events)
            return
        except Exception:
            if time.monotonic() >= deadline:
                raise
            logger.warning("kafka is not ready, retrying sports events", exc_info=True)
            time.sleep(2)


def _send(servers: list[str], events: list[dict]) -> None:
    from kafka import KafkaProducer

    producer = KafkaProducer(
        bootstrap_servers=servers,
        acks="all",
        retries=3,
        request_timeout_ms=10000,
    )
    try:
        topic = topic_name()
        for event in events:
            producer.send(
                topic,
                key=str(event["match_id"]).encode(),
                value=json.dumps(event).encode(),
            )
        producer.flush(timeout=10)
    finally:
        producer.close()
