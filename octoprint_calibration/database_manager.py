# coding=utf-8
# pylint: disable=useless-object-inheritance,invalid-name,missing-function-docstring,missing-class-docstring,missing-module-docstring,line-too-long

import decimal
import logging
import os

import peewee

import octoprint_calibration.models as models

class DatabaseManager(object):
    def __init__(self, parentLogger):
        self._logger = logging.getLogger(parentLogger.name + "." + self.__class__.__name__)

        self._database = None
        self._databaseFileAbsPath = None

    def initialize(self, databaseFileDirectory):
        self._databaseFileAbsPath = os.path.join(databaseFileDirectory, "calibration.db")

        self._logger.info("Database file absolute path: '%s'", self._databaseFileAbsPath)

        self._database = peewee.SqliteDatabase(self._databaseFileAbsPath)
        # http://docs.peewee-orm.com/en/latest/peewee/database.html#setting-the-database-at-run-time
        self._database.bind(models.MODELS)

        # simpl impl for testing
        #self._dropCreateTables()
        self._createTablesIfNotExist()

    def _dropCreateTables(self):
        self._database.connect(reuse_if_open=True)
        self._database.drop_tables(models.MODELS)
        self._database.create_tables(models.MODELS)
        self._database.close()
        self._logger.info("Database tables created cleaning up existing ones.")

    def _createTablesIfNotExist(self):
        self._database.connect(reuse_if_open=True)
        self._database.create_tables(models.MODELS)
        self._database.close()

    def insertEstepsCalibration(self, eStepsCalibrationModel):
        databaseId = None
        with self._database.atomic() as txn:
            try:
                eStepsCalibrationModel.save()
                databaseId = eStepsCalibrationModel.get_id()
            except Exception as e:
                txn.rollback()
                self._logger.exception("Could not insert E steps calibration into database: %s", str(e))
        return databaseId

    def loadAllEStepCalibrations(self, loadData=True):
        query = models.EStepsCalibrationModel.select().order_by(models.EStepsCalibrationModel.created.desc())
        if loadData:
            # conversion of result s.t. it can be directly be passed to flask.jsonify
            result = []
            for elem in query:
                elemData = elem.__data__
                newElemData = {}
                for key in elemData.keys():
                    value = elemData[key]
                    #self._logger.info("Processing key=%s, value=%s", str(key), str(value))
                    # flask.jsonify does not understand decimal.Decimal, therefore special handling is required
                    if isinstance(value, decimal.Decimal):
                        #self._logger.info("Value %s is float.", value)
                        newElemData[key] = float(value)
                    else:
                        newElemData[key] = value
                result.append(newElemData)
            return result
        else:
            return query



    
