class Settings:
    @property
    def flash_method(self):
        return self._settings.get(["flash_method"])

    @property
    def avrdude_path(self):
        return self._settings.get(["avrdude_path"])

    @property
    def avrdude_conf(self):
        return self._settings.get(["avrdude_conf"])
    
    @property
    def avrdude_avrmcu(self):
        return self._settings.get(["avrdude_avrmcu"])

    @property
    def avrdude_programmer(self):
        return self._settings.get(["avrdude_programmer"])

    @property
    def avrdude_baudrate(self):
        return self._settings.get(["avrdude_baudrate"])

    @property
    def avrdude_disableverify(self):
        return self._settings.get_boolean(["avrdude_disableverify"])

    @property
    def bossac_path(self):
        return self._settings.get(["bossac_path"])

    @property
    def bossac_disableverify(self):
        return self._settings.get_boolean(["bossac_disableverify"])

    @property
    def board_shortcode(self):
        return self._settings.get(["board_shortcode"])

    @property
    def version_board(self):
        return self._settings.get(["version_board"])

    @property
    def version_repo(self):
        return self._settings.get(["version_repo"])

    @property
    def update_check(self):
        return self._settings.get_boolean(["update_check"])
