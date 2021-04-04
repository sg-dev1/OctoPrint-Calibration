# coding=utf-8
# pylint: disable=useless-object-inheritance,invalid-name,missing-function-docstring,missing-class-docstring,missing-module-docstring

import datetime
import peewee

def makeTableName(modelClass):
    modelName = modelClass.__name__
    return "calib_" + modelName.lower()

class BaseModel(peewee.Model):
    databaseId = peewee.AutoField()
    created = peewee.DateTimeField(default = datetime.datetime.now)

    class Meta:
        table_function = makeTableName

class EStepsCalibrationModel(BaseModel):
    filamentName = peewee.CharField()
    filamentType = peewee.CharField()
    hotendTemperature = peewee.DecimalField()
    oldESteps = peewee.DecimalField()
    newESteps = peewee.DecimalField()

MODELS = [EStepsCalibrationModel]
