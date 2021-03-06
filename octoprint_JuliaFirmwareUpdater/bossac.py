import os
import time
import serial
from serial import SerialException

from common import FlashException


class Bossac:
    BOSSAC_ERASING = "Erase flash"
    BOSSAC_WRITING = "bytes to flash"
    BOSSAC_VERIFYING = "bytes of flash"
    BOSSAC_NODEVICE = "No device found on"

    def _flash_bossac(self, firmware=None, printer_port=None):
        assert(firmware is not None)
        assert(printer_port is not None)

        # bossac_path = self._settings.get(["bossac_path"])
        # bossac_disableverify = self._settings.get(["bossac_disableverify"])

        working_dir = os.path.dirname(self.bossac_path)

        bossac_command = [self.bossac_path, "-i", "-p", printer_port, "-U", "false", "-e", "-w"]
        if not self.bossac_disableverify:
            bossac_command += ["-v"]
        bossac_command += ["-b", firmware, "-R"]

        self._logger.info(u"Attempting to reset the board to SAM-BA")
        if not self._reset_1200(printer_port):
            self._logger.error(u"Reset failed")
            return False

        import sarge
        self._logger.info(u"Running %r in %s" % (' '.join(bossac_command), working_dir))
        self._console_logger.info(" ".join(bossac_command))
        try:
            p = sarge.run(bossac_command, cwd=working_dir, async=True, stdout=sarge.Capture(buffer_size=1), stderr=sarge.Capture(buffer_size=1))
            p.wait_events()

            while p.returncode is None:
                output = p.stdout.read(timeout=0.5)
                if not output:
                    p.commands[0].poll()
                    continue

                for line in output.split("\n"):
                    if line.endswith("\r"):
                        line = line[:-1]
                    self._console_logger.info(u"> {}".format(line))

                    if self.BOSSAC_ERASING in line:
                        self._logger.info(u"Erasing memory...")
                        self._send_status("progress", subtype="erasing")
                    elif self.BOSSAC_WRITING in line:
                        self._logger.info(u"Writing memory...")
                        self._send_status("progress", subtype="writing")
                    elif self.BOSSAC_VERIFYING in line:
                        self._logger.info(u"Verifying memory...")
                        self._send_status("progress", subtype="verifying")
                    elif self.AVRDUDE_TIMEOUT in line:
                        p.close()
                        raise FlashException("Timeout communicating with programmer")
                    elif self.BOSSAC_NODEVICE in line:
                        raise FlashException("No device found")
                    elif self.AVRDUDE_ERROR_VERIFICATION in line:
                        raise FlashException("Error verifying flash")
                    elif self.AVRDUDE_ERROR in line:
                        raise FlashException("bossac error: " + output[output.find(self.AVRDUDE_ERROR) + len(self.AVRDUDE_ERROR):].strip())

            if p.returncode == 0:
                return True
            else:
                raise FlashException("bossac returned code {returncode}".format(returncode=p.returncode))

        except FlashException as ex:
            self._logger.error(u"Flashing failed. {error}.".format(error=ex.reason))
            self._send_status("flasherror", message=ex.reason)
            return False
        except:
            self._logger.exception(u"Flashing failed. Unexpected error.")
            self._send_status("flasherror")
            return False

    def _check_bossac(self):
        # bossac_path = self._settings.get(["bossac_path"])

        if self.bossac_path is None:
            self._logger.error(u"Path to bossac is not set.")
            return False
        if not os.path.exists(self.bossac_path):
            self._logger.error(u"Path to bossac does not exist: {path}".format(path=self.bossac_path))
            return False
        elif not os.path.isfile(self.bossac_path):
            self._logger.error(u"Path to bossac is not a file: {path}".format(path=self.bossac_path))
            return False
        elif not os.access(self.bossac_path, os.X_OK):
            self._logger.error(u"Path to bossac is not executable: {path}".format(path=self.bossac_path))
            return False
        else:
            return True

    def _reset_1200(self, printer_port=None):
        assert(printer_port is not None)
        self._logger.info(u"Toggling '{port}' at 1200bps".format(port=printer_port))
        try:
            ser = serial.Serial(port=printer_port,
                                baudrate=1200,
                                parity=serial.PARITY_NONE,
                                stopbits=serial.STOPBITS_ONE,
                                bytesize=serial.EIGHTBITS,
                                timeout=2000)
            time.sleep(5)
            ser.close()
        except SerialException as ex:
            self._logger.exception(u"Board reset failed: {error}".format(error=str(ex)))
            self._send_status("flasherror", message="Board reset failed")
            return False

        return True
