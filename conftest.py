import logging

import httpretty as HTTPretty
import octoprint.plugin
import octoprint.settings
import pytest

from octoprint_authentise import AuthentisePlugin

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
    octoprint.settings._instance = None #pylint: disable=protected-access

@pytest.fixture
def plugin(settings): #pylint: disable=redefined-outer-name
    _plugin = AuthentisePlugin()
    _plugin._settings = settings #pylint: disable=protected-access
    return _plugin

@pytest.yield_fixture
def comm(plugin, mocker): #pylint: disable=redefined-outer-name
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
