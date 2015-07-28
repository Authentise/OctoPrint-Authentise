import logging
import pytest
import httpretty as HTTPretty
from octoprint_authentise.printer import AuthentisePrinter
import octoprint.settings

LOGGER = logging.getLogger(__name__)

@pytest.fixture
def create_printer(mocker):
    def __inner():
        mocker.patch('octoprint.plugin.plugin_manager', return_value=mocker.Mock())

        file_manager = mocker.Mock()
        analysis_queue = mocker.Mock()
        printer_profile_manager = mocker.Mock()

        _printer = AuthentisePrinter()
        _printer.startup(fileManager=file_manager, analysisQueue=analysis_queue, printerProfileManager=printer_profile_manager)
        return _printer
    return __inner

@pytest.fixture
def create_settings(mocker):
    def __inner():
        mocker.patch('octoprint.settings.Settings.save')
        _settings = octoprint.settings.settings(init=True, basedir='.')
        return _settings
    return __inner

@pytest.fixture
def printer(create_printer, settings):
    return create_printer()

@pytest.fixture
def settings(create_settings):
    default_settings = octoprint.settings.default_settings
    default_settings['plugins']['authentise'] = {'api_key': 'some-key', 'api_secret': 'some-secret'}
    _settings = create_settings()
    return _settings

@pytest.yield_fixture
def httpretty():
    import socket
    old_socket_type = socket.SocketType
    HTTPretty.enable()
    yield HTTPretty
    HTTPretty.disable()
    socket.SocketType = old_socket_type
    HTTPretty.reset()

