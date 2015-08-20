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
import requests
from octoprint.events import Events, eventManager
from octoprint.settings import settings
from octoprint.util import RepeatedTimer, comm_helpers

from octoprint_authentise import helpers

__author__ = "Scott Lemmon <scott@authentise.com> based on work by Gina Häußge"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 Authentise - Released under terms of the AGPLv3 License"

PRINTER_STATE = {
    'OFFLINE'           : octoprint.plugin.MachineComPlugin.STATE_NONE,
    'CONNECTING'        : octoprint.plugin.MachineComPlugin.STATE_CONNECTING,
    'OPERATIONAL'       : octoprint.plugin.MachineComPlugin.STATE_OPERATIONAL,
    'PRINTING'          : octoprint.plugin.MachineComPlugin.STATE_PRINTING,
    'PAUSED'            : octoprint.plugin.MachineComPlugin.STATE_PAUSED,
    'CLOSED'            : octoprint.plugin.MachineComPlugin.STATE_CLOSED,
    'ERROR'             : octoprint.plugin.MachineComPlugin.STATE_ERROR,
    'CLOSED_WITH_ERROR' : octoprint.plugin.MachineComPlugin.STATE_CLOSED_WITH_ERROR,
    }
PRINTER_STATE_REVERSE = dict((v,k) for k,v in PRINTER_STATE.items())

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
    _print_job_uri = None

    _authentise_process = None
    _authentise_model = None

    _authentise_url = None
    _session = None

    _command_uri_queue = None

    _printer_status_timer = None
    _tool_tempuratures = None
    _bed_tempurature = None

    _print_progress = None

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

        self._printer_status_timer = RepeatedTimer(
            lambda: comm_helpers.get_interval("temperature", default_value=10.0),
            self._update_printer_data,
            run_first=True
        )
        self._printer_status_timer.start()

        self._change_state(PRINTER_STATE['CONNECTING'])

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

    def _change_state(self, new_state):
        # Change the printer state
        if self._state == new_state:
            return

        old_state = self._state
        old_state_string = self.getStateString()
        self._state = new_state
        self._log("Changed printer state from '{}' to '{}'".format(old_state_string, self.getStateString()))
        self._callback.on_comm_state_change(new_state)

        # Deal with firing nessesary events
        if new_state in [PRINTER_STATE['OPERATIONAL'], PRINTER_STATE['PRINTING'], PRINTER_STATE['PAUSED']]:
            # Send connected event if needed
            if old_state == PRINTER_STATE['CONNECTING']:
                payload = dict(port=self._port, baudrate=self._baudrate)
                eventManager().fire(Events.CONNECTED, payload)

            # Pausing and resuming printing
            if new_state == PRINTER_STATE['PAUSED']:
                eventManager().fire(Events.PRINT_PAUSED, None)
            elif new_state == PRINTER_STATE['PRINTING'] and old_state == PRINTER_STATE['PAUSED']:
                eventManager().fire(Events.PRINT_RESUMED, None)

            # New print
            elif new_state == PRINTER_STATE['PRINTING']:
                eventManager().fire(Events.PRINT_STARTED, None)
                self._callback.on_comm_set_job_data('Authentise Streaming Print', 10000, None)

            # It is not easy to tell the difference between an completed print and a cancled print at this point
            elif new_state == PRINTER_STATE['OPERATIONAL'] and old_state != PRINTER_STATE['CONNECTING']:
                eventManager().fire(Events.PRINT_DONE, None)
                self._callback.on_comm_set_job_data(None, None, None)

        elif new_state == PRINTER_STATE['CLOSED']:
            eventManager().fire(Events.DISCONNECTED)

        elif new_state in [PRINTER_STATE['ERROR'], PRINTER_STATE['CLOSED_WITH_ERROR']]:
            eventManager().fire(Events.ERROR, {"error": self.getErrorString()})

    def _log(self, message):
        self._callback.on_comm_log(message)
        self._serialLogger.debug(message)

    ##~~ getters

    def getState(self):
        return self._state

    def getStateString(self): #pylint: disable=too-many-return-statements
        if self._state in [PRINTER_STATE['ERROR'], PRINTER_STATE['CLOSED_WITH_ERROR']]:
            return "Error: {}".format(self.getErrorString())

        return PRINTER_STATE_REVERSE[self._state].title()

    def getErrorString(self):
        return self._errorValue

    def isClosedOrError(self):
        return self._state in [PRINTER_STATE['ERROR'], PRINTER_STATE['CLOSED_WITH_ERROR'], PRINTER_STATE['CLOSED']]

    def isError(self):
        return self._state in [PRINTER_STATE['ERROR'], PRINTER_STATE['CLOSED_WITH_ERROR']]

    def isOperational(self):
        return self._state in [ PRINTER_STATE['OPERATIONAL'], PRINTER_STATE['PRINTING'], PRINTER_STATE['PAUSED']]

    def isPrinting(self):
        return self._state == PRINTER_STATE['PRINTING']

    def isStreaming(self):
        return False

    def isPaused(self):
        return self._state == PRINTER_STATE['PAUSED']

    def isBusy(self):
        return self.isPrinting() or self.isPaused()

    def isSdReady(self):
        return False

    def isSdFileSelected(self):
        return False

    def isSdPrinting(self):
        return False

    def getSdFiles(self):
        return

    def getPrintProgress(self):
        return self._print_progress['percent_complete'] if self._print_progress else None

    def getPrintFilepos(self):
        return int(self._print_progress['percent_complete']*10000) if self._print_progress else None

    def getPrintTime(self):
        return self._print_progress['elapsed'] if self._print_progress else None

    def getCleanedPrintTime(self):
        return self._print_progress['elapsed'] if self._print_progress else None

    def getTemp(self):
        return self._tool_tempuratures

    def getBedTemp(self):
        return self._bed_tempurature

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
        if self._printer_status_timer:
            self._printer_status_timer.cancel()

        self._monitoring_active = False

        printing = self.isPrinting() or self.isPaused()

        if printing:
            eventManager().fire(Events.PRINT_FAILED, None)

        # close the Authentise client if it is open
        if self._authentise_process:
            self._authentise_process.send_signal(2) #send the SIGINT signal

        self._print_job_uri = None
        self._change_state(PRINTER_STATE['CLOSED'])

    def setTemperatureOffset(self, offsets):
        pass

    def fakeOk(self):
        pass

    def sendCommand(self, cmd, cmd_type=None, processed=False):
        cmd = cmd.encode('ascii', 'replace')
        if not processed:
            cmd = comm_helpers.process_gcode_line(cmd)
            if not cmd:
                return

        if self.isOperational():
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
        pass

    def selectFile(self, model_uri, sd):
        pass

    def unselectFile(self):
        pass

    def _send_pause_cancel_request(self, status):
        try:
            response = self._session.put(self._print_job_uri, json={'status':status})
        except (requests.exceptions.MissingSchema, requests.exceptions.ConnectionError) as e:
            self._log('Request to {} generated error: {}'.format(self._print_job_uri, e))
            response = None

        if response and response.ok:
            status_map = {
                    'cancel': PRINTER_STATE['OPERATIONAL'],
                    'pause': PRINTER_STATE['PAUSED'],
                    'resume': PRINTER_STATE['PRINTING'],
                    }
            self._change_state(status_map[status])

    def cancelPrint(self):
        if not self.isPrinting() and not self.isPaused():
            return
        self._send_pause_cancel_request('cancel')

    def setPause(self, pause):
        if not pause and self.isPaused():
            self._send_pause_cancel_request('resume')

        elif pause and self.isPrinting():
            self._send_pause_cancel_request('pause')

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
                self._change_state(PRINTER_STATE['ERROR'])
            time.sleep(0.1)
        self._log("Connection closed, closing down monitor")

    def _update_printer_data(self):
        if not self._printer_uri:
            return

        response = self._session.get(self._printer_uri)

        if not response.ok:
            self._log('Unable to get printer status: {}: {}'.format(response.status_code, response.content))
            return

        response_data = response.json()

        if response_data['current_print'] and response_data['current_print']['status'].lower() != 'new':
            self._print_job_uri = response_data['current_print']['job_uri']
        else:
            self._print_job_uri = None

        self._update_state(response_data)
        self._update_temps(response_data)

        self._update_progress(response_data)

    def _update_temps(self, response_data):
        temps = response_data['temperatures']

        self._tool_tempuratures = {0: [
                temps['extruder1'].get('current') if temps.get('extruder1') else None,
                temps['extruder1'].get('target') if temps.get('extruder1') else None,
            ]}

        self._bed_tempurature = [
                temps['bed'].get('current') if temps.get('bed') else None,
                temps['bed'].get('target') if temps.get('bed') else None,
                ] if temps.get('bed') else None

        self._callback.on_comm_temperature_update(self._tool_tempuratures, self._bed_tempurature)

    def _update_progress(self, response_data):
        current_print = response_data['current_print']

        if current_print and response_data['current_print']['status'].lower() != 'new':
            self._print_progress = {
                'percent_complete' : current_print['percent_complete']/100,
                'elapsed'          : current_print['elapsed'],
                'remaining'        : current_print['remaining'],
            }
            self._callback.on_comm_set_progress_data(
                    current_print['percent_complete'],
                    current_print['percent_complete']*100 if current_print['percent_complete'] else None,
                    current_print['elapsed'],
                    current_print['remaining'],
                    )
        else:
            self._print_progress = None
            self._callback.on_comm_set_progress_data(None, None, None, None)

    def _update_state(self, response_data):
        if response_data['status'].lower() == 'online':
            if not response_data['current_print'] or response_data['current_print']['status'].lower() == 'new':
                self._change_state(PRINTER_STATE['OPERATIONAL'])

            elif response_data['current_print']:
                if response_data['current_print']['status'].lower() in ['printing', 'warming_up']:
                    self._change_state(PRINTER_STATE['PRINTING'])
                elif response_data['current_print']['status'].lower() == 'paused':
                    self._change_state(PRINTER_STATE['PAUSED'])
                else:
                    self._log('Unknown print state: {}'.format(response_data['current_print']['status']))
        else:
            self._change_state(PRINTER_STATE['CONNECTING'])
