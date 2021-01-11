__version__ = "1.0.0"

import logging

logger = logging.getLogger(__name__)
if not logger.handlers:  # To ensure reload() doesn't add another handler
    logger.addHandler(logging.NullHandler())
