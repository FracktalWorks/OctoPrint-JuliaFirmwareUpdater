import re
import datetime

URL_REPO_VERSION = 'https://raw.githubusercontent.com/FracktalWorks/Julia2018MarlinHex/master/info.json'
URL_REPO_HEX = 'https://raw.githubusercontent.com/FracktalWorks/Julia2018MarlinHex/master/J18{}_mega.hex'

STR_DEFAULT_DATETIME = '2018-01-01 00:00'
DATE_FMT_FIRMWARE = '%y%m%d_%H%M'
DATE_FMT_REPO = '%Y-%m-%d %H:%M'

PLUGINS = ["Julia2018AdvancedTouchUI",
           "Julia2018ExtendedTouchUI",
           "Julia2018ProSingleTouchUI",
           "Julia2018ProDualTouchUI",
           "Julia2018ProSingleABLTouchUI",
           "Julia2018ProDualABLTouchUI"
           ]
VARIANTS = ["RX", "RE", "PS", "PD", "PT", "PE"]


class FlashException(Exception):
    def __init__(self, reason, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
        self.reason = reason


def update_check_time():
    try:
        return datetime.datetime.now().strftime(DATE_FMT_REPO)
    except:
        return None


def get_hex_url(variant):
    if variant is None or variant not in VARIANTS:
        return None
    return URL_REPO_HEX.format(variant)


def update_present(board_time, repo_time):
    try:
        dt_board = datetime.datetime.strptime(board_time, DATE_FMT_REPO)
        dt_repo = datetime.datetime.strptime(repo_time, DATE_FMT_REPO)
        return dt_repo > dt_board

    except:
        return False


def validate_repo_timetstamp(str):
    try:
        datetime.datetime.strptime(str, DATE_FMT_REPO)
        return True
    except:
        return False


def convert_firmware_timestamp(str):
    try:
        d = datetime.datetime.strptime(str, DATE_FMT_FIRMWARE)
        return d.strftime(DATE_FMT_REPO)
    except:
        return STR_DEFAULT_DATETIME


def version_match_julia18(test_str):
    if test_str is None:
        return None

    regex = r"Marlin J18([A-Z]{2})_([0-9]{6}_[0-9]{4})_HA"
    matches = re.search(regex, test_str)

    if matches and len(matches.groups()) == 2:
        if matches.group(1) not in VARIANTS:
            return None

        return {
            'VARIANT': matches.group(1),
            'VERSION': convert_firmware_timestamp(matches.group(2))
        }
    else:
        return None


def version_match_fallback(plugin_manager):
    if plugin_manager is None or plugin_manager.get_plugin is None:
        return None

    found = []

    for i, val in enumerate(PLUGINS):
        if plugin_manager.get_plugin(val):
            found.append(VARIANTS[i])

    if len(found) != 1:
        return None

    return {
        'VARIANT': found[0],
        'VERSION': STR_DEFAULT_DATETIME
    }
