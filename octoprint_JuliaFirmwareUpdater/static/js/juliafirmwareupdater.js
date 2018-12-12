$(function() {
    function JuliaFirmwareUpdaterViewModel(parameters) {
        var PLUGIN_URL = PLUGIN_BASEURL + "JuliaFirmwareUpdater/";
        var TITLE = "Julia Firmware Updater";
        
        var self = this;

        self.VM_settings = parameters[0];
        self.VM_loginState = parameters[1];
        self.VM_connection = parameters[2];
        self.VM_printerState = parameters[3];

        self.configurationDialog = undefined;
        self.popup = undefined;

        // Landing page
        self.flashPort = ko.observable(undefined);
        self.hardwareNotReady = ko.observable("");

        // General settings
        self.configFlashMethod = ko.observable();
        self.showAvrdudeConfig = ko.observable(false);
        self.showBossacConfig = ko.observable(false);
        self.configEnablePostflashGcode = ko.observable();

        // Config settings for avrdude
        self.configAvrdudeMcu = ko.observable();
        self.configAvrdudePath = ko.observable();
        self.configAvrdudeConfigFile = ko.observable();
        self.configAvrdudeProgrammer = ko.observable();
        self.configAvrdudeBaudRate = ko.observable();
        self.configAvrdudeDisableVerification = ko.observable();
        self.avrdudePathBroken = ko.observable(false);
        self.avrdudePathOk = ko.observable(false);
        self.avrdudePathText = ko.observable();
        self.avrdudePathHelpVisible = ko.computed(function() {
            return self.avrdudePathBroken() || self.avrdudePathOk();
        });

        self.avrdudeConfPathBroken = ko.observable(false);
        self.avrdudeConfPathOk = ko.observable(false);
        self.avrdudeConfPathText = ko.observable();
        self.avrdudeConfPathHelpVisible = ko.computed(function() {
            return self.avrdudeConfPathBroken() || self.avrdudeConfPathOk();
        });

        // Config settings for bossac
        self.configBossacPath = ko.observable();
        self.configBossacDisableVerification = ko.observable()

        self.bossacPathBroken = ko.observable(false);
        self.bossacPathOk = ko.observable(false);
        self.bossacPathText = ko.observable();
        self.bossacPathHelpVisible = ko.computed(function() {
            return self.bossacPathBroken() || self.bossacPathOk();
        });

        // self.VM_connection.selectedPort.subscribe(function(value) {
        self.VM_settings.serial_port.subscribe(function(value) {
            // if (value === undefined) return;
            // self.flashPort(value);
            self.getHardwareState();
        });

        self.configFlashMethod.subscribe(function(value) {
            if(value == 'avrdude') {
                self.showBossacConfig(false);
                self.showAvrdudeConfig(true);
            } else if(value == 'bossac') {
                self.showBossacConfig(true);
                self.showAvrdudeConfig(false);
            } else {
                self.showBossacConfig(false);
                self.showAvrdudeConfig(false);
            }
        });

        self.getHardwareState = function() {
            $.ajax({
                url: PLUGIN_URL + "hardware/state",
                type: "GET",
                contentType: "application/json",
                success: function(response) {
                    console.log(response);
                    if (response) {
                        if (response.hasOwnProperty('port'))
                            self.flashPort(response.port);
                        if (response.hasOwnProperty('notready'))
                            self.hardwareNotReady(response.notready);
                    } else {
                        self.flashPort(undefined);
                        self.hardwareNotReady("State unknown!");
                    }
                },
                error: function() {
                    self.flashPort(undefined);
                    self.hardwareNotReady("State unknown!");
                }
            });
        };

        self.checkUpdate = function() {
            $.ajax({
                url: PLUGIN_URL + "update/check",
                type: "GET",
                contentType: "text/plain"
            });
        };

        self.startUpdate = function() {
            $.ajax({
                url: PLUGIN_URL + "update/start",
                type: "GET",
                contentType: "text/plain"
            });
        };

        self.startReflash = function() {
            $.ajax({
                url: PLUGIN_URL + "update/reflash",
                type: "GET",
                contentType: "text/plain"
            });
        };

        self._hardwareNotReady = function() {
            if (!self.Config.board_shortcode())
                return gettext("Hardware not defined!");

            if (self.VM_printerState.isPrinting() || self.VM_printerState.isPaused())
                return gettext("Print in progress!");

            if (!self.Config.flash_method())
                return gettext("Flash method undefined!");

            if (self.Config.flash_method() == "avrdude" && !self.Config.avrdude_avrmcu())
                return gettext("AVR MCU undefined!");

            if (self.Config.flash_method() == "avrdude" && !self.Config.avrdude_path())
                return gettext("avrdude undefined!");

            if (self.Config.flash_method() == "avrdude" && !self.Config.avrdude_programmer())
                return gettext("AVR programmer undefined!");

            if (self.Config.flash_method() == "bossac" && !self.Config.bossac_path())
                return gettext("bossac undefined!");

            if (!self.flashPort() || self.flashPort() == 'VIRTUAL')
                return gettext("Hardware port undefined!");

            return false;
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin !== "JuliaFirmwareUpdater") {
                return;
            }
            console.log(data);
            // var message;

            if (data.type === "status") {
                switch (data.status) {
                    case "update_check": {
                        self.showPopup(data.subtype, TITLE, data.message);
                        break;
                    }
                    case "update_start": {
                        self.showPopup(data.subtype, TITLE, data.message);
                        break;
                    }
                    // case "hardwarenotready": {
                    //     console.log(data.message);
                    //     self.hardwareNotReady(data.message);
                    //     break;
                    // }
                    case "flasherror": {
                        // if (!data.message) 
                        // var message = (data.message ? data.message : gettext("Unknown error"));

                        // if (data.subtype) {
                        //     switch (data.subtype) {
                        //         case "busy": {
                        //             message = gettext("Printer is busy.");
                        //             break;
                        //         }
                        //         case "port": {
                        //             message = gettext("Printer port is not available.");
                        //             break;
                        //         }
                        //         case "method": {
                        //             message = gettext("Flash method is not fully configured.");
                        //             break;
                        //         }
                        //         case "hexfile": {
                        //             message = gettext("Cannot read file to flash.");
                        //             break;
                        //         }
                        //         case "already_flashing": {
                        //             message = gettext("Already flashing.");
                        //         }
                        //     }
                        // }
                        if (data.message)
                            self.showPopup("error", "Flashing failed", data.message);
                        break;
                    }
                    case "success": {
                        self.showPopup("success", TITLE, data.message);
                        break;
                    }
                    case "progress": {
                        // if (data.subtype) {
                        //     switch (data.subtype) {
                        //         case "disconnecting": {
                        //             message = gettext("Disconnecting printer...");
                        //             break;
                        //         }
                        //         case "startingflash": {
                        //             // self.isBusy(true);
                        //             message = gettext("Starting flash...");
                        //             break;
                        //         }
                        //         case "writing": {
                        //             message = gettext("Writing memory...");
                        //             break;
                        //         }
                        //         case "erasing": {
                        //             message = gettext("Erasing memory...");
                        //             break;
                        //         }
                        //         case "verifying": {
                        //             message = gettext("Verifying memory...");
                        //             break;
                        //         }
                        //         // case "reconnecting": {
                        //         //     message = gettext("Reconnecting to printer...");
                        //         //     break;
                        //         // }
                        //     }
                        // }

                        if (data.message)
                            self.showPopup("info", TITLE, data.message);
                        break;
                    }
                    case "info": {
                        // self.alertType("alert-info");
                        // self.alertMessage(data.status_description);
                        // self.showAlert(true);
                        if (data.message)
                            self.showPopup("info", TITLE, data.message);
                        break;
                    }
                    case "error": {
                        if (data.message)
                            self.showPopup("error", TITLE, data.message);
                        break;
                    }
                }
            }
        };

        self.showPluginConfig = function() {
            // Load the general settings
            self.configFlashMethod(self.Config.flash_method());

            // Load the avrdude settings
            self.configAvrdudePath(self.Config.avrdude_path());
            self.configAvrdudeConfigFile(self.Config.avrdude_conf());
            self.configAvrdudeMcu(self.Config.avrdude_avrmcu());
            self.configAvrdudeProgrammer(self.Config.avrdude_programmer());
            self.configAvrdudeBaudRate(self.Config.avrdude_baudrate());
            if(self.Config.avrdude_disableverify() != 'false') {
                self.configAvrdudeDisableVerification(self.Config.avrdude_disableverify());
            }

            // Load the bossac settings
            self.configBossacPath(self.Config.bossac_path());
            self.configBossacDisableVerification(self.Config.bossac_disableverify());

            self.configurationDialog.modal();
        };

        self.onConfigClose = function() {
            // self._saveConfig();

            self.configurationDialog.modal("hide");
            // self.alertMessage(undefined);
            // self.showAlert(false);
        };

        self._saveConfig = function() {
            var data = {
                plugins: {
                    JuliaFirmwareUpdater: {
                        flash_method: self.configFlashMethod(),
                        avrdude_path: self.configAvrdudePath(),
                        avrdude_conf: self.configAvrdudeConfigFile(),
                        avrdude_avrmcu: self.configAvrdudeMcu(),
                        avrdude_programmer: self.configAvrdudeProgrammer(),
                        avrdude_baudrate: self.configAvrdudeBaudRate(),
                        avrdude_disableverify: self.configAvrdudeDisableVerification(),
                        bossac_path: self.configBossacPath(),
                        bossac_disableverify: self.configBossacDisableVerification()
                    }
                }
            };
            self.settingsViewModel.saveData(data);
        };

        self.onConfigHidden = function() {
            self.avrdudePathBroken(false);
            self.avrdudePathOk(false);
            self.avrdudePathText("");
            self.bossacPathBroken(false);
            self.bossacPathOk(false);
            self.bossacPathText("");
        };

        self.testAvrdudePath = function() {
            $.ajax({
                url: API_BASEURL + "util/test",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "path",
                    path: self.configAvrdudePath(),
                    check_type: "file",
                    check_access: "x"
                }),
                contentType: "application/json; charset=UTF-8",
                success: function(response) {
                    if (!response.result) {
                        if (!response.exists) {
                            self.avrdudePathText(gettext("The path doesn't exist"));
                        } else if (!response.typeok) {
                            self.avrdudePathText(gettext("The path is not a file"));
                        } else if (!response.access) {
                            self.avrdudePathText(gettext("The path is not an executable"));
                        }
                    } else {
                        self.avrdudePathText(gettext("The path is valid"));
                    }
                    self.avrdudePathOk(response.result);
                    self.avrdudePathBroken(!response.result);
                }
            })
        };

        self.testBossacPath = function() {
            $.ajax({
                url: API_BASEURL + "util/test",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "path",
                    path: self.configBossacPath(),
                    check_type: "file",
                    check_access: "x"
                }),
                contentType: "application/json; charset=UTF-8",
                success: function(response) {
                    if (!response.result) {
                        if (!response.exists) {
                            self.bossacPathText(gettext("The path doesn't exist"));
                        } else if (!response.typeok) {
                            self.bossacPathText(gettext("The path is not a file"));
                        } else if (!response.access) {
                            self.bossacPathText(gettext("The path is not an executable"));
                        }
                    } else {
                        self.bossacPathText(gettext("The path is valid"));
                    }
                    self.bossacPathOk(response.result);
                    self.bossacPathBroken(!response.result);
                }
            })
        };

        self.testAvrdudeConf = function() {
            $.ajax({
                url: API_BASEURL + "util/test",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "path",
                    path: self.configAvrdudeConfigFile(),
                    check_type: "file",
                    check_access: "r"
                }),
                contentType: "application/json; charset=UTF-8",
                success: function(response) {
                    if (!response.result) {
                        if (!response.exists) {
                            self.avrdudeConfPathText(gettext("The path doesn't exist"));
                        } else if (!response.typeok) {
                            self.avrdudeConfPathText(gettext("The path is not a file"));
                        } else if (!response.access) {
                            self.avrdudeConfPathText(gettext("The path is not readable"));
                        }
                    } else {
                        self.avrdudeConfPathText(gettext("The path is valid"));
                    }
                    self.avrdudeConfPathOk(response.result);
                    self.avrdudeConfPathBroken(!response.result);
                }
            });
        };

        // Popup Messages

        self.showPopup = function(message_type, title, text){
            if (self.popup !== undefined){
                self.closePopup();
            }
            self.popup = new PNotify({
                title: gettext(title),
                text: text,
                type: message_type,
                hide: false
            });
        };

        self.closePopup = function() {
            if (self.popup !== undefined) {
                self.popup.remove();
            }
        };

        self.onStartup = function() {
            self.configurationDialog = $("#settings_jfu_config");
        };

        self.onBeforeBinding = function() {
            console.log('Binding JuliaFirmwareUpdaterViewModel')

            self.Config = self.VM_settings.settings.plugins.JuliaFirmwareUpdater;

            console.log(self.Config);
            console.log(self.VM_printerState);
        };

        self.onSettingsShown = function() {
            // self.hardwareNotReady(self._hardwareNotReady());
            self.getHardwareState();
        }
    }

    OCTOPRINT_VIEWMODELS.push([
        JuliaFirmwareUpdaterViewModel,
        ["settingsViewModel", "loginStateViewModel", "connectionViewModel", "printerStateViewModel"],
        ["#settings_plugin_JuliaFirmwareUpdater"]
    ]);
});
