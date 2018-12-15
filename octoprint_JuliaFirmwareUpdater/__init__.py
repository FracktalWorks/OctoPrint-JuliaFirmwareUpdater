# coding=utf-8
from __future__ import absolute_import

import logging
import logging.handlers
import os
import requests
import tempfile
import threading
import flask
# from flask import jsonify

import octoprint.plugin

import octoprint.server.util.flask
# from octoprint.server import admin_permission, NO_CONTENT
from octoprint.server import NO_CONTENT
from octoprint.events import Events
# import json

from . import common
from . import avrdude
from . import bossac
from . import settings


class JuliaFirmwareUpdaterPlugin(octoprint.plugin.BlueprintPlugin,
                                 octoprint.plugin.TemplatePlugin,
                                 octoprint.plugin.AssetPlugin,
                                 octoprint.plugin.SettingsPlugin,
                                 octoprint.plugin.EventHandlerPlugin,
                                 avrdude.Avrdude,
                                 bossac.Bossac,
                                 settings.Settings):
    '''
    IPC
    '''
    @octoprint.plugin.BlueprintPlugin.route("/hardware/state", methods=["GET"])
    def route_hardware_state(self):
        port = self._get_hardware_port()
        port = False if port is None else port
        return flask.jsonify(port=port, notready=self._hardware_not_ready())

    @octoprint.plugin.BlueprintPlugin.route("/update/<task>", methods=["GET"])
    def route_update(self, task):
        if task == "check":
            status = self._update_check_inv()
            # self._logger.info(status)
            if status == 0:
                subtype = "info"
                message = "No updates found"
            elif status == -1:
                subtype = "success"
                message = "Updates found!"
            else:
                subtype = "error"
                message = status
            self._send_status("update_check", subtype=subtype, message=message)
        elif task == "start" or task == "reflash":
            status = self._flash_firmware_inv(reflash=(task == "reflash"))
            # self._logger.info(status)
            self._send_status("update_start",
                              subtype="success" if not status else "error",
                              message="Firmware flashing started" if not status else status)
        else:
            return flask.make_response("Invalid request", 404)
        return flask.make_response(NO_CONTENT)

    def _send_status(self, status, subtype=None, message=None):
        if status == "flasherror":
            if not message:
                message = "Unknown error"
            if subtype:
                # if subtype == "busy":
                #     message = "Printer is busy."
                # if subtype == "port":
                #     message = "Printer port is not available."
                if subtype == "method":
                    message = "Flash method is not fully configured."
                # if subtype == "hexfile":
                #     message = "Cannot read file to flash."
                if subtype == "already_flashing":
                    message = "Already flashing."
        if status == "success":
            message = "Flashing successful"
        if status == "progress":
            if subtype:
                if subtype == "disconnecting":
                    message = "Disconnecting printer..."
                if subtype == "startingflash":
                    message = "Starting flash..."
                if subtype == "writing":
                    message = "Writing memory..."
                if subtype == "erasing":
                    message = "Erasing memory..."
                if subtype == "verifying":
                    message = "Verifying memory..."
                if subtype == "reconnecting":
                    message = "Reconnecting to printer..."

        msg = dict(type="status",
                   status=status,
                   subtype=subtype,
                   message=message)
        self._plugin_manager.send_plugin_message(self._identifier, msg)

    '''
    Check for update
    '''
    def _update_check_inv(self):    # False if update found else reason
        state = self._hardware_not_ready()
        if state:
            return state

        try:
            resp = requests.get(url=common.URL_REPO_VERSION)
            data = resp.json()
            self._logger.info("Repo data\n" + str(data))

            if data is not None and data['version'] is not None:
                time = str(common.update_check_time())
                self._logger.info("Update time: " + time)
                self._settings.set(["update_check"], time)
                if common.validate_repo_timetstamp(data['version']):
                    self._settings.set(["version_repo"], data['version'])
                self._settings.save()
            else:
                return "Invalid data received"
        except:
            # self._logger.error("Update check failed")
            return "Update check failed"

        if common.update_present(self.version_board, self.version_repo):
            return -1
        return 0

    '''
    Hardware
    '''
    def _get_hardware_port(self):
        port = self._printer.get_current_connection()[1]
        if port is None or port == 'VIRTUAL':
            return None
        if port == 'AUTO':
            # self._logger.info(json.dumps(self._printer.get_connection_options()))
            connections = self._printer.get_connection_options()['ports']
            if connections and len(connections) > 0:
                for val in connections:
                    if val != 'VIRTUAL':
                        return val
        return port

    def _hardware_not_ready(self):
        msg = False
        if self._get_hardware_port() is None:
            msg = "Port not connected!"
        if self._printer.is_printing() or self._printer.is_paused():
            msg = "Print in progress!"
        if not self.flash_method:
            msg = "Flash method undefined!"
        if self.flash_method == "avrdude" and not self.avrdude_avrmcu:
            msg = "AVR MCU undefined!"
        if self.flash_method == "avrdude" and not self.avrdude_path:
            msg = "avrdude undefined!"
        if self.flash_method == "avrdude" and not self.avrdude_programmer:
            msg = "AVR programmer undefined!"
        if self.flash_method == "bossac" and not self.bossac_path:
            msg = "bossac undefined!"

        # self._send_status("hardwarenotready", message=msg)
        return msg

    def _parse_firmware_info(self, printer_message):
        from octoprint.util.comm import parse_firmware_line
        # Create a dict with all the keys/values returned by the M115 request
        data = parse_firmware_line(printer_message)
        # self._update_check_inv(data['FIRMWARE_NAME'])

        port = self._get_hardware_port()
        if port is None:
            return False

        self._logger.info("Port: " + port)

        machine_info = common.version_match_julia18(data['FIRMWARE_NAME'])       # from firmware
        if machine_info is None:
            machine_info = common.version_match_fallback(self._plugin_manager)   # from UI plugin
        self._logger.info("Machine data\n" + str(machine_info))

        if machine_info is None:
            self._settings.set(["board_shortcode"], None)
            self._settings.set(["version_board"], None)
            self._settings.save()
            return False

        self._settings.set(["board_shortcode"], machine_info['VARIANT'])
        self._settings.set(["version_board"], machine_info['VERSION'])
        self._settings.save()
        return True

    def _flash_firmware_inv(self, reflash=False):  # false if flash worker started else error
        state = self._hardware_not_ready()
        if state:
            return state

        if self._flash_thread is not None:
            self._logger.debug("Cannot flash firmware, already flashing")
            return "Already flashing firmware in another thread"

        port = self._get_hardware_port()
        if not port:
            return "Printer port is not available."

        if not self.board_shortcode:
            return "Board could not be determined"
        if not self.version_board:
            return "Installed firmware version could not be determined"
        if not self.version_repo:
            return "Previous update check failed"

        if not (reflash or common.update_present(self.version_board, self.version_repo)):
            return "No update present!"

        firmware_url = common.get_hex_url(self.board_shortcode)
        if not firmware_url:
            self._logger.debug("Invalid URL")
            return "Invalid firmware URL"

        method = self.flash_method
        if method in self._flash_prechecks:
            if not self._flash_prechecks[method]():
                self._logger.debug("Flash method precheck failed")
                return "Internal error"

        self._flash_thread = threading.Thread(target=self._flash_worker, args=(method, port, firmware_url))
        self._flash_thread.daemon = True
        self._flash_thread.start()
        return False

    def _flash_worker(self, method, printer_port, firmware_url):
        try:
            self._logger.info("Firmware update started")

            if method not in self._flash_methods:
                self._logger.error("Unsupported flashing method: {}".format(method))
                return

            flash_callable = self._flash_methods[method]
            if not callable(flash_callable):
                self._logger.error("Don't have a callable for flashing method {}: {!r}".format(method, flash_callable))
                return

            file_to_flash = None
            try:
                file_to_flash = tempfile.NamedTemporaryFile(mode='r+b', delete=False)
                file_to_flash.close()

                r = requests.get(firmware_url, stream=True, timeout=30)
                r.raise_for_status()
                with open(file_to_flash.name, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                            f.flush()
            except:
                if file_to_flash:
                    try:
                        os.remove(file_to_flash.name)
                    except:
                        self._logger.exception("Error while trying to delete the temporary hex file")
                error_message = "Error while downloading the hex file from server"
                self._send_status("flasherror", subtype="hexfile", message=error_message)
                self._logger.exception(error_message)
                return

            firmware = file_to_flash.name

            reconnect = None
            if self._printer.is_operational():
                _, current_port, current_baudrate, current_profile = self._printer.get_current_connection()

                reconnect = (current_port, current_baudrate, current_profile)
                self._logger.info("Disconnecting from printer")
                self._send_status("progress", subtype="disconnecting")
                self._printer.disconnect()

            self._send_status("progress", subtype="startingflash")

            try:
                if flash_callable(firmware=firmware, printer_port=printer_port):
                    message = u"Flashing successful."
                    self._logger.info(message)
                    self._console_logger.info(message)
                    self._send_status("success")

            except:
                self._logger.exception(u"Error while attempting to flash")
                self._send_status("flasherror")
            finally:
                try:
                    os.remove(firmware)
                except:
                    self._logger.exception(u"Could not delete temporary hex file at {}".format(firmware))

            if reconnect is not None:
                port, baudrate, profile = reconnect
                self._logger.info("Reconnecting to printer: port={}, baudrate={}, profile={}".format(port, baudrate, profile))
                # self._send_status("progress", subtype="reconnecting")
                self._printer.connect(port=port, baudrate=baudrate, profile=profile)
        except Exception as e:
            self._logger.error(e.message)
        finally:
            self._flash_thread = None

    '''
    Plugin management
    '''

    def __init__(self):
        self._flash_thread = None

        self._flash_prechecks = dict()
        self._flash_methods = dict()

        self._console_logger = None

    def initialize(self):
        # TODO: make method configurable via new plugin hook "octoprint.plugin.firmwareupdater.flash_methods",
        # also include prechecks
        self._flash_prechecks = dict(avrdude=self._check_avrdude, bossac=self._check_bossac)
        self._flash_methods = dict(avrdude=self._flash_avrdude, bossac=self._flash_bossac)

        console_logging_handler = logging.handlers.RotatingFileHandler(self._settings.get_plugin_logfile_path(postfix="console"), maxBytes=(2 * 1024 * 1024))
        console_logging_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        console_logging_handler.setLevel(logging.DEBUG)

        self._console_logger = logging.getLogger("octoprint.plugins.softwareupdate.console")
        self._console_logger.addHandler(console_logging_handler)
        self._console_logger.setLevel(logging.DEBUG)
        self._console_logger.propagate = False

    def on_event(self, event, payload):
        # self._logger.info("Got event: {}".format(event))
        if event == Events.CONNECTED:
            self._logger.info("Got CONNECTED event: " + str(payload))
            # self._logger.warning(self._update_start_inv(reflash=True))

    def get_assets(self):
        return dict(js=["js/juliafirmwareupdater.js"])

    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=True)
        ]

    def get_settings_defaults(self):
        return dict(
            flash_method="avrdude",
            avrdude_path="/usr/bin/avrdude",
            avrdude_conf=None,
            avrdude_avrmcu="m2560",
            avrdude_programmer="wiring",
            avrdude_baudrate="115200",
            avrdude_disableverify=False,
            bossac_path='/usr/bin/bossac',
            bossac_disableverify=False,

            board_shortcode=None,
            version_board=None,
            version_repo=None,
            update_check=False
        )

    '''
    Hooks
    '''
    def printer_message_received_hook(self, comm, line, *args, **kwargs):
        if "FIRMWARE_NAME" not in line:
            return line
        self._parse_firmware_info(line)
        return line

    def update_hook(self):
        return dict(
            juliafirmwareupdater=dict(
                displayName="Julia Firmware Updater",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="OctoPrint",
                repo="FracktalWorks/OctoPrint-JuliaFirmwareUpdater",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/FracktalWorks/OctoPrint-JuliaFirmwareUpdater/archive/{target_version}.zip"
            )
        )


__plugin_name__ = "Julia Firmware Updater"


def __plugin_load__():
    global __plugin_implementation__
    global __plugin_hooks__

    __plugin_implementation__ = JuliaFirmwareUpdaterPlugin()

    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.update_hook,
        "octoprint.comm.protocol.gcode.received": __plugin_implementation__.printer_message_received_hook
    }
