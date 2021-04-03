/*
 * View model for OctoPrint-Calibration
 *
 * Author: Stefan G
 * License: AGPLv3
 */
$(function() {
    function APIClient(pluginId, baseUrl) {
        var self = this;

        self.pluginId = pluginId;
        self.baseUrl = baseUrl;

        self.makePostRequest = function(postData, responseHandler) {
            $.ajax({
                url: self.baseUrl + "plugin/" + self.pluginId,
                type: "post",
                dataType: "json",
                contentType: 'application/json',
                data: JSON.stringify(postData)
            }).done(function( data ){
                responseHandler(data);
            });
        };

        self.makeGetRequest = function(responseHandler) {
            $.ajax({
                url: self.baseUrl + "plugin/" + self.pluginId,
                type: "get"
            }).done(function( data ){
                responseHandler(data);
            });
        };
    };

    // http://jsfiddle.net/rniemeyer/SSY6n/
    function Step(id, name, template, model) {
        var self = this;
        self.id = id;
        self.name = ko.observable(name);
        self.template = template;
        self.model = ko.observable(model);  
         
        self.getTemplate = function() {
            return self.template;   
        }
     }

    function CalibrationViewModel(parameters) {
        var self = this;

        var PLUGIN_ID = "calibration"; // from setup.py plugin_identifier

        var calibrateEStepsCmd = {
            "command": "calibrateESteps",
        };
        var startExtrudingCmd = {
            "command": "startExtruding",
        };
        var saveNewEstepsCmd = {
            "command": "saveNewESteps"
        }; 

        // assign the injected parameters, e.g.:
        // self.loginStateViewModel = parameters[0];
        // self.settingsViewModel = parameters[1];

        // TODO: Implement your plugin's view model here.

        console.log("Hello from CalibrationViewModel");
        
        self.apiClient = new APIClient(PLUGIN_ID, API_BASEURL);

        /*
            class State(Enum):
                IDLE = 1
                WAITING_FOR_M92_ANSWER = 2
                WAITING_FOR_EXTRUDER_TEMP = 3
                WAITING_FOR_EXTRUDE_START = 4
                WAITING_FOR_EXTRUDE_FINISHED = 5
                WAITING_FOR_MEASUREMENT_INPUT = 6
                WAITING_FOR_USER_CONFIRM = 7
        */
        self.getToolState = function(handleToolState) {
            self.apiClient.makeGetRequest(function (data) {
                console.log("GET call done:" + JSON.stringify(data));

                handleToolState(data["eStepsToolState"]);
            });
        };

        self.stepModels = ko.observableArray([
            new Step(0,  "StartPage", "calibPlugin_startPageTmpl", {
                startNewEStepsCalibration: 
                    function() {
                        console.log("startNewEStepsCalibration called");                        
                        
                        self.apiClient.makePostRequest(calibrateEStepsCmd, function(data) {
                            console.log("Call done:" + JSON.stringify(data));

                            var timeoutHandler = function() {
                                self.getToolState(function(state) {
                                    if (state == 4) {
                                        // only advance to next step when state == WAITING_FOR_EXTRUDE_START (4)
                                        self.currentStep(self.stepModels()[2]);
                                    }
                                    else {
                                        self.currentStep(self.stepModels()[1]);
                                        setTimeout(timeoutHandler, 3000);
                                    }
                                });
                            };
                            timeoutHandler();
                        });
                    }
            }),
            new Step(1, "WaitingForExtruderTemp", "eSteps_waitingForExtruderTemp", {                
            }),
            new Step(2, "StartExtruding", "eSteps_startExtrudingTmpl", {
                startExtruding: 
                    function() {
                        console.log("startExtruding called");                        
            
                        self.apiClient.makePostRequest(startExtrudingCmd, function(data) {
                            console.log("Call done:" + JSON.stringify(data)); 
                        });

                        var timeoutHandler = function() {
                            self.getToolState(function(state) {
                                if (state == 6) {
                                    // only advance to next step when state == WAITING_FOR_MEASUREMENT_INPUT (6)
                                    self.currentStep(self.stepModels()[4]);
                                }
                                else {
                                    self.currentStep(self.stepModels()[3]);
                                    setTimeout(timeoutHandler, 3000);
                                }
                            });
                        };
                        timeoutHandler();
                    }
            }),
            new Step(3, "WaitingForExtrudeFinished", "eSteps_waitingForExtrudeFinishedTmpl", {
            }),
            new Step(4, "EStepsResult", "eSteps_resultCalcTmpl", {
                measuredFilamentLength: ko.observable(20),
                submitMeasuredFilamentLength: 
                    function() {
                        console.log("submitMeasuredFilamentLength called");

                        var innerSelf = this;

                        var eStepsMeasuredCmd = {
                            "command": "eStepsMeasured",
                            "measurement": innerSelf.measuredFilamentLength()
                        };
            
                        console.log("Sending request: " + JSON.stringify(eStepsMeasuredCmd));
            
                        self.apiClient.makePostRequest(eStepsMeasuredCmd, function(data) {
                            console.log("Call done:" + JSON.stringify(data));
            
                            self.apiClient.makeGetRequest(function (data) {
                                console.log("GET call done:" + JSON.stringify(data));
            
                                if (data["newEstepsValid"] == "True") {
                                    innerSelf.oldEsteps(data["oldEsteps"]);
                                    innerSelf.newEsteps(data["newEsteps"]);
                                }
                            });
                        });
                    },
                oldEsteps: ko.observable(),
                newEsteps: ko.observable(),
                saveNewEsteps: 
                    function() {
                        console.log("saveNewEsteps called");
            
                        self.apiClient.makePostRequest(saveNewEstepsCmd, function(data) {
                            console.log("Call done:" + JSON.stringify(data));

                            self.currentStep(self.stepModels()[5]);
                        });
                    }
            }),
            new Step(5, "EStepCalibrationFinished", "eSteps_calibrationFinishedTmpl", {
                eStepCalibFinished: function() {
                    self.currentStep(self.stepModels()[0]);
                }
            })
        ]);
        
        self.currentStep = ko.observable(self.stepModels()[0]);
        self.getTemplate = function(data) {
            return self.currentStep().template();
        };
    }

    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push({
        construct: CalibrationViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        dependencies: [ /* "loginStateViewModel", "settingsViewModel" */ ],
        // Elements to bind to, e.g. #settings_plugin_calibration, #tab_plugin_calibration, ...
        // This is very important for the data binding
        // If it is empty (default after creating the skeleton project) no data binding is applied (button clicks don't work etc.)
        elements: [ "#tab_plugin_calibration" ]
    });
});
