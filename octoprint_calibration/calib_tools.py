# coding=utf-8
from enum import Enum
import threading

class EStepsCalibrationTool(object):
    class State(Enum):
        IDLE = 1
        WAITING_FOR_M92_ANSWER = 2
        WAITING_FOR_EXTRUDER_TEMP = 3
        WAITING_FOR_EXTRUDE_START = 4
        WAITING_FOR_EXTRUDE_FINISHED = 5
        WAITING_FOR_MEASUREMENT_INPUT = 6
        WAITING_FOR_USER_CONFIRM = 7

    def initialize(self, calibPluginInstance):
        self._calibPluginInstance = calibPluginInstance
        self._state = EStepsCalibrationTool.State.IDLE
        self._startExtrudingClicked = False
        self._eSteps = 0.0
        self._newEsteps = 0.0
        self._newEstepsValid = False

    def getToolState(self):
        return dict(
            oldEsteps="%.2f" % self._eSteps,
            newEsteps="%.2f" % self._newEsteps,
            newEstepsValid=str(self._newEstepsValid),
            eStepsToolState=str(self._state.value)
        )

    def getApiCommands(self):
        return dict(
            calibrateESteps=["filamentName", "filamentType"],
            startExtruding=[],
            eStepsMeasured=["measurement"],
            saveNewESteps=[],
        )

    def handleApiCommand(self, command, data):
        if not self._calibPluginInstance.isOperational():
            self._calibPluginInstance._logger.error("Not operational. Cannot calibrate e steps.")
            return

        if command == "calibrateESteps":
            self._filamentName = data["filamentName"]
            self._filamentType = data["filamentType"]
            toolTemperature = self._calibPluginInstance._settings.get_int(["hotendTemp"])

            self._calibPluginInstance._logger.info(
                "Starting new e steps calibration for filament '%s' of type '%s' with hotend temperature %d." % \
                    (self._filamentName, self._filamentType["name"], toolTemperature))

            self._calibPluginInstance._printer.set_temperature("tool0", toolTemperature)
            self._calibPluginInstance._printer.commands("M92")
            self._switchState(EStepsCalibrationTool.State.WAITING_FOR_M92_ANSWER)

        if command == "startExtruding":
            if self._state == EStepsCalibrationTool.State.WAITING_FOR_EXTRUDE_START:
                self._extrudeFilament()
            else:
                self._startExtrudingClicked = True

        if command == "eStepsMeasured":
            if self._state != EStepsCalibrationTool.State.WAITING_FOR_MEASUREMENT_INPUT:
                self._calibPluginInstance._logger.info("Wrong state detected: %s" % self._state)
                return
            self._calibPluginInstance._logger.info("Command received: eStepsMeasured")
            
            measuredLength = float(data["measurement"])
            self._calibPluginInstance._logger.info("Received measurement %.2f." % measuredLength)

            filamentExtruded = 120 - measuredLength
            self._newEsteps = self._eSteps / filamentExtruded * 100
            self._newEstepsValid = True

            self._calibPluginInstance._logger.info("E steps should be changed from %.2f to %.2f." % (self._eSteps, self._newEsteps))

            self._switchState(EStepsCalibrationTool.State.WAITING_FOR_USER_CONFIRM)

            # present result to user (with option to save it)
            # what to use as "return channel" to notify user - WebSockets?
            # --> for simplicity now the get endpoint is now used by the frontend (not the best solution)

        if command == "saveNewESteps":
            if self._state != EStepsCalibrationTool.State.WAITING_FOR_USER_CONFIRM:
                self._calibPluginInstance._logger.info("Wrong state detected: %s" % self._state)
                return
            self._calibPluginInstance._logger.info("Command received: saveNewESteps")

            self._calibPluginInstance._printer.set_temperature("tool0", 0)
            self._calibPluginInstance._printer.commands(["M92 E%.2f" % self._newEsteps, "M500", "G90"])

            self._calibPluginInstance._logger.info("E steps calibration procedure finished")

    def handleGcodeReceived(self, comm, line, *args, **kwargs):
        line_lower = line.lower()

        # Recv: echo: M92 X80.0 Y80.0 Z800.0 E90.0
        if "m92" in line_lower and self._state == EStepsCalibrationTool.State.WAITING_FOR_M92_ANSWER:
            parts = line_lower.split(" ")
            eStepsStr = parts[len(parts) - 1][1:]
            self._calibPluginInstance._logger.info("E steps got from printer: " + eStepsStr)
            self._eSteps = float(eStepsStr)
            self._switchState(EStepsCalibrationTool.State.WAITING_FOR_EXTRUDER_TEMP)
            threading.Timer(3.0, self._preheatWait).start()

        if self._state == EStepsCalibrationTool.State.WAITING_FOR_EXTRUDE_FINISHED and "ok" in line_lower:
            self._switchState(EStepsCalibrationTool.State.WAITING_FOR_MEASUREMENT_INPUT)

    def handlePrinterDisconnected(self):
        self._state = EStepsCalibrationTool.State.IDLE

    ##################
    ### Internal stuff

    def _switchState(self, newState):
        oldState = self._state
        self._state = newState
        self._calibPluginInstance._logger.info("Switching from state %s to state %s." % (str(oldState), str(newState)))

    def _extrudeFilament(self):
        self._startExtrudingClicked = False
        self._calibPluginInstance._printer.commands(["G91", "G1 E100 F50"])

        # need to wait till extrude is finished
        self._switchState(EStepsCalibrationTool.State.WAITING_FOR_EXTRUDE_FINISHED)

    def _preheatWait(self):
        if self._state != EStepsCalibrationTool.State.WAITING_FOR_EXTRUDER_TEMP:
            self._calibPluginInstance._logger.info("Wrong state detected")
            return
        temps = self._calibPluginInstance._printer.get_current_temperatures()
        self._calibPluginInstance._logger.info("temps: %s" % str(temps))
        toolReady = True
        if temps['tool0']['actual'] + 3 < temps['tool0']['target']:
            toolReady = False
        if toolReady:
            self._switchState(EStepsCalibrationTool.State.WAITING_FOR_EXTRUDE_START)
            if self._startExtrudingClicked:
                # user is already ready for extrude
                self._extrudeFilament()
        else:
            self._calibPluginInstance._logger.info("Preheating...")
            threading.Timer(3.0, self._preheatWait).start()
