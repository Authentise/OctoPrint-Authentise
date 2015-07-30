import logging
import pytest
import httpretty as HTTPretty
from octoprint_authentise.comm import MachineCom
from octoprint_authentise import AuthentisePlugin
import octoprint.settings
import octoprint.plugin

LOGGER = logging.getLogger(__name__)
logging.basicConfig()

@pytest.yield_fixture
def settings(mocker):
    plugin_settings = {
                'api_key': 'some-key',
                'api_secret': 'some-secret',
                'authentise_url': 'https://not-a-real-url.com/',
                }

    default_settings = octoprint.settings.default_settings
    default_settings['plugins']['authentise'] = plugin_settings
    mocker.patch('octoprint.settings.Settings.save')
    octoprint.settings.settings(init=True, basedir='.')
    _settings = octoprint.plugin.plugin_settings('authentise', defaults=plugin_settings)
    yield _settings
    octoprint.settings._instance = None

@pytest.fixture
def plugin(settings, mocker):
    _plugin = AuthentisePlugin()
    _plugin._settings = settings
    return _plugin

@pytest.yield_fixture
def comm(plugin, mocker):
    mocker.patch('octoprint.plugin.plugin_manager', return_value=mocker.Mock())

    callback = mocker.Mock()
    printer_profile_manager = mocker.Mock()

    plugin.startup(callbackObject=callback, printerProfileManager=printer_profile_manager)

    yield plugin
    plugin.close()

@pytest.yield_fixture
def httpretty():
    import socket
    old_socket_type = socket.SocketType
    HTTPretty.enable()
    yield HTTPretty
    HTTPretty.disable()
    socket.SocketType = old_socket_type
    HTTPretty.reset()

