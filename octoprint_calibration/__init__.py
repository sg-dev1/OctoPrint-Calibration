# coding=utf-8
from __future__ import absolute_import
from enum import Enum
import threading

import flask

### (Don't forget to remove me)
# This is a basic skeleton for your plugin's __init__.py. You probably want to adjust the class name of your plugin
# as well as the plugin mixins it's subclassing from. This is really just a basic skeleton to get you started,
# defining your plugin as a template plugin, settings and asset plugin. Feel free to add or remove mixins
# as necessary.
#
# Take a look at the documentation on what other plugin mixins are available.

import octoprint.plugin

class CalibrationPlugin(octoprint.plugin.SettingsPlugin,
                        octoprint.plugin.AssetPlugin,
                        octoprint.plugin.TemplatePlugin,
                        octoprint.plugin.SimpleApiPlugin,
                        octoprint.plugin.EventHandlerPlugin):

    class PluginState(Enum):
        IDLE = 1
        WAITING_FOR_M92_ANSWER = 2
        WAITING_FOR_EXTRUDER_TEMP = 3
        WAITING_FOR_EXTRUDE_START = 4
        WAITING_FOR_EXTRUDE_FINISHED = 5
        WAITING_FOR_MEASUREMENT_INPUT = 6
        WAITING_FOR_USER_CONFIRM = 7

    def initialize(self):
        if self._printer.get_state_id() == "OPERATIONAL":
            self._connected = True
        else:
            self._connected = False
        self._state = CalibrationPlugin.PluginState.IDLE
        self._startExtrudingClicked = False
        self._eSteps = 0.0
        self._newEsteps = 0.0
        self._newEstepsValid = False

    ##~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        return dict(
            # put your plugin's default settings here
            hotendTemp=210
        )

    ##~~ AssetPlugin mixin

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return dict(
            js=["js/calibration.js"],
            css=["css/calibration.css"],
            less=["less/calibration.less"]
        )

    ##~~ Softwareupdate hook

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
        # for details.
        return dict(
            calibration=dict(
                displayName="Calibration Plugin",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="you",
                repo="OctoPrint-Calibration",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/you/OctoPrint-Calibration/archive/{target_version}.zip"
            )
        )

    #~~ SimpleApiPlugin mixin
    def get_api_commands(self):
        return dict(
            #command1=[],
            #command2=["some_parameter"]
            calibrateESteps=[],
            startExtruding=[],
            eStepsMeasured=["measurement"],
            saveNewESteps=[],
        )

    def on_api_command(self, command, data):        
        """
        if command == "command1":
            parameter = "unset"
            if "parameter" in data:
                parameter = "set"
            self._logger.info("command1 called, parameter is {parameter}".format(**locals()))
        elif command == "command2":
            self._logger.info("command2 called, some_parameter is {some_parameter}".format(**data))
        """
        if not self._isOperational():
            self._logger.error("Not operational. Cannot calibrate e steps.")
            return

        if command == "calibrateESteps":
            self._logger.info("Command received: calibrateESteps")            

            self._printer.set_temperature("tool0", self._settings.get_int(["hotendTemp"]))
            self._printer.commands("M92")
            self._switchState(CalibrationPlugin.PluginState.WAITING_FOR_M92_ANSWER)

        if command == "startExtruding":
            if self._state == CalibrationPlugin.PluginState.WAITING_FOR_EXTRUDE_START:
                self._extrudeFilament()
            else:
                self._startExtrudingClicked = True

        if command == "eStepsMeasured":
            if self._state != CalibrationPlugin.PluginState.WAITING_FOR_MEASUREMENT_INPUT:
                self._logger.info("Wrong state detected: %s" % self._state)
                return
            self._logger.info("Command received: eStepsMeasured")
            if not self._isOperational():
                self._logger.error("Not operational. Cannot calibrate e steps.")
                return
            
            measuredLength = float(data["measurement"])
            self._logger.info("Received measurement %.2f." % measuredLength)

            filamentExtruded = 120 - measuredLength
            self._newEsteps = self._eSteps / filamentExtruded * 100
            self._newEstepsValid = True

            self._logger.info("E steps should be changed from %.2f to %.2f." % (self._eSteps, self._newEsteps))

            self._switchState(CalibrationPlugin.PluginState.WAITING_FOR_USER_CONFIRM)

            # present result to user (with option to save it)
            # what to use as "return channel" to notify user - WebSockets?
            # --> for simplicity now the get endpoint is now used by the frontend (not the best solution)

        if command == "saveNewESteps":
            if self._state != CalibrationPlugin.PluginState.WAITING_FOR_USER_CONFIRM:
                self._logger.info("Wrong state detected: %s" % self._state)
                return
            self._logger.info("Command received: saveNewESteps")

            self._printer.set_temperature("tool0", 0)
            self._printer.commands(["M92 E%.2f" % self._newEsteps, "M500", "G90"])

            self._logger.info("E steps calibration procedure finished")


    def on_api_get(self, request):
        return flask.jsonify(
                oldEsteps="%.2f" % self._eSteps,
                newEsteps="%.2f" % self._newEsteps,
                newEstepsValid=str(self._newEstepsValid)
            )

    #~~ EventHandlerPlugin mixin
    def on_event(self, event, payload):
        if event == 'Disconnected':
            self._logger.info("Printer disconnected. \n" + str(payload))
            self._connected = False    
            self._state = CalibrationPlugin.PluginState.IDLE 
        if event == 'Connected':
            self._logger.info("Printer connected. \n" + str(payload))
            self._connected = True
            # event["port"], event["baudrate"]

    #~~ Gcode Received hook

    def on_printer_gcode_received(self, comm, line, *args, **kwargs):
        #if "wait" != line:
        #    self._logger.info("on_printer_gcode_received: line=" + line)
        line_lower = line.lower()

        # Recv: echo: M92 X80.0 Y80.0 Z800.0 E90.0
        if "m92" in line_lower and self._state == CalibrationPlugin.PluginState.WAITING_FOR_M92_ANSWER:
            parts = line_lower.split(" ")
            eStepsStr = parts[len(parts) - 1][1:]
            self._logger.info("E steps got from printer: " + eStepsStr)
            self._eSteps = float(eStepsStr)
            self._switchState(CalibrationPlugin.PluginState.WAITING_FOR_EXTRUDER_TEMP)
            threading.Timer(3.0, self._preheatWait).start()

        if self._state == CalibrationPlugin.PluginState.WAITING_FOR_EXTRUDE_FINISHED and "ok" in line_lower:
            self._switchState(CalibrationPlugin.PluginState.WAITING_FOR_MEASUREMENT_INPUT)

        return line

    ### Internal stuff
    def _isOperational(self):
        return self._connected

    def _switchState(self, newState):
        oldState = self._state
        self._state = newState
        self._logger.info("Switching from state %s to state %s." % (str(oldState), str(newState)))

    def _extrudeFilament(self):
        self._startExtrudingClicked = False
        self._printer.commands(["G91", "G1 E100 F50"])

        # need to wait till extrude is finished
        self._switchState(CalibrationPlugin.PluginState.WAITING_FOR_EXTRUDE_FINISHED)

    def _preheatWait(self):
        if self._state != CalibrationPlugin.PluginState.WAITING_FOR_EXTRUDER_TEMP:
            self._logger.info("Wrong state detected")
            return
        temps = self._printer.get_current_temperatures()
        self._logger.info("temps: %s" % str(temps))
        toolReady = True
        if temps['tool0']['actual'] + 3 < temps['tool0']['target']:
            toolReady = False
        if toolReady:
            self._switchState(CalibrationPlugin.PluginState.WAITING_FOR_EXTRUDE_START)
            if self._startExtrudingClicked:
                # user is already ready for extrude
                self._extrudeFilament()
        else:
            self._logger.info("Preheating...")
            threading.Timer(3.0, self._preheatWait).start()



# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Calibration Plugin"

# Starting with OctoPrint 1.4.0 OctoPrint will also support to run under Python 3 in addition to the deprecated
# Python 2. New plugins should make sure to run under both versions for now. Uncomment one of the following
# compatibility flags according to what Python versions your plugin supports!
#__plugin_pythoncompat__ = ">=2.7,<3" # only python 2
__plugin_pythoncompat__ = ">=3,<4" # only python 3
#__plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = CalibrationPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        'octoprint.comm.protocol.gcode.received': __plugin_implementation__.on_printer_gcode_received,
    }

