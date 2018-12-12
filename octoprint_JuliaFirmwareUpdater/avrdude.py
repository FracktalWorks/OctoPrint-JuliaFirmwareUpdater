import os
from common import FlashException


class Avrdude:
    AVRDUDE_WRITING = "writing flash"
    AVRDUDE_VERIFYING = "reading on-chip flash data"
    AVRDUDE_TIMEOUT = "timeout communicating with programmer"
    AVRDUDE_ERROR = "ERROR:"
    AVRDUDE_ERROR_SYNC = "not in sync"
    AVRDUDE_ERROR_VERIFICATION = "verification error"
    AVRDUDE_ERROR_DEVICE = "can't open device"

    def _flash_avrdude(self, firmware=None, printer_port=None):
        assert(firmware is not None)
        assert(printer_port is not None)

        # avrdude_path = self._settings.get(["avrdude_path"])
        # avrdude_conf = self._settings.get(["avrdude_conf"])
        # avrdude_avrmcu = self._settings.get(["avrdude_avrmcu"])
        # avrdude_programmer = self._settings.get(["avrdude_programmer"])
        # avrdude_baudrate = self._settings.get(["avrdude_baudrate"])
        # avrdude_disableverify = self._settings.get(["avrdude_disableverify"])

        working_dir = os.path.dirname(self.avrdude_path)

        avrdude_command = [self.avrdude_path, "-v", "-q", "-p", self.avrdude_avrmcu, "-c", self.avrdude_programmer, "-P", printer_port, "-D"]
        if self.avrdude_conf is not None and self.avrdude_conf != "":
            avrdude_command += ["-C", self.avrdude_conf]
        if self.avrdude_baudrate is not None and self.avrdude_baudrate != "":
            avrdude_command += ["-b", self.avrdude_baudrate]
        if self.avrdude_disableverify:
            avrdude_command += ["-V"]

        avrdude_command += ["-U", "flash:w:" + firmware + ":i"]

        import sarge
        self._logger.info(u"Running %r in %s" % (' '.join(avrdude_command), working_dir))
        self._console_logger.info(" ".join(avrdude_command))
        try:
            p = sarge.run(avrdude_command, cwd=working_dir, async=True, stdout=sarge.Capture(), stderr=sarge.Capture())
            p.wait_events()

            while p.returncode is None:
                output = p.stderr.read(timeout=0.5)
                if not output:
                    p.commands[0].poll()
                    continue

                for line in output.split("\n"):
                    if line.endswith("\r"):
                        line = line[:-1]
                    self._console_logger.info(u"> {}".format(line))

                if self.AVRDUDE_WRITING in output:
                    self._logger.info(u"Writing memory...")
                    self._send_status("progress", subtype="writing")
                elif self.AVRDUDE_VERIFYING in output:
                    self._logger.info(u"Verifying memory...")
                    self._send_status("progress", subtype="verifying")
                elif self.AVRDUDE_TIMEOUT in output:
                    p.commands[0].kill()
                    p.close()
                    raise FlashException("Timeout communicating with programmer")
                elif self.AVRDUDE_ERROR_DEVICE in output:
                    p.commands[0].kill()
                    p.close()
                    raise FlashException("Error opening serial device")
                elif self.AVRDUDE_ERROR_VERIFICATION in output:
                    p.commands[0].kill()
                    p.close()
                    raise FlashException("Error verifying flash")
                elif self.AVRDUDE_ERROR_SYNC in output:
                    p.commands[0].kill()
                    p.close()
                    raise FlashException("Avrdude says: 'not in sync" + output[output.find(self.AVRDUDE_ERROR_SYNC) + len(self.AVRDUDE_ERROR_SYNC):].strip() + "'")
                elif self.AVRDUDE_ERROR in output:
                    raise FlashException("Avrdude error: " + output[output.find(self.AVRDUDE_ERROR) + len(self.AVRDUDE_ERROR):].strip())

            if p.returncode == 0:
                return True
            else:
                raise FlashException("Avrdude returned code {returncode}".format(returncode=p.returncode))

        except FlashException as ex:
            self._logger.error(u"Flashing failed. {error}.".format(error=ex.reason))
            self._send_status("flasherror", message=ex.reason)
            return False
        except:
            self._logger.exception(u"Flashing failed. Unexpected error.")
            self._send_status("flasherror")
            return False

    def _check_avrdude(self):
        # avrdude_path = self._settings.get(["avrdude_path"])
        # avrdude_avrmcu = self._settings.get(["avrdude_avrmcu"])
        # avrdude_programmer = self._settings.get(["avrdude_programmer"])

        if not os.path.exists(self.avrdude_path):
            self._logger.error(u"Path to avrdude does not exist: {path}".format(path=self.avrdude_path))
            return False
        elif not os.path.isfile(self.avrdude_path):
            self._logger.error(u"Path to avrdude is not a file: {path}".format(path=self.avrdude_path))
            return False
        elif not os.access(self.avrdude_path, os.X_OK):
            self._logger.error(u"Path to avrdude is not executable: {path}".format(path=self.avrdude_path))
            return False
        elif not self.avrdude_avrmcu:
            self._logger.error(u"AVR MCU type has not been selected.")
            return False
        elif not self.avrdude_programmer:
            self._logger.error(u"AVR programmer has not been selected.")
            return False
        else:
            return True
