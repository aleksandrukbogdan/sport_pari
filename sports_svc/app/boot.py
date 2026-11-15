from app.database import init_db
from app.database import read_events
from app.kafka_bus import publish_saved_events
from app.seed_events import seed_learning_events


def main() -> None:
    init_db()
    seed_learning_events()
    publish_saved_events(read_events())


if __name__ == "__main__":
    main()
