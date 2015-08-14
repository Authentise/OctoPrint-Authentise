#pylint: disable=line-too-long, protected-access
import json
import Queue

import pytest
from octoprint.events import Events

from octoprint_authentise import comm as _comm


# tests case in which the user has no authentise printers
def test_printer_connect_create_authentise_printer(comm, printer, httpretty, mocker):
    httpretty.register_uri(httpretty.GET,
                           printer['request_url'],
                           body=json.dumps({"resources": []}),
                           content_type='application/json')

    httpretty.register_uri(httpretty.POST, printer['request_url'],
                           adding_headers={"Location": printer['uri']})

    # keep authentise and monitoring threads from actually starting
    mocker.patch('octoprint_authentise.comm.threading.Thread')
    mocker.patch('octoprint_authentise.comm.RepeatedTimer')
    mocker.patch("octoprint_authentise.comm.helpers.run_client")

    comm.connect(port="1234", baudrate=5678)

    assert comm.getState() == _comm.PRINTER_STATE['CONNECTING']
    assert comm._printer_uri == printer['uri']


# tests case in which the user has a printer on the right port, but the baud rate is wrong
def test_printer_connect_get_authentise_printer(comm, printer, httpretty, mocker,):
    httpretty.register_uri(httpretty.POST, printer['request_url'],
                           adding_headers={"Location": printer['uri']})

    httpretty.register_uri(httpretty.PUT, printer['uri'])


    # keep authentise and monitoring threads from actually starting
    mocker.patch('octoprint_authentise.comm.threading.Thread')
    mocker.patch('octoprint_authentise.comm.RepeatedTimer')
    mocker.patch("octoprint_authentise.comm.helpers.run_client")

    comm.connect(port="/dev/tty.derp", baudrate=5678)

    assert comm.getState() == _comm.PRINTER_STATE['CONNECTING']
    assert comm._printer_uri == printer['uri']


# tests case in which port and baud rate are just right
def test_printer_connect_get_authentise_printer_no_put(comm, printer, mocker):
    # keep authentise and monitoring threads from actually starting
    mocker.patch('octoprint_authentise.comm.threading.Thread')
    mocker.patch('octoprint_authentise.comm.RepeatedTimer')
    mocker.patch("octoprint_authentise.comm.helpers.run_client")

    comm.connect(port="/dev/tty.derp", baudrate=250000)

    assert comm.getState() == _comm.PRINTER_STATE['CONNECTING']
    assert comm._printer_uri == printer['uri']

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
]) #pylint: disable=too-many-arguments
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
    ('ok T:7.Nooope', None),
    ('ok T:219.0 /220.0 T0:219.0 /220.0 @:72 B@:0', {'tools': [{'actual':219.0, 'target':220}], 'bed':None}),
])
def test_parse_temps(line, expected):
    actual = _comm.parse_temps(line)
    assert actual == expected

@pytest.mark.parametrize("old_state, new_state, event", [
    (_comm.PRINTER_STATE['OFFLINE'], _comm.PRINTER_STATE['CONNECTING'], None),
    (_comm.PRINTER_STATE['CONNECTING'], _comm.PRINTER_STATE['OPERATIONAL'], (Events.CONNECTED, {'port':'/dev/tty.derp', 'baudrate':250000})),
    (_comm.PRINTER_STATE['PRINTING'], _comm.PRINTER_STATE['PAUSED'], (Events.PRINT_PAUSED, None)),
    (_comm.PRINTER_STATE['PAUSED'], _comm.PRINTER_STATE['PRINTING'], (Events.PRINT_RESUMED, None)),
    (_comm.PRINTER_STATE['OPERATIONAL'], _comm.PRINTER_STATE['PRINTING'], (Events.PRINT_STARTED, None)),
    (_comm.PRINTER_STATE['PRINTING'], _comm.PRINTER_STATE['OPERATIONAL'], (Events.PRINT_DONE, None)),
    (_comm.PRINTER_STATE['OPERATIONAL'], _comm.PRINTER_STATE['CLOSED'], (Events.DISCONNECTED,)),
    (_comm.PRINTER_STATE['OPERATIONAL'], _comm.PRINTER_STATE['ERROR'], (Events.ERROR, {'error': None})),
    (_comm.PRINTER_STATE['OPERATIONAL'], _comm.PRINTER_STATE['CLOSED_WITH_ERROR'], (Events.ERROR, {'error': None})),
])
def test_change_state(old_state, new_state, event, comm, connect_printer, mocker): #pylint: disable=unused-argument
    event_fire_mock = mocker.Mock()
    mocker.patch('octoprint_authentise.comm.eventManager', return_value=mocker.Mock(fire=event_fire_mock))

    comm._state = old_state
    comm._change_state(new_state)

    assert comm._state == new_state
    if event:
        event_fire_mock.assert_called_once_with(*event)
    else:
        assert event_fire_mock.call_count == 0

