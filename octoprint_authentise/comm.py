# coding=utf-8
from __future__ import absolute_import
__author__ = "Scott Lemmon <scott@authentise.com> based on work by Gina Häußge"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2015 Authentise - Released under terms of the AGPLv3 License"

import logging
import requests
import threading
import urlparse

from octoprint.events import eventManager, Events
from octoprint.util import get_exception_string, RepeatedTimer, comm_helpers
import octoprint.plugin


class MachineCom(octoprint.plugin.MachineComPlugin):
    _logger = None
    _serialLogger = None

    _state = None

    _port = None
    _baudrate = None
    _printer_id = None

    _authentise_model = None

    _authentise_url = None
    _api_key = None
    _api_secret = None

    _command_uri_queue = None

    _temp = {}
    _bedTemp = None
    _temperature_timer = None

    _callback = None
    _printer_profile_manager = None

    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._serialLogger = logging.getLogger("SERIAL")

        self._command_uri_queue = comm_helpers.TypedQueue()

        self._state = self.STATE_NONE

    def startup(self, callbackObject=None, printerProfileManager=None):
        if callbackObject == None:
            callbackObject = MachineComPrintCallback()

        self._callback = callbackObject

        self._printer_profile_manager = printerProfileManager

        self._authentise_url = self._settings.get(['authentise_url'])
        self._api_key = self._settings.get(['api_key'])
        self._api_secret = self._settings.get(['api_secret'])

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
        self._printer_id = self._settings.get(['printer_id'])

        # monitoring thread
        self._monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitor_loop, name="comm._monitor")
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()

        self._temperature_timer = RepeatedTimer(lambda: comm_helpers.get_interval("temperature", default_value=4.0), self._poll_temperature, run_first=True)
        self._temperature_timer.start()

        payload = dict(port=self._port, baudrate=self._baudrate)
        self._changeState(self.STATE_OPERATIONAL)

        eventManager().fire(Events.CONNECTED, payload)

    ##~~ internal state management

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

    def getStateString(self):
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
        return self._state == self.STATE_OPERATIONAL or self._state == self.STATE_PRINTING or self._state == self.STATE_PAUSED or self._state == self.STATE_TRANSFERING_FILE

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

    def getPrintProgress(self):
        #TODO: Add print progress status updates
        return self._print_progress

    def getPrintFilepos(self):
        return

    def getPrintTime(self):
        #TODO: Add print time
            return

    def getCleanedPrintTime(self):
        return

    def getTemp(self):
        return self._temp

    def getBedTemp(self):
        return self._bedTemp

    def getOffsets(self):
        return {}

    def getCurrentTool(self):
        return 0

    def getConnection(self):
        return self._printer_id

    ##~~ external interface

    def close(self, isError = False):
        if self._temperature_timer is not None:
            try:
                self._temperature_timer.cancel()
            except:
                pass

        self._monitoring_active = False

        printing = self.isPrinting() or self.isPaused()

        if printing:
            eventManager().fire(Events.PRINT_FAILED, None)
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
            printer_command_url = urlparse.urljoin(self._authentise_url, 'printer/instance/{}/command/'.format(self._printer_id))
            response = requests.post(printer_command_url, json=data, auth=(self._api_key, self._api_secret))
            if not response.ok:
                self._log('Warning: Got invalid response {}: {} for {}: {}'.format(response.status_code, response.content, response.request.url, response.request.body))
                return

            self._log('Sent {} to {} with response {}: {}'.format(response.request.body, response.request.url, response.status_code, response.content))
            command_uri = response.headers['Location']
            self._command_uri_queue.put({'uri': command_uri, 'tries': 0})

    def startPrint(self):
        if not self.isOperational() or self.isPrinting():
            return

        try:
            #TODO: add logic to make print request here
            payload = {}
            response = requests.post('http://print.authentise.com/print/', json=payload, auth=(self._api_key, self._api_secret))

            self._changeState(self.STATE_PRINTING)
            eventManager().fire(Events.PRINT_STARTED, None)

        except:
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
            #TODO: send resume command

            eventManager().fire(Events.PRINT_RESUMED, payload)
        elif pause and self.isPrinting():
            self._changeState(self.STATE_PAUSED)
            #TODO: send pause command

            eventManager().fire(Events.PRINT_PAUSED, payload)

    def getSdFiles(self):
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

    def _monitor_loop(self):
        def _readline():
            #TODO: read the response from command uri in the command uri queue
            # if the response is older that 2 minutes, pop it from the queue    
            # if the response has a gcode response, return it and pop it from the queue
            # also should probably check if the command is a temp command
            #   and throw the updated temp event accordingly
            return ''

        self._log("Connected, starting monitor")

        while self._monitoring_active:
            try:
                line = _readline()
                if not line:
                    continue

                #TODO: if the line is a temp line:
                if 'T:' in line: #this is probably totally wrong
                    self._callback.on_comm_temperature_update(self._temp, self._bedTemp)
                self._log(line)
                self._callback.on_comm_message(line)

            except:
                self._logger.exception("Something crashed inside the serial connection loop, please report this in OctoPrint's bug tracker:")
                errorMsg = "See octoprint.log for details"
                self._log(errorMsg)
                self._errorValue = errorMsg
                self._changeState(self.STATE_ERROR)
                eventManager().fire(Events.ERROR, {"error": self.getErrorString()})
        self._log("Connection closed, closing down monitor")

    def _poll_temperature(self):
        if self.isOperational():
            self.sendCommand("M105", cmd_type="temperature_poll")

