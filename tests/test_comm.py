#pylint: disable=line-too-long, protected-access
import json
import Queue
from urlparse import urljoin

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
def test_readline(comm, httpretty, set_time, command_queue, response, current_time, expected_return, expected_queue):
    set_time(current_time)

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
def test_change_state(old_state, new_state, event, comm, connect_printer, event_manager): #pylint: disable=unused-argument
    comm._state = old_state
    comm._change_state(new_state)

    assert comm._state == new_state
    if event:
        event_manager.fire.assert_called_once_with(*event)
    else:
        assert event_manager.fire.call_count == 0

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

### TESTS FOR OTHER METHODS ###

def test_close_not_printing(comm, connect_printer, event_manager): #pylint: disable=unused-argument
    comm._state = _comm.PRINTER_STATE['OPERATIONAL']
    comm.close()

    comm._printer_status_timer.cancel.assert_called_once_with()
    comm._authentise_process.send_signal.assert_called_once_with(2)
    assert comm._state == _comm.PRINTER_STATE['CLOSED']
    event_manager.fire.assert_called_once_with(Events.DISCONNECTED)

def test_close_while_printing(comm, connect_printer, event_manager): #pylint: disable=unused-argument
    comm._print_job_uri = 'test'
    comm._state = _comm.PRINTER_STATE['PRINTING']
    comm.close()

    comm._printer_status_timer.cancel.assert_called_once_with()
    comm._authentise_process.send_signal.assert_called_once_with(2)
    assert comm._state == _comm.PRINTER_STATE['CLOSED']
    assert comm._print_job_uri == None
    event_manager.fire.assert_any_call(Events.PRINT_FAILED, None)
    event_manager.fire.assert_called_with(Events.DISCONNECTED)

@pytest.mark.parametrize("command, sent_command", [
    ('G1 X50 Y50', 'G1 X50 Y50'),
    (u'G28; HOME!!!!', 'G28'),
])
def test_send_command_printer_operational(command, sent_command, comm, connect_printer, httpretty, set_time): #pylint: disable=unused-argument
    now = 12345
    set_time(now)

    comm._state = _comm.PRINTER_STATE['OPERATIONAL']

    command_uri = urljoin(comm._printer_uri, 'command/1234-asdf/')

    httpretty.register_uri(httpretty.POST,
                           urljoin(comm._printer_uri, 'command/'),
                           adding_headers={'Location': command_uri})

    comm.sendCommand(command)
    expected = {'uri': command_uri,
            'start_time' : now,
            'previous_time' : None}
    assert comm._command_uri_queue.get_nowait() == expected
    assert httpretty.last_request().body == json.dumps({'command': sent_command})

def test_send_command_printer_not_operational(comm, connect_printer, httpretty): #pylint: disable=unused-argument
    httpretty.reset()
    comm._state = _comm.PRINTER_STATE['OFFLINE']

    comm.sendCommand('G1 X50 Y50')
    with pytest.raises(Queue.Empty):
        comm._command_uri_queue.get_nowait()
    assert not httpretty.has_request()

def test_send_command_bad_response(comm, connect_printer, httpretty): #pylint: disable=unused-argument
    comm._state = _comm.PRINTER_STATE['OPERATIONAL']

    command_uri = urljoin(comm._printer_uri, 'command/1234-asdf/')

    httpretty.register_uri(httpretty.POST,
                           urljoin(comm._printer_uri, 'command/'),
                           status=400,
                           adding_headers={'Location': command_uri})

    comm.sendCommand('G1 X50 Y50')
    with pytest.raises(Queue.Empty):
        comm._command_uri_queue.get_nowait()
    assert httpretty.last_request().body == json.dumps({'command': 'G1 X50 Y50'})


@pytest.mark.parametrize("printer_status", [
    'PRINTING',
    'PAUSED',
])
def test_cancelPrint_print_in_progress(printer_status, comm, connect_printer, httpretty): #pylint: disable=unused-argument
    comm._state = _comm.PRINTER_STATE[printer_status]
    comm._print_job_uri = 'http://test.uri.com/job/1234/'

    httpretty.register_uri(httpretty.PUT,
                           comm._print_job_uri,
                           status=204,
                           content_type='application/json')

    comm.cancelPrint()
    assert httpretty.last_request().body == json.dumps({'status': 'cancel'})

