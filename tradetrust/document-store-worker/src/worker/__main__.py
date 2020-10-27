from src.worker import Worker  # pragma: no cover
from src.config import Config  # pragma: no cover

Worker(Config.from_environ()).start()  # pragma: no cover
