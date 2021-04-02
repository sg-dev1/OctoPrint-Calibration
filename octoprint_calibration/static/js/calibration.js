/*
 * View model for OctoPrint-Calibration
 *
 * Author: Stefan G
 * License: AGPLv3
 */
$(function() {
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
            
            $.ajax({
                url: API_BASEURL + "plugin/" + PLUGIN_ID,
                type: "post",
                dataType: "json",
                contentType: 'application/json',
                //data: "{\"command\": \"calibrateESteps\"}"
                /*JSON.stringify({
                    "command": "calibrateESteps",
                })*/
                data: JSON.stringify(calibrateEStepsCmd)
            }).done(function( data ){
                //responseHandler(data)
                //shoud be done by the server to make sure the server is informed countdownDialog.modal('hide');
                //countdownDialog.modal('hide');
                //countdownCircle = null;
                console.log("Call done:" + JSON.stringify(data));
            });
        };

        self.startExtruding = function() {
            console.log("startExtruding called");

            $.ajax({
                url: API_BASEURL + "plugin/" + PLUGIN_ID,
                type: "post",
                dataType: "json",
                contentType: 'application/json',
                data: JSON.stringify(startExtrudingCmd)
            }).done(function( data ){
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

            $.ajax({
                url: API_BASEURL + "plugin/" + PLUGIN_ID,
                type: "post",
                dataType: "json",
                contentType: 'application/json',
                data: JSON.stringify(eStepsMeasuredCmd)
            }).done(function( data ){
                console.log("Call done:" + data);

                $.ajax({
                    url: API_BASEURL + "plugin/" + PLUGIN_ID,
                    type: "get"
                }).done(function( data ){
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

            $.ajax({
                url: API_BASEURL + "plugin/" + PLUGIN_ID,
                type: "post",
                dataType: "json",
                contentType: 'application/json',
                data: JSON.stringify(saveNewEstepsCmd)
            }).done(function( data ){
                console.log("Call done:" + JSON.stringify(data));
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
