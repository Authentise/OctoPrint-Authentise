import logging
import pytest

LOGGER = logging.getLogger(__name__)

@pytest.fixture
def create_printer():
    def __inner():
        pass
    return __inner

@pytest.fixture
def printer(create_printer):
    return create_printer()

