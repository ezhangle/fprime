"""
fprime.fbuild.settings:

An implementation used to pull settings into the fprime build.  This version uses INI files in order to load the
settings from the settings.default file that is part of the F prime deployment directory.

@author mstarch
"""
import configparser  # Written after PY2 eol
import os


class IniSettings:
    """Class to load settings from INI files"""

    DEF_FILE = "settings.ini"
    SET_ENV = "FPRIME_SETTINGS_FILE"

    @staticmethod
    def find_fprime():
        """
        Finds F prime by recursing parent to parent until a matching directory is found.
        """
        needle = os.path.join(
            "cmake", "FPrime.cmake"
        )  # If the F prime cmake file exists
        path = os.getcwd()
        while path != os.path.dirname(path):
            if os.path.isfile(os.path.join(path, needle)):
                return os.path.abspath(os.path.normpath(path))
            path = os.path.dirname(path)
        raise FprimeLocationUnknownException(
            "Please set 'framework_path' in [fprime] section in 'settings.ini"
        )

    @staticmethod
    def read_safe_path(parser, section, key, ini_file):
        """
        Reads path(s), safely, from the config parser.  Validates the path(s) exists or raises an exception. Paths are
        separated by ':'.  This will also expand relative paths relative to the settings file.

        :param parser: parser to read from
        :param key: key to read from
        :param ini_file: ini_file path for clean errors
        :return: path, validated
        """
        base_dir = os.path.dirname(ini_file)
        all_paths = parser.get(section, key, fallback="").split(":")
        expanded = []
        for path in all_paths:
            if path == "" or path is None:
                continue
            full_path = os.path.abspath(os.path.normpath(os.path.join(base_dir, path)))
            if not os.path.exists(full_path):
                raise FprimeSettingsException(
                    "Non-existant path '{}' found in section '{}' option '{}' of file '{}'".format(
                        path, section, key, ini_file
                    )
                )
            expanded.append(full_path)
        return expanded

    @staticmethod
    def load(settings_file):
        """
        Load settings from specified file or from specified build directory. Either a specific file or the build
        directory must be not None.

        :param settings_file: (optional) file to load settings from (in INI format). Must be specified if build_dir is not.
        :param build_dir: (optional) directory to search for settings.ini. Must be specified if file is not.
        :return: a dictionary of needed settings
        """
        settings_file = (
            settings_file
            if settings_file is not None
            else os.path.join(IniSettings.DEF_FILE)
        )
        # Check file existence if specified
        if not os.path.exists(settings_file):
            print("[WARNING] Failed to find settings file: {}".format(settings_file))
            fprime_location = IniSettings.find_fprime()
            return {
                "framework_path": fprime_location,
            }
        confparse = configparser.ConfigParser()
        confparse.read(settings_file)
        # Search through F prime locations
        fprime_location = IniSettings.read_safe_path(
            confparse, "fprime", "framework_path", settings_file
        )
        if not fprime_location:
            fprime_location = IniSettings.find_fprime()
        else:
            fprime_location = fprime_location[0]
        # Read project root if it is available
        proj_root = IniSettings.read_safe_path(
            confparse, "fprime", "project_root", settings_file
        )
        proj_root = None if not proj_root else proj_root[0]
        # Read ac constants if it is available
        ac_consts = IniSettings.read_safe_path(
            confparse, "fprime", "ac_constants", settings_file
        )
        ac_consts = None if not ac_consts else ac_consts[0]
        # Read include constants if it is available
        config_dir = IniSettings.read_safe_path(
            confparse, "fprime", "config_directory", settings_file
        )
        config_dir = None if not config_dir else config_dir[0]

        # Read separate environment file if necessary
        env_file = IniSettings.read_safe_path(
            confparse, "fprime", "environment_file", settings_file
        )
        env_file = settings_file if not env_file else env_file[0]
        libraries = IniSettings.read_safe_path(
            confparse, "fprime", "library_locations", settings_file
        )
        environment = IniSettings.load_environment(env_file)
        settings = {
            "settings_file": settings_file,
            "framework_path": fprime_location,
            "library_locations": libraries,
            "default_toolchain": confparse.get(
                "fprime", "default_toolchain", fallback="native"
            ),
            "environment_file": env_file,
            "environment": environment,
        }
        # Set the project root
        if proj_root is not None:
            settings["project_root"] = proj_root
        # Set AC constants if available
        if ac_consts is not None:
            settings["ac_constants"] = ac_consts
        # Set the config dir
        if config_dir is not None:
            settings["config_dir"] = config_dir
        return settings

    @staticmethod
    def load_environment(env_file):
        """
        Load the environment from the given parser.

        :param env_file: load environment from this file
        :return: environment dictionary
        """
        parser = configparser.ConfigParser()
        parser.optionxform = str
        parser.read(env_file)
        env_dict = {}
        try:
            for key, value in parser.items("environment"):
                env_dict[key] = value
        except configparser.NoSectionError:
            pass  # Ignore missing environment
        return env_dict


class FprimeLocationUnknownException(Exception):
    """ Fprime location could not be determined """


class FprimeSettingsException(Exception):
    """ An exception for handling F prime settings misconfiguration """