@pytest.mark.parametrize("printer_status", [
    'OFFLINE',
    'CONNECTING',
    'OPERATIONAL',
    'CLOSED',
])
def test_cancelPrint_not_printing(printer_status, comm, connect_printer, httpretty): #pylint: disable=unused-argument
    httpretty.reset()
    comm._state = _comm.PRINTER_STATE[printer_status]
    comm._print_job_uri = 'http://test.uri.com/job/1234/'

    httpretty.register_uri(httpretty.PUT,
                           comm._print_job_uri,
                           status=204,
                           content_type='application/json')

    comm.cancelPrint()
    assert not httpretty.has_request()

def test_cancelPrint_no_print_uri(comm, connect_printer, httpretty): #pylint: disable=unused-argument
    httpretty.reset()
    comm._state = _comm.PRINTER_STATE['PRINTING']
    comm._print_job_uri = None

    comm.cancelPrint()
    assert not httpretty.has_request()

def test_cancelPrint_bad_print_url(comm, connect_printer, httpretty): #pylint: disable=unused-argument
    httpretty.reset()
    comm._state = _comm.PRINTER_STATE['PRINTING']
    comm._print_job_uri = 'http://not-a-good-url/'

    comm.cancelPrint()
    assert httpretty.last_request().body == json.dumps({'status': 'cancel'})

@pytest.mark.parametrize("response, expected_state", [
    ({'status': 'new'     , 'current_print': {'status':'new'}}        , _comm.PRINTER_STATE['CONNECTING']),
    ({'status': 'OFFLINE' , 'current_print': None}                    , _comm.PRINTER_STATE['CONNECTING']),
    ({'status': 'ONLINE'  , 'current_print': None}                    , _comm.PRINTER_STATE['OPERATIONAL']),
    ({'status': 'ONLINE'  , 'current_print': {'status':'new'}}        , _comm.PRINTER_STATE['OPERATIONAL']),
    ({'status': 'ONLINE'  , 'current_print': {'status':'PRINTING'}}   , _comm.PRINTER_STATE['PRINTING']),
    ({'status': 'ONLINE'  , 'current_print': {'status':'WARMING_UP'}} , _comm.PRINTER_STATE['PRINTING']),
    ({'status': 'ONLINE'  , 'current_print': {'status':'PAUSED'}}     , _comm.PRINTER_STATE['PAUSED']),
    ({'status': 'ONLINE'  , 'current_print': {'status':'WAT?'}}       , _comm.PRINTER_STATE['OFFLINE']),
])
def test_update_state(response, expected_state, comm):
    comm._state = _comm.PRINTER_STATE['OFFLINE']
    comm._update_state(response)
    assert comm._state == expected_state

@pytest.mark.parametrize("response, expected_progress, expected_callback", [
    ({'current_print': {'status':'new'}}, None, [None, None, None, None]),
    ({'current_print': {'status':'PRINTING', 'percent_complete': 23.55, 'elapsed': 54, 'remaining': 66.3}}, {'percent_complete': 0.2355, 'elapsed': 54, 'remaining': 66.3}, [23.55, 2355, 54, 66.3]),
    ({'current_print': {'status':'WARMING_UP', 'percent_complete': 43.1, 'elapsed': 40, 'remaining': 66.3}}, {'percent_complete': 0.431, 'elapsed': 40, 'remaining': 66.3}, [43.1, 4310, 40, 66.3]),
    ({'current_print': {'status':'PAUSED', 'percent_complete': 23.56, 'elapsed': 54, 'remaining': 66.3}}, {'percent_complete': 0.2356, 'elapsed': 54, 'remaining': 66.3}, [23.56, 2356, 54, 66.3]),
])
def test_update_progress(response, expected_progress, expected_callback, comm, assert_almost_equal):
    comm._update_progress(response)
    assert_almost_equal(comm._print_progress, expected_progress)
    comm._callback.on_comm_set_progress_data.assert_called_once_with(*expected_callback)

