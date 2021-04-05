# coding=utf-8
# pylint: disable=useless-object-inheritance,invalid-name,missing-function-docstring,missing-class-docstring,missing-module-docstring,line-too-long
from enum import Enum
import logging
import threading

from octoprint_calibration.models import EStepsCalibrationModel

class EStepsCalibrationTool(object):
    def __init__(self, parentLogger):
        self._logger = logging.getLogger(parentLogger.name + "." + self.__class__.__name__)
        self._calibPluginInstance = None
        self._databaseManager = None
        self._printer = None
        self._state = EStepsCalibrationTool.State.IDLE
        self._startExtrudingClicked = False
        self._eSteps = 0.0
        self._newEsteps = 0.0
        self._toolTemperature = 0.0
        self._newEstepsValid = False
        self._filamentName = ""
        self._filamentType = ""

    class State(Enum):
        IDLE = 1
        WAITING_FOR_M92_ANSWER = 2
        WAITING_FOR_EXTRUDER_TEMP = 3
        WAITING_FOR_EXTRUDE_START = 4
        WAITING_FOR_EXTRUDE_FINISHED = 5
        WAITING_FOR_MEASUREMENT_INPUT = 6
        WAITING_FOR_USER_CONFIRM = 7

    def initialize(self, calibPluginInstance, databaseManager, printer):
        self._calibPluginInstance = calibPluginInstance
        self._databaseManager = databaseManager
        self._printer = printer

    def getToolState(self):
        #self._logger.info(str(self._printer.get_current_temperatures()))
        return dict(
            oldEsteps="%.2f" % self._eSteps,
            newEsteps="%.2f" % self._newEsteps,
            newEstepsValid=str(self._newEstepsValid),
            eStepsToolState=str(self._state.value),
            currTemp="%.2f" % self._printer.get_current_temperatures()["tool0"]["actual"]
        )

    # pylint: disable=no-self-use
    def getApiCommands(self):
        return dict(
            calibrateESteps=["filamentName", "filamentType", "hotendTemp"],
            startExtruding=[],
            eStepsMeasured=["measurement"],
            saveNewESteps=[],
        )

    def handleApiCommand(self, command, data):
        if not self._calibPluginInstance.isOperational():
            reason = "Not operational. Cannot calibrate e steps."
            self._logger.error(reason)
            return False, reason

        if command == "calibrateESteps":
            self._filamentName = data["filamentName"]
            self._filamentType = data["filamentType"]
            #self._toolTemperature = self._calibPluginInstance._settings.get_int(["hotendTemp"])
            self._toolTemperature = int(data["hotendTemp"])

            self._logger.info(
                "Starting new e steps calibration for filament '%s' of type '%s' with hotend temperature %d.", \
                    self._filamentName, self._filamentType["name"], self._toolTemperature)

            self._printer.set_temperature("tool0", self._toolTemperature)
            self._printer.commands("M92")
            self._switchState(EStepsCalibrationTool.State.WAITING_FOR_M92_ANSWER)

        if command == "startExtruding":
            if self._state == EStepsCalibrationTool.State.WAITING_FOR_EXTRUDE_START:
                self._extrudeFilament()
            else:
                self._startExtrudingClicked = True

        if command == "eStepsMeasured":
            if self._state != EStepsCalibrationTool.State.WAITING_FOR_MEASUREMENT_INPUT:
                reason = "Wrong state detected: %s" % self._state
                self._logger.info(reason)
                return False, reason
            self._logger.info("Command received: eStepsMeasured")

            measuredLength = float(data["measurement"])
            self._logger.info("Received measurement %.2f.", measuredLength)

            filamentExtruded = 120 - measuredLength
            self._newEsteps = self._eSteps / filamentExtruded * 100
            self._newEstepsValid = True

            self._logger.info("E steps should be changed from %.2f to %.2f.", self._eSteps, self._newEsteps)

            self._switchState(EStepsCalibrationTool.State.WAITING_FOR_USER_CONFIRM)

            # present result to user (with option to save it)
            # what to use as "return channel" to notify user - WebSockets?
            # --> for simplicity now the get endpoint is now used by the frontend (not the best solution)

        if command == "saveNewESteps":
            if self._state != EStepsCalibrationTool.State.WAITING_FOR_USER_CONFIRM:
                reason = "Wrong state detected: %s" % self._state
                self._logger.info()
                return False, reason
            self._logger.info("Command received: saveNewESteps")

            self._printer.set_temperature("tool0", 0)
            self._printer.commands(["M92 E%.2f" % self._newEsteps, "M500", "G90"])

            self._logger.info("E steps calibration procedure finished")

            eStepsCalibModel = EStepsCalibrationModel()
            eStepsCalibModel.filamentName = self._filamentName
            eStepsCalibModel.filamentType = self._filamentType["name"]
            eStepsCalibModel.hotendTemperature = self._toolTemperature
            eStepsCalibModel.oldESteps = round(self._eSteps, 3)
            eStepsCalibModel.newESteps = round(self._newEsteps, 3)
            self._databaseManager.insertEstepsCalibration(eStepsCalibModel)

        return True, ""

    # pylint: disable=unused-argument
    def handleGcodeReceived(self, comm, line, *args, **kwargs):
        line_lower = line.lower()

        # Recv: echo: M92 X80.0 Y80.0 Z800.0 E90.0
        if "m92" in line_lower and self._state == EStepsCalibrationTool.State.WAITING_FOR_M92_ANSWER:
            parts = line_lower.split(" ")
            eStepsStr = parts[len(parts) - 1][1:]
            self._logger.info("E steps got from printer: %s", eStepsStr)
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
        self._logger.info("Switching from state %s to state %s.", str(oldState), str(newState))

    def _extrudeFilament(self):
        self._startExtrudingClicked = False
        self._printer.commands(["G91", "G1 E100 F50"])

        # need to wait till extrude is finished
        self._switchState(EStepsCalibrationTool.State.WAITING_FOR_EXTRUDE_FINISHED)

    def _preheatWait(self):
        if self._state != EStepsCalibrationTool.State.WAITING_FOR_EXTRUDER_TEMP:
            self._logger.info("Wrong state detected")
            return
        temps = self._printer.get_current_temperatures()
        self._logger.info("temps: %s", str(temps))
        toolReady = True
        if temps['tool0']['actual'] + 3 < temps['tool0']['target']:
            toolReady = False
        if toolReady:
            self._switchState(EStepsCalibrationTool.State.WAITING_FOR_EXTRUDE_START)
            if self._startExtrudingClicked:
                # user is already ready for extrude
                self._extrudeFilament()
        else:
            self._logger.info("Preheating...")
            threading.Timer(3.0, self._preheatWait).start()