### TESTS FOR VARIOUS GETTERS ###
def test_getState(comm):
    comm._state = _comm.PRINTER_STATE['OPERATIONAL']
    assert comm.getState() == _comm.PRINTER_STATE['OPERATIONAL']

@pytest.mark.parametrize("state, state_string", [
    (_comm.PRINTER_STATE['OFFLINE'], 'Offline'),
    (_comm.PRINTER_STATE['CONNECTING'], 'Connecting'),
    (_comm.PRINTER_STATE['OPERATIONAL'], 'Operational'),
    (_comm.PRINTER_STATE['PRINTING'], 'Printing'),
    (_comm.PRINTER_STATE['PAUSED'], 'Paused'),
    (_comm.PRINTER_STATE['CLOSED'], 'Closed'),
    (_comm.PRINTER_STATE['ERROR'], 'Error: None'),
    (_comm.PRINTER_STATE['CLOSED_WITH_ERROR'], 'Error: None'),
])
def test_getStateString(comm, state, state_string):
    comm._state = state
    assert comm.getStateString() == state_string

def test_getErrorString(comm):
    comm._errorValue = 'some error!'
    assert comm.getErrorString() == 'some error!'

@pytest.mark.parametrize("state, result", [
    (_comm.PRINTER_STATE['OFFLINE'], False),
    (_comm.PRINTER_STATE['CONNECTING'], False),
    (_comm.PRINTER_STATE['OPERATIONAL'], False),
    (_comm.PRINTER_STATE['PRINTING'], False),
    (_comm.PRINTER_STATE['PAUSED'], False),
    (_comm.PRINTER_STATE['CLOSED'], True),
    (_comm.PRINTER_STATE['ERROR'], True),
    (_comm.PRINTER_STATE['CLOSED_WITH_ERROR'], True),
])
def test_isClosedOrError(state, result, comm):
    comm._state = state
    assert comm.isClosedOrError() == result

@pytest.mark.parametrize("state, result", [
    (_comm.PRINTER_STATE['OFFLINE'], False),
    (_comm.PRINTER_STATE['CONNECTING'], False),
    (_comm.PRINTER_STATE['OPERATIONAL'], False),
    (_comm.PRINTER_STATE['PRINTING'], False),
    (_comm.PRINTER_STATE['PAUSED'], False),
    (_comm.PRINTER_STATE['CLOSED'], False),
    (_comm.PRINTER_STATE['ERROR'], True),
    (_comm.PRINTER_STATE['CLOSED_WITH_ERROR'], True),
])
def test_isError(state, result, comm):
    comm._state = state
    assert comm.isError() == result

@pytest.mark.parametrize("state, result", [
    (_comm.PRINTER_STATE['OFFLINE'], False),
    (_comm.PRINTER_STATE['CONNECTING'], False),
    (_comm.PRINTER_STATE['OPERATIONAL'], True),
    (_comm.PRINTER_STATE['PRINTING'], True),
    (_comm.PRINTER_STATE['PAUSED'], True),
    (_comm.PRINTER_STATE['CLOSED'], False),
    (_comm.PRINTER_STATE['ERROR'], False),
    (_comm.PRINTER_STATE['CLOSED_WITH_ERROR'], False),
])
def test_isOperational(state, result, comm):
    comm._state = state
    assert comm.isOperational() == result

