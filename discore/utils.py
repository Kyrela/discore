import string
from typing import Union, Optional

import envtoml
import addict
import i18n
from mergedeep import merge
from os import path
from dotenv import load_dotenv
import logging

__all__ = (
    'sformat',
    'config',
    'init_config',
    'setup_logging',
    'get_config',
    't'
)


class SparseFormatter(string.Formatter):
    """
    A modified string formatter that handles a sparse set of format
    args/kwargs.
    """

    # re-implemented this method for python2/3 compatibility
    def vformat(self, format_string, args, kwargs):
        used_args = set()
        result, _ = self._vformat(format_string, args, kwargs, used_args, 2)
        self.check_unused_args(used_args, args, kwargs)
        return result

    def _vformat(self, format_string, args, kwargs, used_args, recursion_depth,
                 auto_arg_index=0):
        if recursion_depth < 0:
            raise ValueError('Max string recursion exceeded')
        result = []
        for literal_text, field_name, format_spec, conversion in \
                self.parse(format_string):

            orig_field_name = field_name

            # output the literal text
            if literal_text:
                result.append(literal_text)

            # if there's a field, output it
            if field_name is not None:
                # this is some markup, find the object and do
                #  the formatting

                # handle arg indexing when empty field_names are given.
                if field_name == '':
                    if auto_arg_index is False:
                        raise ValueError('cannot switch from manual field '
                                         'specification to automatic field '
                                         'numbering')
                    field_name = str(auto_arg_index)
                    auto_arg_index += 1
                elif field_name.isdigit():
                    if auto_arg_index:
                        raise ValueError('cannot switch from manual field '
                                         'specification to automatic field '
                                         'numbering')
                    # disable auto arg incrementing, if it gets
                    # used later on, then an exception will be raised
                    auto_arg_index = False

                # given the field_name, find the object it references
                #  and the argument it came from
                try:
                    obj, arg_used = self.get_field(field_name, args, kwargs)
                except (IndexError, KeyError):
                    # catch issues with both arg indexing and kwarg key errors
                    obj = orig_field_name
                    if conversion:
                        obj += '!{}'.format(conversion)
                    if format_spec:
                        format_spec, auto_arg_index = self._vformat(
                            format_spec, args, kwargs, used_args,
                            recursion_depth, auto_arg_index=auto_arg_index)
                        obj += ':{}'.format(format_spec)
                    result.append('{' + obj + '}')
                else:
                    used_args.add(arg_used)

                    # do any conversion on the resulting object
                    obj = self.convert_field(obj, conversion)

                    # expand the format spec, if needed
                    format_spec, auto_arg_index = self._vformat(
                        format_spec, args, kwargs,
                        used_args, recursion_depth-1,
                        auto_arg_index=auto_arg_index)

                    # format the object and append to the result
                    result.append(self.format_field(obj, format_spec))

        return ''.join(result), auto_arg_index


def sformat(s, *args, **kwargs):
    """
    Sparse format a string.

    Parameters
    ----------
    s : str
    args : *Any
    kwargs : **Any

    Examples
    --------
    >>> sformat('The {} is {}', 'answer')
    'The answer is {}'

    >>> sformat('The answer to {question!r} is {answer:0.2f}', answer=42)
    'The answer to {question!r} is 42.00'

    >>> sformat('The {} to {} is {:0.{p}f}', 'answer', 'everything', p=4)
    'The answer to everything is {:0.4f}'

    Returns
    -------
    str
    """
    return SparseFormatter().format(s, *args, **kwargs)


config: addict.Dict = addict.Dict()


def _load_config_file(configuration_file: Optional[str]) -> addict.Dict:
    """
    The configuration file loader

    :param configuration_file: the path to the configuration file
    :return: the configuration as an addict.Dict
    """

    if configuration_file is None:
        return _load_config({})
    return _load_config(envtoml.load(configuration_file))


def _load_config(config: Union[dict, addict.Dict]) -> addict.Dict:
    """
    The configuration loader

    :param config: the local configuration to load
    :return: the configuration as an addict.Dict
    """

    default_config = envtoml.load(
        path.join(path.dirname(__file__), "default_config.toml"))
    return addict.Dict(merge(default_config, config))


def init_config(**kwargs):
    """
    Initialize the configuration
    """

    env_file = kwargs.pop('env_file', '.env')
    if env_file:
        load_dotenv(dotenv_path=env_file)

    global config
    if 'configuration' in kwargs:
        config = _load_config(kwargs.pop('configuration'))
    else:
        config = _load_config_file(
            kwargs.pop('configuration_file', 'config.toml'))
    return config


def get_config():
    return config


