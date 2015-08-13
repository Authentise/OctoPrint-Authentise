# coding=utf-8
from __future__ import absolute_import

import logging
import Queue
import re
import threading
import time
import urlparse
from urllib import quote_plus

import octoprint.plugin
from octoprint.events import Events, eventManager
from octoprint.settings import settings
from octoprint.util import RepeatedTimer, comm_helpers, get_exception_string

from octoprint_authentise import helpers

__author__ = "Scott Lemmon <scott@authentise.com> based on work by Gina Häußge"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 Authentise - Released under terms of the AGPLv3 License"


FLOAT_RE = r'[-+]?\d*\.?\d+'
JUNK_RE = r'(?:\s+.*?\s*)?'
TEMP_RE = re.compile(
        r'^(?:ok)?\s*T:\s*(?P<T>{float})(?:\s*/(?P<TT>{float}))?'
        r'(?:{junk}\s*B:\s*(?P<B>{float})(?:\s*/(?P<TB>{float}))?)?'
        r'(?:{junk}\s*T0:\s*(?P<T0>{float})(?:\s*/(?P<TT0>{float}))?)?'
        r'(?:{junk}\s*T1:\s*(?P<T1>{float})(?:\s*/(?P<TT1>{float}))?)?'
        r'{junk}$'.format(float=FLOAT_RE, junk=JUNK_RE)
)
def parse_temps(line):
    def _cast_to_float(value):
        if value:
            try:
                return float(value)
            except ValueError:
                return

    match = TEMP_RE.match(line)
    if not match:
        return

    tools = []
    bed = None

    tool0_actual = _cast_to_float(match.group('T0') or match.group('T'))
    tool0_target = _cast_to_float(match.group('TT0') or match.group('TT'))
    tools.append({'actual': tool0_actual, 'target': tool0_target})

    tool1_actual = _cast_to_float(match.group('T1'))
    tool1_target = _cast_to_float(match.group('TT1'))
    if tool1_actual:
        tools.append({'actual': tool1_actual, 'target': tool1_target})

    bed_actual = _cast_to_float(match.group('B'))
    bed_target = _cast_to_float(match.group('TB'))
    if bed_actual:
        bed = {'actual': bed_actual, 'target': bed_target}

    return {'tools': tools, 'bed': bed}