@pytest.mark.parametrize("response, expected_temps, expected_bed", [
    ({'temperatures':{'extruder1':{'current':0}}}, {0: [0, None]}, None),
    ({'temperatures':{'extruder1':{'current':180.9, 'target':200}}}, {0: [180.9, 200]}, None),
    ({'temperatures':{'extruder1':{'current':180.9}, 'bed':{'current':30.5, 'target':50.1}}}, {0: [180.9, None]}, [30.5, 50.1]),
])
def test_update_temps(response, expected_temps, expected_bed, comm):
    comm._update_temps(response)
    assert comm._tool_tempuratures == expected_temps
    assert comm._bed_tempurature == expected_bed

def test_update_printer_data_ok_response(comm, connect_printer, httpretty, assert_almost_equal): #pylint: disable=unused-argument
    comm._state = _comm.PRINTER_STATE['CONNECTING']
    comm._tool_tempuratures = None
    comm._bed_tempurature = None
    comm._print_progress = None

    printer_payload = {"baud_rate": 250000,
                       "port": "/dev/tty.derp",
                       "uri": comm._printer_uri,
                       'status': 'ONLINE',
                       'temperatures':{'extruder1': {'current':185.9}},
                       'current_print': {
                           'status': 'PRINTING',
                           'percent_complete': 10.55,
                           'elapsed': 30,
                           'remaining': 0.4,
                           'job_uri': 'http://some-job-uri.com/',
                       }}

    httpretty.register_uri(httpretty.GET,
                           comm._printer_uri,
                           status=200,
                           body=json.dumps(printer_payload),
                           content_type='application/json')

    comm._update_printer_data()

    assert comm._state == _comm.PRINTER_STATE['PRINTING']
    assert comm._tool_tempuratures == {0: [185.9, None]}
    assert comm._bed_tempurature == None
    assert comm._print_job_uri == 'http://some-job-uri.com/'
    assert_almost_equal(comm._print_progress, {'percent_complete': 0.1055, 'elapsed': 30, 'remaining': 0.4})

def test_update_printer_data_not_printing(comm, connect_printer, httpretty, assert_almost_equal): #pylint: disable=unused-argument
    comm._state = _comm.PRINTER_STATE['CONNECTING']
    comm._tool_tempuratures = None
    comm._bed_tempurature = None
    comm._print_progress = None
    comm._print_job_uri = 'http://some-job-uri.com/'

    printer_payload = {"baud_rate": 250000,
                       "port": "/dev/tty.derp",
                       "uri": comm._printer_uri,
                       'status': 'ONLINE',
                       'temperatures':{'extruder1': {'current':185.9}},
                       'current_print': None}

    httpretty.register_uri(httpretty.GET,
                           comm._printer_uri,
                           status=200,
                           body=json.dumps(printer_payload),
                           content_type='application/json')

    comm._update_printer_data()

    assert comm._state == _comm.PRINTER_STATE['OPERATIONAL']
    assert comm._tool_tempuratures == {0: [185.9, None]}
    assert comm._bed_tempurature == None
    assert comm._print_job_uri == None
    assert comm._print_progress == None

def test_update_printer_data_bad_response(comm, connect_printer, httpretty): #pylint: disable=unused-argument
    comm._state = _comm.PRINTER_STATE['CONNECTING']
    comm._tool_tempuratures = None
    comm._bed_tempurature = None
    comm._print_progress = None

    printer_payload = {}

    httpretty.register_uri(httpretty.GET,
                           comm._printer_uri,
                           status=400,
                           body=json.dumps(printer_payload),
                           content_type='application/json')

    comm._update_printer_data()

    assert comm._state == _comm.PRINTER_STATE['CONNECTING']
    assert comm._tool_tempuratures == None
    assert comm._bed_tempurature == None
    assert comm._print_progress == None
    assert comm._print_job_uri == None

def test_update_printer_data_no_print_uri(comm):
    comm._state = _comm.PRINTER_STATE['CONNECTING']
    comm._printer_uri = None
    comm._tool_tempuratures = None
    comm._bed_tempurature = None
    comm._print_progress = None

    comm._update_printer_data()

    assert comm._state == _comm.PRINTER_STATE['CONNECTING']
    assert comm._tool_tempuratures == None
    assert comm._bed_tempurature == None
    assert comm._print_progress == None
    assert comm._print_job_uri == None