_ainsi = {
    "bg_black": "\x1b[40m",
    "bg_red": "\x1b[41m",
    "bg_green": "\x1b[42m",
    "bg_orange": "\x1b[43m",
    "bg_blue": "\x1b[44m",
    "bg_magenta": "\x1b[45m",
    "bg_cyan": "\x1b[46m",
    "bg_light_grey": "\x1b[47m",
    "bg_normal": "\x1b[49m",

    "bg_dark_grey": "\x1b[100m",
    "bg_light_red": "\x1b[101m",
    "bg_light_green": "\x1b[102m",
    "bg_yellow": "\x1b[103m",
    "bg_light_blue": "\x1b[104m",
    "bg_light_purple": "\x1b[105m",
    "bg_teal": "\x1b[106m",
    "bg_white": "\x1b[107m",

    "black": "\x1b[30m",
    "red": "\x1b[31m",
    "green": "\x1b[32m",
    "orange": "\x1b[33m",
    "blue": "\x1b[34m",
    "magenta": "\x1b[35m",
    "cyan": "\x1b[36m",
    "light_grey": "\x1b[37m",
    "normal": "\x1b[39m",

    "dark_grey": "\x1b[90m",
    "light_red": "\x1b[91m",
    "light_green": "\x1b[92m",
    "yellow": "\x1b[93m",
    "light_blue": "\x1b[94m",
    "light_purple": "\x1b[95m",
    "teal": "\x1b[96m",
    "white": "\x1b[97m",

    "bold": "\x1b[1m",
    "no_bold": "\x1b[22m",
    "faint": "\x1b[2m",
    "no_faint": "\x1b[22m",
    "italic": "\x1b[3m",
    "no_italic": "\x1b[23m",
    "underline": "\x1b[4m",
    "no_underline": "\x1b[24m",
    "blink": "\x1b[5m",
    "no_blink": "\x1b[25m",
    "reverse": "\x1b[7m",
    "no_reverse": "\x1b[27m",
    "conceal": "\x1b[8m",
    "no_conceal": "\x1b[28m",
    "crossed": "\x1b[9m",
    "no_crossed": "\x1b[29m",

    "reset": "\x1b[0m"
}


class Formatter(logging.Formatter):

    def __init__(self, color: bool = True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.color = color

        ainsi = _ainsi if color else {k: "" for k in _ainsi}

        self.formatters = {
            level: logging.Formatter(
                sformat(
                    sformat(config.log.format, levelformat=text_format),
                    **ainsi),
                config.log.date_format,
                style='{'
            )
            for level, text_format in config.log.level_format.items()
        }

    def format(self, record: logging.LogRecord) -> str:
        formatter = self.formatters.get(
            record.levelname.lower(), self.formatters['debug'])

        # Override the traceback to always print in red
        if record.exc_info and self.color:
            text = formatter.formatException(record.exc_info)
            record.exc_text = f'\x1b[31m{text}\x1b[0m'

        output = formatter.format(record)

        # Remove the cache layer
        record.exc_text = None
        return output


def setup_logging(**kwargs) -> None:
    """
    Setup the logging

    :return: None
    """
    log_level = kwargs.pop("log_level", config.log.level)
    given_formatter = kwargs.pop("formatter", None)
    stream_handler = kwargs.pop("log_handler", logging.StreamHandler())
    stream_formatter = given_formatter or Formatter()
    stream_handler.setFormatter(stream_formatter)

    handlers = [stream_handler]

    log_file = kwargs.pop("log_file", config.log.file)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_formatter = given_formatter or Formatter(color=False)
        file_handler.setFormatter(file_formatter)

        handlers.append(file_handler)

    root_logger = kwargs.pop("root_logger", config.log.root)
    if root_logger:
        loggers = (logging.getLogger(),)
    else:
        loggers = (logging.getLogger(__name__.split(".")[0]), logging.getLogger("discord"))

    for logger in loggers:
        for handler in handlers:
            logger.addHandler(handler)
        logger.setLevel(log_level)


i18n.set('filename_format', '{locale}.{format}')
i18n.set('file_format', 'yml')
i18n.set('locale', 'en-US')
i18n.set('fallback', 'en-US')
i18n.load_path.append(path.join(path.dirname(__file__), "locales"))
 if path.exists("locales") and path.isdir("locales"):
    i18n.load_path.append("locales")


def t(ctx, key, **kwargs):
    """
    Translate a key into a string
    """
    try:
        locale = ctx.guild.preferred_locale.value
    except AttributeError:
        locale = i18n.config.get("locale")
    return i18n.t(key, locale=locale, **kwargs)
