import json
from urlparse import urljoin

import httpretty
import json
import pytest
import Queue

from octoprint_authentise import comm as _comm


# tests case in which the user has no authentise printers
def test_printer_connect_create_authentise_printer(comm, httpretty, mocker, settings):
    comm.node_uuid = "youre-a-wizard-harry"

    url = urljoin(settings.get(["authentise_url"]), "/printer/instance/")

    httpretty.register_uri(httpretty.GET,
                           url,
                           body=json.dumps({"resources": []}),
                           content_type='application/json')

    httpretty.register_uri(httpretty.POST, url,
                           adding_headers={"Location": urljoin(url, "abc-123/")})

    # keep authentise from actually starting
    mocker.patch("octoprint_authentise.helpers.run_client")

    comm.connect(port="1234", baudrate=5678)

    assert comm.isOperational()
    assert not comm.isBusy()
    assert not comm.isPrinting()
    assert not comm.isPaused()
    assert not comm.isError()
    assert not comm.isClosedOrError()
    assert comm._printer_uri == urljoin(url, "abc-123/")


# tests case in which the user has a printer on the right port, but the baud rate is wrong
def test_printer_connect_get_authentise_printer(comm, httpretty, mocker, settings):
    comm.node_uuid = "youre-a-wizard-harry"
    url = urljoin(settings.get(["authentise_url"]), "/printer/instance/")
    printer_uri = urljoin(url, "abc-123/")
    printers_payload = {"resources": [{"baud": 250000,
                                       "port": "/dev/tty.derp",
                                       "uri": printer_uri}]}

    httpretty.register_uri(httpretty.GET,
                           url,
                           body=json.dumps(printers_payload),
                           content_type='application/json')

    httpretty.register_uri(httpretty.POST, url,
                           adding_headers={"Location": urljoin(url, "abc-123/")})

    httpretty.register_uri(httpretty.PUT, printer_uri)


    # keep authentise from actually starting
    mocker.patch("octoprint_authentise.helpers.run_client")

    comm.connect(port="/dev/tty.derp", baudrate=5678)

    assert comm.isOperational()
    assert not comm.isBusy()
    assert not comm.isPrinting()
    assert not comm.isPaused()
    assert not comm.isError()
    assert not comm.isClosedOrError()
    assert comm._printer_uri == urljoin(url, "abc-123/")


# tests case in which port and baud rate are just right
def test_printer_connect_get_authentise_printer_no_put(comm, httpretty, mocker, settings):
    comm.node_uuid = "youre-a-wizard-harry"
    url = urljoin(settings.get(["authentise_url"]), "/printer/instance/")
    printer_uri = urljoin(url, "abc-123/")
    printers_payload = {"resources": [{"baud": 250000,
                                       "port": "/dev/tty.derp",
                                       "uri": printer_uri}]}

    httpretty.register_uri(httpretty.GET,
                           url,
                           body=json.dumps(printers_payload),
                           content_type='application/json')

    # keep authentise from actually starting
    mocker.patch("octoprint_authentise.helpers.run_client")

    comm.connect(port="/dev/tty.derp", baudrate=250000)

    assert comm.isOperational()
    assert not comm.isBusy()
    assert not comm.isPrinting()
    assert not comm.isPaused()
    assert not comm.isError()
    assert not comm.isClosedOrError()
    assert comm._printer_uri == urljoin(url, "abc-123/")