class MachineCom(octoprint.plugin.MachineComPlugin): #pylint: disable=too-many-instance-attributes, too-many-public-methods
    _logger = None
    _serialLogger = None

    _state = None

    _port = None
    _baudrate = None
    _printer_uri = None

    _authentise_process = None
    _authentise_model = None

    _authentise_url = None
    _session = None

    _command_uri_queue = None

    _temperature_timer = None

    _callback = None
    _printer_profile_manager = None

    monitoring_thread = None
    _monitoring_active = False

    _errorValue = None

    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._serialLogger = logging.getLogger("SERIAL")

        self._command_uri_queue = comm_helpers.TypedQueue()

        self._state = self.STATE_NONE

    def startup(self, callbackObject=None, printerProfileManager=None):
        if callbackObject == None:
            callbackObject = comm_helpers.MachineComPrintCallback()

        self._callback = callbackObject

        self._printer_profile_manager = printerProfileManager

        self._authentise_url = self._settings.get(['authentise_url']) #pylint: disable=no-member
        self._session = helpers.session(self._settings) #pylint: disable=no-member

    def connect(self, port=None, baudrate=None):
        if port == None:
            port = settings().get(["serial", "port"])
        if baudrate == None:
            settings_baudrate = settings().getInt(["serial", "baudrate"])
            if settings_baudrate is None:
                baudrate = 0
            else:
                baudrate = settings_baudrate

        self._port = port
        self._baudrate = baudrate
        self._printer_uri = self._get_or_create_printer(port, baudrate)

        self._authentise_process = helpers.run_client(self._settings) #pylint: disable=no-member

        # monitoring thread
        self._monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitor_loop, name="comm._monitor")
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()

        self._temperature_timer = RepeatedTimer(
            lambda: comm_helpers.get_interval("temperature", default_value=4.0),
            self._poll_temperature,
            run_first=True
        )
        self._temperature_timer.start()

        payload = dict(port=self._port, baudrate=self._baudrate)
        self._changeState(self.STATE_OPERATIONAL)

        eventManager().fire(Events.CONNECTED, payload)

    def _get_or_create_printer(self, port, baud_rate):
        client_url = urlparse.urljoin(self._authentise_url, '/client/{}/'.format(self.node_uuid)) #pylint: disable=no-member

        url = urlparse.urljoin(self._authentise_url,
                               '/printer/instance/?filter[client]={}'.format(quote_plus(client_url)))
        target_printer = None
        self._log('Getting printer list from: {}'.format(url))

        printer_get_resp = self._session.get(url=url)

        for printer in printer_get_resp.json()["resources"]:
            if printer['port'] == port:
                target_printer = printer
                self._log('Printer {} matches selected port {}'.format(printer, port))
                break

        if target_printer:
            if target_printer['baud_rate'] != baud_rate:
                self._session.put(target_printer["uri"], json={'baud_rate': baud_rate})

            return target_printer['uri']
        else:
            self._log('No printer found for port {}. Creating it.'.format(port))

            payload = {'client': client_url,
                       'printer_model': 'https://print.dev-auth.com/printer/model/9/',
                       'name': 'Octoprint Printer',
                       'port': port,
                       'baud_rate': baud_rate}
            create_printer_resp = self._session.post(urlparse.urljoin(self._authentise_url,
                                                                 '/printer/instance/'),
                                                json=payload)
            return create_printer_resp.headers["Location"]

    # #~~ internal state management

    def _changeState(self, newState):
        if self._state == newState:
            return

        oldState = self.getStateString()
        self._state = newState
        self._log('Changing monitoring state from \'%s\' to \'%s\'' % (oldState, self.getStateString()))
        self._callback.on_comm_state_change(newState)

    def _log(self, message):
        self._callback.on_comm_log(message)
        self._serialLogger.debug(message)

    ##~~ getters

    def getState(self):
        return self._state

    def getStateString(self): #pylint: disable=too-many-return-statements
        if self._state == self.STATE_NONE:
            return "Offline"
        if self._state == self.STATE_OPEN_SERIAL:
            return "Opening serial port"
        if self._state == self.STATE_DETECT_SERIAL:
            return "Detecting serial port"
        if self._state == self.STATE_DETECT_BAUDRATE:
            return "Detecting baudrate"
        if self._state == self.STATE_CONNECTING:
            return "Connecting"
        if self._state == self.STATE_OPERATIONAL:
            return "Operational"
        if self._state == self.STATE_PRINTING:
            return "Printing"
        if self._state == self.STATE_PAUSED:
            return "Paused"
        if self._state == self.STATE_CLOSED:
            return "Closed"
        if self._state == self.STATE_ERROR:
            return "Error: %s" % (self.getErrorString())
        if self._state == self.STATE_CLOSED_WITH_ERROR:
            return "Error: %s" % (self.getErrorString())
        if self._state == self.STATE_TRANSFERING_FILE:
            return "Transfering file to SD"
        return "?%d?" % (self._state)

    def getErrorString(self):
        return self._errorValue

    def isClosedOrError(self):
        return self._state == self.STATE_ERROR or self._state == self.STATE_CLOSED_WITH_ERROR or self._state == self.STATE_CLOSED

    def isError(self):
        return self._state == self.STATE_ERROR or self._state == self.STATE_CLOSED_WITH_ERROR

    def isOperational(self):
        return (self._state == self.STATE_OPERATIONAL
                or self._state == self.STATE_PRINTING
                or self._state == self.STATE_PAUSED
                or self._state == self.STATE_TRANSFERING_FILE)

    def isPrinting(self):
        return self._state == self.STATE_PRINTING

    def isStreaming(self):
        return self._authentise_model is not None

    def isPaused(self):
        return self._state == self.STATE_PAUSED

    def isBusy(self):
        return self.isPrinting() or self.isPaused()

    def isSdReady(self):
        return

    def isSdFileSelected(self):
        return

    def isSdPrinting(self):
        return

    def getSdFiles(self):
        return

    def getPrintProgress(self):
        return

    def getPrintFilepos(self):
        return

    def getPrintTime(self):
        return

    def getCleanedPrintTime(self):
        return

    def getTemp(self):
        return

    def getBedTemp(self):
        return

    def getOffsets(self):
        return {}

    def getCurrentTool(self):
        return 0

    def getConnection(self):
        return self._port, self._baudrate

    def getTransport(self):
        return

    ##~~ external interface

    def close(self, isError = False):
        if self._temperature_timer:
            self._temperature_timer.cancel()

        self._monitoring_active = False

        printing = self.isPrinting() or self.isPaused()

        if printing:
            eventManager().fire(Events.PRINT_FAILED, None)

        # close the Authentise client if it is open
        if self._authentise_process:
            self._authentise_process.send_signal(2) #send the SIGINT signal

        self._changeState(self.STATE_CLOSED)
        eventManager().fire(Events.DISCONNECTED)

    def setTemperatureOffset(self, offsets):
        return

    def fakeOk(self):
        return

    def sendCommand(self, cmd, cmd_type=None, processed=False):
        cmd = cmd.encode('ascii', 'replace')
        if not processed:
            cmd = comm_helpers.process_gcode_line(cmd)
            if not cmd:
                return

        if self.isPrinting() or self.isOperational():
            data = {'command': cmd}
            printer_command_url = urlparse.urljoin(self._printer_uri, 'command/')

            response = self._session.post(printer_command_url, json=data)
            if not response.ok:
                self._log(
                    'Warning: Got invalid response {}: {} for {}: {}'.format(
                        response.status_code,
                        response.content,
                        response.request.url,
                        response.request.body))
                return

            self._log(
                'Sent {} to {} with response {}: {}'.format(
                    response.request.body,
                    response.request.url,
                    response.status_code,
                    response.content))
            command_uri = response.headers['Location']
            self._command_uri_queue.put({
                'uri'           : command_uri,
                'start_time'    : time.time(),
                'previous_time' : None,
            })

    def startPrint(self):
        if not self.isOperational() or self.isPrinting():
            return

        try:
            payload = {}
            self._session.post('http://print.authentise.com/print/', json=payload)

            self._changeState(self.STATE_PRINTING)
            eventManager().fire(Events.PRINT_STARTED, None)

        except: #pylint: disable=bare-except
            self._logger.exception("Error while trying to start printing")
            self._errorValue = get_exception_string()
            self._changeState(self.STATE_ERROR)
            eventManager().fire(Events.ERROR, {"error": self.getErrorString()})

    def selectFile(self, model_uri, sd):
        if self.isBusy():
            return

        self._authentise_model = {
                'uri': model_uri,
                'name': None,
                'snapshot': None,
                'content': None,
                'manifold': None,
                }

        response = requests.get(model_uri)
        if response.ok:
            model_data = response.json()
            self._authentise_model['name'] = model_data['name']
            self._authentise_model['status'] = model_data['status']
            self._authentise_model['snapshot'] = model_data['snapshot']
            self._authentise_model['content'] = model_data['content']
            self._authentise_model['manifold'] = model_data['analyses']['manifold']

        eventManager().fire(Events.FILE_SELECTED, {
            "file": self._authentise_model['name'],
            "filename": self._authentise_model['name'],
            "origin": self._authentise_model['uri'],
        })
        self._callback.on_comm_file_selected(model_uri, 0, False)

    def unselectFile(self):
        if self.isBusy():
            return

        self._authentise_model = None
        eventManager().fire(Events.FILE_DESELECTED)
        self._callback.on_comm_file_selected(None, None, False)

    def cancelPrint(self):
        if not self.isOperational() or self.isStreaming():
            return

        if not self._authentise_model:
            return

        self._changeState(self.STATE_OPERATIONAL)

        payload = {
            "file": self._authentise_model['name'],
            "filename": self._authentise_model['name'],
            "origin": self._authentise_model['uri'],
        }

        eventManager().fire(Events.PRINT_CANCELLED, payload)

    def setPause(self, pause):
        if self.isStreaming():
            return

        if not self._authentise_model:
            return

        payload = {
            "file": self._authentise_model['name'],
            "filename": self._authentise_model['name'],
            "origin": self._authentise_model['uri'],
        }

        if not pause and self.isPaused():
            self._changeState(self.STATE_PRINTING)

            eventManager().fire(Events.PRINT_RESUMED, payload)
        elif pause and self.isPrinting():
            self._changeState(self.STATE_PAUSED)

            eventManager().fire(Events.PRINT_PAUSED, payload)

    def sendGcodeScript(self, scriptName, replacements=None):
        return

    def startFileTransfer(self, filename, localFilename, remoteFilename):
        return

    def startSdFileTransfer(self, filename):
        return

    def endSdFileTransfer(self, filename):
        return

    def deleteSdFile(self, filename):
        return

    def refreshSdFiles(self):
        return

    def initSdCard(self):
        return

    def releaseSdCard(self):
        return

    ##~~ Serial monitor processing received messages

    def _readline(self):
        def _put_command_on_queue(data, start_time_diff):
            if start_time_diff < 120:
                self._command_uri_queue.put(data)

        current_time = time.time()

        try:
            command = self._command_uri_queue.get_nowait()
        except Queue.Empty:
            return ''

        start_time    = command['start_time']
        previous_time = command['previous_time']
        command_uri   = command['uri']

        start_time_diff = current_time - start_time
        previous_time_diff = (current_time - previous_time) if previous_time else start_time_diff

        if previous_time_diff < 2:
            _put_command_on_queue({
                'uri'           : command_uri,
                'start_time'    : start_time,
                'previous_time' : previous_time,
            }, start_time_diff)
            return ''

        response = self._session.get(command_uri)

        if response.ok and response.json()['status'] in ['error', 'printer_offline']:
            return ''
        elif not response.ok or response.json()['status'] != 'ok':
            _put_command_on_queue({
                'uri'           : command_uri,
                'start_time'    : start_time,
                'previous_time' : current_time,
            }, start_time_diff)
            return ''

        command_response = response.json()
        self._log('Got response: {}, for command: {}'.format(command_response['response'], command_response['command']))
        return command_response['response']

    def _get_printer_status(self):
        pass

    def _monitor_loop(self):

        self._log("Connected, starting monitor")

        while self._monitoring_active:
            try:
                line = self._readline()

                if not line:
                    continue

                temps = parse_temps(line)
                if temps:
                    tool_temps = {i: [temp['actual'], temp['target']] for i, temp in enumerate(temps['tools'])}
                    bed_temp = (temps['bed']['actual'], temps['bed']['target']) if temps['bed'] else None
                    self._callback.on_comm_temperature_update(tool_temps, bed_temp)
                self._callback.on_comm_message(line)

            except: #pylint: disable=bare-except
                self._logger.exception("Something crashed inside the serial connection loop,"
                        " please report this in OctoPrint's bug tracker:")
                errorMsg = "See octoprint.log for details"
                self._log(errorMsg)
                self._errorValue = errorMsg
                self._changeState(self.STATE_ERROR)
                eventManager().fire(Events.ERROR, {"error": self.getErrorString()})
            time.sleep(0.1)
        self._log("Connection closed, closing down monitor")

    def _poll_temperature(self):
        if self.isOperational():
            self.sendCommand("M105", cmd_type="temperature_poll")
