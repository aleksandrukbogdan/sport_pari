import json
import logging

from app.config import get_settings
from app.tasks import ingest_sports_event

logger = logging.getLogger(__name__)


def handle_message(raw: bytes) -> None:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("sports event payload must be an object")
    ingest_sports_event.delay(payload)


def run_consumer() -> None:
    from kafka import KafkaConsumer

    settings = get_settings()
    servers = [item.strip() for item in settings.kafka_bootstrap_servers.split(",") if item.strip()]
    consumer = KafkaConsumer(
        settings.kafka_topic,
        bootstrap_servers=servers,
        group_id=settings.kafka_group_id,
        enable_auto_commit=True,
        auto_offset_reset="earliest",
    )
    for message in consumer:
        try:
            handle_message(message.value)
        except json.JSONDecodeError:
            logger.warning("skipped sports message that is not JSON")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    run_consumer()


if __name__ == "__main__":
    main()