@pytest.mark.parametrize("command_queue, response, current_time, expected_return, expected_queue", [
    (
        {
            'uri'          : 'https://not-a-uri.com/',
            'start_time'   : 0,
            'previous_time' : None,
        },
        {
            'status_code': 200,
            'json': {
                'command'  : 'G28 X Y',
                'response' : 'ok',
                'status'   : 'ok',
                },
        },
        10,
        'ok',
        None
    ),
    (
        {
            'uri'          : 'https://not-a-uri.com/',
            'start_time'   : 0,
            'previous_time' : None,
        },
        {
            'status_code': 200,
            'json': {
                'command'  : 'G28 X Y',
                'response' : '',
                'status'   : 'sent',
                },
        },
        10,
        '',
        {
            'uri'          : 'https://not-a-uri.com/',
            'start_time'   : 0,
            'previous_time' : 10,
        },
    ),
    (
        None,
        None,
        10,
        '',
        None,
    ),
    (
        {
            'uri'          : 'https://not-a-uri.com/',
            'start_time'   : 0,
            'previous_time' : 9,
        },
        {
            'status_code': 200,
            'json': {
                'command'  : 'G28 X Y',
                'response' : 'ok',
                'status'   : 'ok',
                },
        },
        10,
        '',
        {
            'uri'          : 'https://not-a-uri.com/',
            'start_time'   : 0,
            'previous_time' : 9,
        },
    ),
    (
        {
            'uri'          : 'https://not-a-uri.com/',
            'start_time'   : 0,
            'previous_time' : 8,
        },
        {
            'status_code': 200,
            'json': {
                'command'  : 'G28 X Y',
                'response' : 'ok',
                'status'   : 'ok',
                },
        },
        10.1,
        'ok',
        None
    ),
    (
        {
            'uri'          : 'https://not-a-uri.com/',
            'start_time'   : 0,
            'previous_time' : None,
        },
        {
            'status_code': 200,
            'json': {
                'command'  : 'G28 X Y',
                'response' : '',
                'status'   : 'sent',
                },
        },
        121,
        '',
        None
    ),
    (
        {
            'uri'          : 'https://not-a-uri.com/',
            'start_time'   : 0,
            'previous_time' : None,
        },
        {
            'status_code': 400,
        },
        10,
        '',
        {
            'uri'          : 'https://not-a-uri.com/',
            'start_time'   : 0,
            'previous_time' : 10,
        },
    ),
    (
        {
            'uri'          : 'https://not-a-uri.com/',
            'start_time'   : 0,
            'previous_time' : None,
        },
        {
            'status_code': 400,
        },
        120.1,
        '',
        None
    ),
    (
        {
            'uri'          : 'https://not-a-uri.com/',
            'start_time'   : 0,
            'previous_time' : None,
        },
        {
            'status_code': 200,
            'json': {
                'command'  : 'G28 X Y',
                'response' : '',
                'status'   : 'printer_offline',
                },
        },
        10,
        '',
        None
    ),
    (
        {
            'uri'          : 'https://not-a-uri.com/',
            'start_time'   : 0,
            'previous_time' : None,
        },
        {
            'status_code': 200,
            'json': {
                'command'  : 'G28 X Y',
                'response' : '',
                'status'   : 'error',
                },
        },
        10,
        '',
        None
    ),
    (
        {
            'uri'          : 'https://not-a-uri.com/',
            'start_time'   : 0,
            'previous_time' : None,
        },
        {
            'status_code': 200,
            'json': {
                'command'  : 'G28 X Y',
                'response' : '',
                'status'   : 'sent',
                },
        },
        10,
        '',
        {
            'uri'          : 'https://not-a-uri.com/',
            'start_time'   : 0,
            'previous_time' : 10,
        },
    ),
    (
        {
            'uri'          : 'https://not-a-uri.com/',
            'start_time'   : 0,
            'previous_time' : None,
        },
        {
            'status_code': 200,
            'json': {
                'command'  : 'G28 X Y',
                'response' : '',
                'status'   : 'unsent',
                },
        },
        10,
        '',
        {
            'uri'          : 'https://not-a-uri.com/',
            'start_time'   : 0,
            'previous_time' : 10,
        },
    ),
])
def test_readline(comm, httpretty, mocker, command_queue, response, current_time, expected_return, expected_queue):
    mocker.patch('time.time', return_value=current_time)

    if command_queue:
        httpretty.register_uri(httpretty.GET, command_queue['uri'],
                               body=json.dumps(response.get('json')),
                               status=response['status_code'],
                               content_type='application/json')
        comm._command_uri_queue.put(command_queue)

    response = comm._readline()
    assert response == expected_return
    try:
        assert comm._command_uri_queue.get_nowait() == expected_queue
    except Queue.Empty:
        assert not expected_queue

@pytest.mark.parametrize("line, expected", [
    ('ok T:70', {'tools': [{'actual':70, 'target':None}], 'bed':None}),
    ('ok T: 80', {'tools': [{'actual':80, 'target':None}], 'bed':None}),
    ('T:70', {'tools': [{'actual':70, 'target':None}], 'bed':None}),
    ('ok T:90 B:30', {'tools': [{'actual':90, 'target':None}], 'bed':{'actual':30, 'target':None}}),
    ('ok T: 70 B: 40', {'tools': [{'actual':70, 'target':None}], 'bed':{'actual':40, 'target':None}}),
    ('ok T:70 /0 B:30 /0', {'tools': [{'actual':70, 'target':0}], 'bed':{'actual':30, 'target':0}}),
    ('T:23.61 /0 @:0 T0:23.61 /0 @0:0 RAW0:3922 T1:23.89 /0 @1:0 RAW1:3920', {'tools': [{'actual':23.61, 'target':0}, {'actual':23.89, 'target':0}], 'bed':None}),
    ('ok T:70 /190 B:30 /100 T0:70 /190 T1:90 /210', {'tools': [{'actual':70, 'target':190}, {'actual':90, 'target':210}], 'bed':{'actual':30, 'target':100}}),
    ('ok', None),
    ('something that isnt gcode', None),
    ('ok, T:7.Nooope', None),
])
def test_parse_temps(line, expected):
    actual = _comm.parse_temps(line)
    assert actual == expected
