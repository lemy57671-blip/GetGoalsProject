from __future__ import annotations

import logging

from app.services.chat.local_algorithm_provider import LocalAlgorithmProvider

logger = logging.getLogger(__name__)


def get_tutor_provider() -> LocalAlgorithmProvider:
    return LocalAlgorithmProvider()

