from __future__ import annotations

import configparser
import configparser as _configparser
import os
import typing
from dataclasses import dataclass

from flytekit.exceptions import user as _user_exceptions


@dataclass
class LegacyConfigEntry(object):
    """
    Creates a record for the config entry. contains
    Args:
        section: section the option should be found unddd
        option: the option str to lookup
        type_: Expected type of the value
    """
    section: str
    option: str
    type_: typing.Type = str

    def read_from_env(self) -> typing.Optional[typing.Any]:
        """
        Reads the config entry from environment variable, the structure of the env var is current
        ``FLYTE_{SECTION}_{OPTION}`` all upper cased. We will change this in the future.
        :return:
        """
        env = f"FLYTE_{self.section.upper()}_{self.option.upper()}"
        return os.environ.get(env, None)

    def read_from_file(
        self, cfg: ConfigFile, transform: typing.Optional[typing.Callable] = None
    ) -> typing.Optional[typing.Any]:
        if not cfg:
            return None
        try:
            v = cfg.get(self)
            return transform(v) if transform else v
        except configparser.Error:
            pass
        return None


@dataclass
class ConfigEntry(object):
    """
    A top level Config entry holder, that holds multiple different represnetations of the config.
    Currently only legacy is supported, but more will be added soon
    """

    legacy: LegacyConfigEntry
    transform: typing.Optional[typing.Callable[[str], typing.Any]] = None

    def read(self, cfg: typing.Optional[ConfigFile] = None) -> typing.Optional[typing.Any]:
        """
        Reads the config Entry from the various sources in the following order,
         First try to read from environment, if not then try to read from the given config file
        :param cfg:
        :return:
        """
        return self.legacy.read_from_env() or self.legacy.read_from_file(cfg, self.transform)


class ConfigFile(object):
    def __init__(self, location: str):
        """
        Load the config from this location
        """
        self._location = location
        # TODO, we can choose legacy vs other config using the extension. For .yaml, we can use the new config parser
        self._legacy_config = self._read_legacy_config(location)

    def _read_legacy_config(self, location: str) -> _configparser.ConfigParser:
        c = _configparser.ConfigParser()
        c.read(self._location)
        if c.has_section("internal"):
            raise _user_exceptions.FlyteAssertion(
                "The config file '{}' cannot contain a section for internal " "only configurations.".format(location)
            )
        return c

    def _get_from_legacy(self, c: LegacyConfigEntry) -> typing.Any:
        if issubclass(c.type_, bool):
            return self._legacy_config.getboolean(c.section, c.option)

        if issubclass(c.type_, int):
            return self._legacy_config.getint(c.section, c.option)

        if issubclass(c.type_, list):
            v = self._legacy_config.get(c.section, c.option)
            return v.split(",")

        return self._legacy_config.get(c.section, c.option)

    def get(self, c: typing.Union[LegacyConfigEntry]) -> typing.Any:
        if isinstance(c, LegacyConfigEntry):
            return self._get_from_legacy(c)
        raise NotImplemented("Support for other config types besides .ini / .config files not yet supported")

    @property
    def legacy_config(self) -> _configparser.ConfigParser:
        return self._legacy_config


def get_config_file(c: typing.Union[str, ConfigFile]) -> typing.Optional[ConfigFile]:
    """
    Checks if the given argument is a file or a configFile and returns a loaded configFile else returns None

    # TODO support automatic loading from Home dir .flyte/
    """
    if c is None:
        return None
    if isinstance(c, str):
        return ConfigFile(c)
    return c


def set_if_exists(d: dict, k: str, v: typing.Any) -> dict:
    """
    Given a dict `d` sets the key `k` with value of config `c`, if the config `c` is set
    It also returns the updated dictionary.

    .. note::

        The input dictionary `d` will be mutated.

    """
    if v:
        d[k] = v
    return d