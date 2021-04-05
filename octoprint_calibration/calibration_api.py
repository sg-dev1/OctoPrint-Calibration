# coding=utf-8
# pylint: disable=useless-object-inheritance,invalid-name,missing-function-docstring,missing-class-docstring,missing-module-docstring,line-too-long

import octoprint.plugin
import flask

#############################################################
# Internal API for all Frontend communications
#############################################################
class CalibrationAPI(octoprint.plugin.BlueprintPlugin):
    @octoprint.plugin.BlueprintPlugin.route("/eStepCalibrations", methods=["GET"])
    def getAllEStepCalibrations(self):
        calibs = self._databaseManager.loadAllEStepCalibrations()
        self._logger.info("calibs=%s", str(calibs))
        return flask.jsonify(calibs)
