import json
import logging
import uuid
from urlparse import urljoin

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

@pytest.fixture
def printer(comm, node_uuid, settings, httpretty): #pylint: disable=redefined-outer-name
    comm.node_uuid = node_uuid

    url = urljoin(settings.get(["authentise_url"]), "/printer/instance/")
    printer_uri = urljoin(url, "abc-123/")

    printer_payload = {"baud_rate": 250000,
                       "port": "/dev/tty.derp",
                       "uri": printer_uri}

    httpretty.register_uri(httpretty.GET,
                           url,
                           body=json.dumps({"resources": [printer_payload]}),
                           content_type='application/json')

    httpretty.register_uri(httpretty.GET,
                           printer_uri,
                           body=json.dumps(printer_payload),
                           content_type='application/json')

    return {'uri':printer_uri, 'request_url':url, 'port':'/dev/tty.derp', 'baud_rate':250000}

@pytest.fixture
def connect_printer(comm, printer, mocker, event_manager): #pylint: disable=redefined-outer-name, unused-argument
    mocker.patch('octoprint_authentise.comm.threading.Thread')
    mocker.patch('octoprint_authentise.comm.RepeatedTimer')
    mocker.patch("octoprint_authentise.comm.helpers.run_client")

    comm.connect(port=printer['port'], baudrate=printer['baud_rate'])

@pytest.fixture
def node_uuid():
    return uuid.uuid4()

@pytest.fixture
def event_manager(mocker):
    manager = mocker.Mock()
    mocker.patch('octoprint_authentise.comm.eventManager', return_value=manager)
    return manager

@pytest.fixture
def set_time(mocker):
    def __inner(_time):
        mocker.patch('time.time', return_value=_time)
    return __inner

@pytest.yield_fixture
def httpretty():
    import socket
    old_socket_type = socket.SocketType
    HTTPretty.enable()
    yield HTTPretty
    HTTPretty.disable()
    socket.SocketType = old_socket_type
    HTTPretty.reset()

@pytest.fixture
def assert_almost_equal():
    def __inner(value_0, value_1, places=4):
        if value_0 != value_1:
            value_0 = cut_insignificant_digits_recursively(value_0, places)
            value_1 = cut_insignificant_digits_recursively(value_1, places)
        assert value_0 == value_1
    return __inner

#these fucntions are for very basic asserting almost equal, taken from and answer in
#http://stackoverflow.com/questions/12136762/assertalmostequal-in-python-unit-test-for-collections-of-floats
def cut_insignificant_digits(number, places):
    if not isinstance(number, float):
        return number
    number_as_str = str(number)
    end_of_number = number_as_str.find('.')+places+1
    if end_of_number > len(number_as_str):
        return number
    return float(number_as_str[:end_of_number])

def cut_insignificant_digits_lazy(iterable, places):
    for obj in iterable:
        yield cut_insignificant_digits_recursively(obj, places)

def cut_insignificant_digits_recursively(obj, places):
    t = type(obj)
    if t == float:
        return cut_insignificant_digits(obj, places)
    if t in (list, tuple, set):
        return t(cut_insignificant_digits_lazy(obj, places))
    if t == dict:
        return {cut_insignificant_digits_recursively(key, places):
                cut_insignificant_digits_recursively(val, places)
                for key,val in obj.items()}
    return obj
