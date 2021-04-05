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

        self.makePostRequest = function(postData, responseHandler, errorHandler) {
            $.ajax({
                url: self.baseUrl + "plugin/" + self.pluginId,
                type: "post",
                dataType: "json",
                contentType: 'application/json',
                data: JSON.stringify(postData)
            }).done(
                function( data ) {
                    responseHandler(data);
                }
            ).fail(
                function (data) {
                    console.error("Error: " + JSON.stringify(data));
                    errorHandler(data);
                }
            );
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

    // https://jsfiddle.net/AnkUser/975ncawv/149/
    // https://stackoverflow.com/questions/51638095/knockout-table-paging
    function EStepsCalibrationModel(creationDate, filamentName, filamentType, hotendTemp, oldEsteps, newESteps) {
        var self = this;
        self.creationDate = ko.observable(creationDate);
        self.filamentName = ko.observable(filamentName);
        self.filamentType = ko.observable(filamentType);
        self.hotendTemp = ko.observable(hotendTemp);
        self.oldEsteps = ko.observable(oldEsteps);
        self.newESteps = ko.observable(newESteps);        
    }
    EStepsCalibrationModel.fromRawDataPoint = function(dto) {
        return new EStepsCalibrationModel(dto.creationDate, dto.filamentName, dto.filamentType, dto.hotendTemp, dto.oldEsteps, dto.newESteps);
    }

    function ShowEStepsCalibrationsView(entriesPerPage) {
        var self = this;

        // Start of logic for Paging    
  
        self.items = ko.observableArray();
        this.all =  self.items;

        self.pageNumber = ko.observable(0);
        self.nbPerPage = entriesPerPage;
    
        this.totalPages = ko.computed(function() {
            var div = Math.floor(self.all().length / self.nbPerPage);
            div += self.all().length % self.nbPerPage > 0 ? 1 : 0;
            return div - 1;
        });

        this.paginated = ko.computed(function() {            
            var first = self.pageNumber() * self.nbPerPage;
            console.log("paginated called. first=" + first);
            console.log("self.all=" + JSON.stringify(self.all));
            console.log("self.items=" + JSON.stringify(self.items));
            //return self.all.slice(first, first + self.nbPerPage);
            return self.items.slice(first, first + self.nbPerPage);
        });
    
        this.hasPrevious = ko.computed(function() {
            return self.pageNumber() !== 0;
        });
  
        this.hasNext = ko.computed(function() {
            return self.pageNumber() !== self.totalPages();
        });
  
        this.next = function() {
            if(self.pageNumber() < self.totalPages()) {
                self.pageNumber(self.pageNumber() + 1);
            }
        }
  
        this.previous = function() {
            if(self.pageNumber() != 0) {
                self.pageNumber(self.pageNumber() - 1);
            }
        }  


        // End of Logic for Paging

        self.loadData = function(rawData) {
            self.items(rawData.map(EStepsCalibrationModel.fromRawDataPoint))
        }

        self.select = function(item) {
            if (item === self.selected()) {
                self.selected(null);
            } else {
                self.selected(item);
            }   
        };

        self.selected = ko.observable(self.items()[0]);
    }

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

    function EStepsCalibrationTool(apiClient, parent) {
        var self = this;

        self.apiClient = apiClient;
        self.parent = parent;       // the creator of this class (e.g. CalibrationViewModel)

        var startExtrudingCmd = {
            "command": "startExtruding",
        };
        var saveNewEstepsCmd = {
            "command": "saveNewESteps"
        };

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

        self.defaultErrorHandler = function(response) {
            self.parent.reportError(response["responseText"]);
        }

        self.stepModels = ko.observableArray([
            new Step(0, "NewEStepCalibration", "eSteps_newEStepCalibrationTmpl", {
                filamentName: ko.observable(),
                filamentTypes: ko.observableArray([
                    {name: "PLA"},
                    {name: "PETG"},
                    {name: "ABS"},
                    {name: "Nylon"},
                    {name: "PC"}
                ]),
                selectedFilamentType: ko.observable(),
                hotendTemperature: ko.observable(),
                startEStepsCalibration: 
                    function() {
                        var innerSelf = this;

                        var calibrateEStepsCmd = {
                            "command": "calibrateESteps",
                            "filamentName": innerSelf.filamentName(),
                            "filamentType": innerSelf.selectedFilamentType(),
                            "hotendTemp": innerSelf.hotendTemperature()
                        };
                        
                        self.apiClient.makePostRequest(calibrateEStepsCmd, function(data) {
                            console.log("Call done:" + JSON.stringify(data));

                            var timeoutHandler = function() {
                                self.getToolState(function(state) {
                                    if (state == 4) {
                                        // only advance to next step when state == WAITING_FOR_EXTRUDE_START (4)
                                        self.parent.setCurrentStep(self.stepModels()[2]);
                                    }
                                    else {
                                        self.parent.setCurrentStep(self.stepModels()[1]);
                                        setTimeout(timeoutHandler, 3000);
                                    }
                                });
                            };
                            timeoutHandler();
                        }, self.defaultErrorHandler);
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
                        }, self.defaultErrorHandler);

                        var timeoutHandler = function() {
                            self.getToolState(function(state) {
                                if (state == 6) {
                                    // only advance to next step when state == WAITING_FOR_MEASUREMENT_INPUT (6)
                                    self.parent.setCurrentStep(self.stepModels()[4]);
                                }
                                else {
                                    self.parent.setCurrentStep(self.stepModels()[3]);
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
                        }, self.defaultErrorHandler);
                    },
                oldEsteps: ko.observable(),
                newEsteps: ko.observable(),
                saveNewEsteps: 
                    function() {
                        console.log("saveNewEsteps called");
            
                        self.apiClient.makePostRequest(saveNewEstepsCmd, function(data) {
                            console.log("Call done:" + JSON.stringify(data));

                            self.parent.setCurrentStep(self.stepModels()[5]);
                        }, self.defaultErrorHandler);
                    }
            }),
            new Step(5, "EStepCalibrationFinished", "eSteps_calibrationFinishedTmpl", {
                eStepCalibFinished: function() {
                    self.parent.goToStartPage();
                }
            }),
            // special step for show E Steps calibration view
            new Step(6, "ShowEStepCalibrationsView", "eSteps_showCalibrationsTmpl", {
                eStepsCalibrationView: undefined,
                initialize: function() {
                    var innerSelf = this;
                    var entriesPerPage = 2;
                    innerSelf.eStepsCalibrationView = new ShowEStepsCalibrationsView(entriesPerPage);
                },
                loadData: function(rawData) {
                    var innerSelf = this;
                    console.log("Loading data: " + JSON.stringify(rawData))
                    innerSelf.eStepsCalibrationView.loadData(rawData);
                }                
            })
        ]);

        self.firstStep = function() {
            return self.stepModels()[0];
        }

        self.stepModels()[6].model().initialize();
        self.showEStepsCalibrations = function() {
            // load data from backend - for testing use dummy data
            var dummyData = [
                {
                    creationDate: "2021-01-01 12:24:25",
                    filamentName: "TestFilament1", 
                    filamentType: "PLA", 
                    hotendTemp: 210, 
                    oldEsteps: 90.0, 
                    newESteps: 91.5
                },
                {
                    creationDate: "2021-02-01 12:24:25",
                    filamentName: "TestFilament2", 
                    filamentType: "PETG", 
                    hotendTemp: 230, 
                    oldEsteps: 91, 
                    newESteps: 92.33
                },
                {
                    creationDate: "2021-03-01 12:24:25",
                    filamentName: "TestFilament3", 
                    filamentType: "ABS", 
                    hotendTemp: 250, 
                    oldEsteps: 92, 
                    newESteps: 91.3
                },
                {
                    creationDate: "2021-04-01 12:24:25",
                    filamentName: "TestFilament4", 
                    filamentType: "TPU", 
                    hotendTemp: 230, 
                    oldEsteps: 90.0, 
                    newESteps: 95
                },
                {
                    creationDate: "2021-04-02 12:24:25",
                    filamentName: "TestFilament5", 
                    filamentType: "PLA", 
                    hotendTemp: 200, 
                    oldEsteps: 91, 
                    newESteps: 90.5
                },
                {
                    creationDate: "2021-04-03 12:24:25",
                    filamentName: "TestFilament6", 
                    filamentType: "PETG", 
                    hotendTemp: 230, 
                    oldEsteps: 90.5, 
                    newESteps: 93
                }
            ];

            // and call <Step>.loadData(loadedDataInDto)
            showCalibStep = self.stepModels()[6];
            showCalibStep.model().loadData(dummyData);

            return showCalibStep;
        }
    }

    function CalibrationViewModel(parameters) {
        var self = this;

        var PLUGIN_ID = "calibration"; // from setup.py plugin_identifier

        // assign the injected parameters, e.g.:
        // self.loginStateViewModel = parameters[0];
        // self.settingsViewModel = parameters[1];

        console.log("Hello from CalibrationViewModel");
        
        self.apiClient = new APIClient(PLUGIN_ID, API_BASEURL);
        self.eStepsCalibrationTool = new EStepsCalibrationTool(self.apiClient, self);

        self.stepModels = ko.observableArray([
            new Step(0,  "StartPage", "calibPlugin_startPageTmpl", {
                newEStepsCalibration: 
                    function() {
                        self.currentStep(self.eStepsCalibrationTool.firstStep());
                    },
                showEStepsCalibrations:
                    function() {
                        self.currentStep(self.eStepsCalibrationTool.showEStepsCalibrations());
                    }
            }),
            new Step(1, "ErrorPage", "calibPlugin_errorPageTmpl", {
                errorMessage: ko.observable(),
                backToStartPage: 
                    function() {
                        self.goToStartPage();
                    }
            })
        ]);
        
        self.currentStep = ko.observable(self.stepModels()[0]);
        self.getTemplate = function(data) {
            return self.currentStep().template();
        };

        self.goToStartPage = function() {
            return self.currentStep(self.stepModels()[0]);
        }
        self.setCurrentStep = function(currStep) {
            self.currentStep(currStep);
        }

        self.reportError = function(errorMsg) {
            errorStp = self.stepModels()[1];
            //console.log("errorStp.model: " + JSON.stringify(errorStp.model()));
            errorStp.model()["errorMessage"](errorMsg);
            self.currentStep(errorStp);
        }
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
