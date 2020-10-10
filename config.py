import logging

logger = logging.getLogger("gunicorn.error")
logger.setLevel(logger.level)

ENV = "prod"
