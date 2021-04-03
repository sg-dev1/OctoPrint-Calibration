# coding=utf-8
from __future__ import absolute_import

import flask
from octoprint_calibration.calib_tools import EStepsCalibrationTool

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

    def initialize(self):
        if self._printer.get_state_id() == "OPERATIONAL":
            self._connected = True
        else:
            self._connected = False

        self._eStepsCalibTool = EStepsCalibrationTool()
        self._eStepsCalibTool.initialize(self)

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
        return self._eStepsCalibTool.getApiCommands()

    def on_api_command(self, command, data):
        self._eStepsCalibTool.handleApiCommand(command, data)

    def on_api_get(self, request):
        return flask.jsonify(self._eStepsCalibTool.getToolState())

    #~~ EventHandlerPlugin mixin
    def on_event(self, event, payload):
        if event == 'Disconnected':
            self._logger.info("Printer disconnected. \n" + str(payload))
            self._connected = False    
            #self._state = CalibrationPlugin.PluginState.IDLE
            self._eStepsCalibTool.handlePrinterDisconnected()
        if event == 'Connected':
            self._logger.info("Printer connected. \n" + str(payload))
            self._connected = True
            # event["port"], event["baudrate"]

    #~~ Gcode Received hook

    def on_printer_gcode_received(self, comm, line, *args, **kwargs):
        #if "wait" != line:
        #    self._logger.info("on_printer_gcode_received: line=" + line)

        self._eStepsCalibTool.handleGcodeReceived(comm, line, args, kwargs)

        return line

    ### Public Interface
    def isOperational(self):
        return self._connected

    ### Internal stuff
    ###



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