@pytest.mark.parametrize("state, result", [
    (_comm.PRINTER_STATE['OFFLINE'], False),
    (_comm.PRINTER_STATE['CONNECTING'], False),
    (_comm.PRINTER_STATE['OPERATIONAL'], False),
    (_comm.PRINTER_STATE['PRINTING'], True),
    (_comm.PRINTER_STATE['PAUSED'], False),
    (_comm.PRINTER_STATE['CLOSED'], False),
    (_comm.PRINTER_STATE['ERROR'], False),
    (_comm.PRINTER_STATE['CLOSED_WITH_ERROR'], False),
])
def test_isPrinting(state, result, comm):
    comm._state = state
    assert comm.isPrinting() == result

@pytest.mark.parametrize("state, result", [
    (_comm.PRINTER_STATE['OFFLINE'], False),
    (_comm.PRINTER_STATE['CONNECTING'], False),
    (_comm.PRINTER_STATE['OPERATIONAL'], False),
    (_comm.PRINTER_STATE['PRINTING'], False),
    (_comm.PRINTER_STATE['PAUSED'], True),
    (_comm.PRINTER_STATE['CLOSED'], False),
    (_comm.PRINTER_STATE['ERROR'], False),
    (_comm.PRINTER_STATE['CLOSED_WITH_ERROR'], False),
])
def test_isPaused(state, result, comm):
    comm._state = state
    assert comm.isPaused() == result

@pytest.mark.parametrize("state, result", [
    (_comm.PRINTER_STATE['OFFLINE'], False),
    (_comm.PRINTER_STATE['CONNECTING'], False),
    (_comm.PRINTER_STATE['OPERATIONAL'], False),
    (_comm.PRINTER_STATE['PRINTING'], True),
    (_comm.PRINTER_STATE['PAUSED'], True),
    (_comm.PRINTER_STATE['CLOSED'], False),
    (_comm.PRINTER_STATE['ERROR'], False),
    (_comm.PRINTER_STATE['CLOSED_WITH_ERROR'], False),
])
def test_isBusy(state, result, comm):
    comm._state = state
    assert comm.isBusy() == result

@pytest.mark.parametrize("state, result", [
    (_comm.PRINTER_STATE['OFFLINE'], False),
    (_comm.PRINTER_STATE['CONNECTING'], False),
    (_comm.PRINTER_STATE['OPERATIONAL'], False),
    (_comm.PRINTER_STATE['PRINTING'], False),
    (_comm.PRINTER_STATE['PAUSED'], False),
    (_comm.PRINTER_STATE['CLOSED'], False),
    (_comm.PRINTER_STATE['ERROR'], False),
    (_comm.PRINTER_STATE['CLOSED_WITH_ERROR'], False),
])
def test_isStreaming_isSdReady_isSdFileSelected_isSdPrinting(state, result, comm):
    comm._state = state
    assert comm.isStreaming() == result
    assert comm.isSdReady() == result
    assert comm.isSdFileSelected() == result
    assert comm.isSdPrinting() == result

def test_getSdFiles(comm):
    assert not comm.getSdFiles()

@pytest.mark.parametrize("progress, percent, time", [
    ({'percent_complete': 0.112, 'elapsed': 54}, 0.112, 54),
    (None, None, None),
])
def test_getPrintProgress_getPrintTime_getCleanedPrintTime(progress, percent, time, comm):
    comm._print_progress = progress
    assert comm.getPrintProgress() == percent
    assert comm.getPrintTime() == time
    assert comm.getCleanedPrintTime() == time

def test_getPrintFilepos(comm):
    assert not comm.getPrintFilepos()

def test_getTemp(comm):
    comm._tool_tempuratures = {0: [210.5, 215]}
    assert comm.getTemp() == {0: [210.5, 215]}

def test_getBedTemp(comm):
    comm._bed_tempurature = [210.5, 215]
    assert comm.getBedTemp() == [210.5, 215]

def test_getOffsets(comm):
    assert comm.getOffsets() == {}

def test_getCurrentTool(comm):
    assert comm.getCurrentTool() == 0

def test_getConnection(comm, connect_printer): #pylint: disable=unused-argument
    assert comm.getConnection() == ('/dev/tty.derp', 250000)

def test_getTransport(comm):
    assert not comm.getTransport()
