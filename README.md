# OctoPrint-Calibration

3D Printer calibration plugin for OctoPrint.
Currently it supports a guided e steps calibration procedure.
The result of it is stored in an SQLite database so that it can be reviewed later.

Further planned features are:
  - ABL procedure
  - PID autotune procedure storing the results in the SQLite database
  - Slicer Flow calib
  - Retraction tuning
  - Temp tuning
  - Accel tuning
  - Linear Advance

*Note:* This is a Python3 only plugin. I will not support an outdated version of Python.

## Reasons for creating this plugin

In the past I did calibrations on my 3D printers by using the nice [calibration site created by TeachingTech](https://teachingtechyt.github.io/calibration.html).
This included typing all the required commands via the OctoPrint terminal.
In order to have the important parameters saved for later review (e.g. for e steps calibration this would be filament name, filament type, hotend temperature, as well as old and new e steps value) I put them into a txt file.

Therefore, I thought it would be nice to have this functionality all in an OctoPrint plugin.
This is done by providing a guided procedure for calibration as well as persistency of the results in an SQLite database.

## Setup

Install via the bundled [Plugin Manager](https://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html)
or manually using this URL:

    https://github.com/sg-dev1/OctoPrint-Calibration/archive/master.zip

**TODO:** Describe how to install your plugin, if more needs to be done than just installing it via pip or through
the plugin manager.

## Configuration

**TODO:** Describe your plugin's configuration options (if any).
