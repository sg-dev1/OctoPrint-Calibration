/*
 * View model for OctoPrint-Calibration
 *
 * Author: Stefan G
 * License: AGPLv3
 */
$(function() {
    function APIClient(pluginId, baseUrl) {
        this.pluginId = pluginId;
        this.baseUrl = baseUrl;

        this.makePostRequest = function(postData, responseHandler) {
            $.ajax({
                url: this.baseUrl + "plugin/" + this.pluginId,
                type: "post",
                dataType: "json",
                contentType: 'application/json',
                data: JSON.stringify(postData)
            }).done(function( data ){
                responseHandler(data);
            });
        };

        this.makeGetRequest = function(responseHandler) {
            $.ajax({
                url: this.baseUrl + "plugin/" + this.pluginId,
                type: "get"
            }).done(function( data ){
                responseHandler(data);
            });
        };
    };

    function CalibrationViewModel(parameters) {
        var self = this;

        var PLUGIN_ID = "calibration"; // from setup.py plugin_identifier

        // assign the injected parameters, e.g.:
        // self.loginStateViewModel = parameters[0];
        // self.settingsViewModel = parameters[1];

        // TODO: Implement your plugin's view model here.

        console.log("Hello from CalibrationViewModel");

        self.measuredFilamentLength = ko.observable();
        self.oldEsteps = ko.observable();
        self.newEsteps = ko.observable();
        
        self.apiClient = new APIClient(PLUGIN_ID, API_BASEURL);

        var calibrateEStepsCmd = {
            "command": "calibrateESteps",
        };
        var startExtrudingCmd = {
            "command": "startExtruding",
        };
        var saveNewEstepsCmd = {
            "command": "saveNewESteps"
        };      

        self.startNewEStepsCalibration = function() {
            console.log("startNewEStepsCalibration called");
            
            self.apiClient.makePostRequest(calibrateEStepsCmd, function(data) {
                console.log("Call done:" + JSON.stringify(data)); 
            });
        };

        self.startExtruding = function() {
            console.log("startExtruding called");

            self.apiClient.makePostRequest(startExtrudingCmd, function(data) {
                console.log("Call done:" + JSON.stringify(data)); 
            });
        }

        self.submitMeasuredFilamentLength = function() {
            console.log("submitMeasuredFilamentLength called");

            var eStepsMeasuredCmd = {
                "command": "eStepsMeasured",
                "measurement": self.measuredFilamentLength()
            };

            console.log("Sending request: " + JSON.stringify(eStepsMeasuredCmd));

            self.apiClient.makePostRequest(eStepsMeasuredCmd, function(data) {
                console.log("Call done:" + JSON.stringify(data));

                self.apiClient.makeGetRequest(function (data) {
                    console.log("GET call done:" + JSON.stringify(data));

                    if (data["newEstepsValid"] == "True") {
                        self.oldEsteps(data["oldEsteps"]);
                        self.newEsteps(data["newEsteps"]);
                    }
                });
            });
        };

        self.saveNewEsteps = function() {
            console.log("saveNewEsteps called");

            self.apiClient.makePostRequest(saveNewEstepsCmd, function(data) {
                console.log("Call done:" + JSON.stringify(data));
                // Here at least user should be informed that calib procedure is finished
            });
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
