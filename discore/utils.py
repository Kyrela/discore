import string
from typing import Union, Optional
import envtoml
import addict
import i18n
from mergedeep import merge
from os import path
import os
from datetime import datetime
import sys
import traceback as tb
from dotenv import load_dotenv
import logging

import discord
from discord.ext import commands
from discord import app_commands

__all__ = (
    'sformat',
    'config',
    'init_config',
    'setup_logging',
    'get_config',
    't',
    'reply_with_fallback',
    'get_command_usage',
    'get_app_command_usage',
    'sanitize',
    'log_command_error',
    'log_data',
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
                        used_args, recursion_depth - 1,
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
        if 'configuration_file' in kwargs:
            config_file = kwargs.pop('configuration_file')
        elif 'DISCORE_CONFIG' in os.environ:
            config_file = os.environ['DISCORE_CONFIG']
        else:
            config_file = "config.toml"
        config = _load_config_file(config_file)
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
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
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


def t(ctx_i, key, **kwargs):
    """
    Translate a key into a string
    """
    if isinstance(ctx_i, commands.Context):
        if ctx_i.interaction:
            locale = ctx_i.interaction.locale.value
        else:
            locale = i18n.config.get("locale")
    else:
        locale = ctx_i.locale.value
    return i18n.t(key, locale=locale, **kwargs)


async def reply_with_fallback(ctx_i: Union[commands.Context, discord.Interaction], message: str):
    """
    Try to reply to a message, if it fails, send it as a normal message

    :param ctx_i: The context or interaction of the command
    :param message: The message to send
    :return: The return value of the function.
    """

    if isinstance(ctx_i, commands.Context):
        try:
            return await ctx_i.reply(message, mention_author=False)
        except discord.errors.HTTPException:
            return await ctx_i.send(message)

    if ctx_i.response.is_done():
        return await ctx_i.channel.send(message)
    await ctx_i.response.send_message(message, ephemeral=True)


def get_command_usage(prefix: str, command: commands.Command) -> str:
    """
    returns a command usage text for users

    :param prefix: the bot prefix
    :param command: the command on which the usage should be got
    :return: the command usage
    """
    parent = command.full_parent_name
    if len(command.aliases) > 0:
        aliases = '|'.join(command.aliases)
        fmt = f'[{command.name}|{aliases}]'
        if parent:
            fmt = parent + ' ' + fmt
        alias = fmt
    else:
        alias = command.name if not parent else parent + ' ' + command.name

    return f'{prefix}{alias} {command.signature}'


def get_app_command_usage(command: Union[app_commands.Command, app_commands.ContextMenu]):
    """
    returns a command usage text for users

    :param command: the command on which the usage should be got
    :return: the command usage
    """

    return (
            '/'
            + command.qualified_name
            + ' '
            + ' '.join(
        param.display_name for param
        in (command.parameters if isinstance(command, app_commands.Command) else [])))


def sanitize(text: str, limit=4000, crop_at_end: bool = True) -> str:
    """
    Sanitize a string to be displayed in Discord, and shorten it if needed

    :param text: The text to sanitize
    :param limit: The maximum length of the text
    :param crop_at_end: Whether to crop the text at the end or at the start
    """

    sanitized_text = text.replace("```", "'''")
    text_len = len(sanitized_text)
    if text_len > limit:
        if crop_at_end:
            return sanitized_text[:limit - 3] + "..."
        return "..." + sanitized_text[text_len - limit + 3:]
    return sanitized_text


async def log_command_error(
        bot: commands.Bot, ctx_i: Union[commands.Context, discord.Interaction], err: Exception,
        logger: logging.Logger = logging.getLogger(__name__)) -> None:
    """
    Sends the internal command error to the raising channel and to the
    error channel

    :param bot: the bot instance
    :param ctx_i: the context/interaction of the command
    :param err: the raised error
    :param logger: the logger to use
    :return: None
    """

    error_data = tb.extract_tb(err.__traceback__)[1]
    error_filename = path.basename(error_data.filename)
    public_prompt = (
        f"File {error_filename!r}, "
        f"line {error_data.lineno}, "
        f"command {error_data.name!r}\n"
        f"{type(err).__name__} : {err}"
    )

    await reply_with_fallback(
        ctx_i, t(ctx_i, "command_error.exception").format(public_prompt))

    user = ctx_i.author if isinstance(ctx_i, commands.Context) else ctx_i.user

    data: dict[str] = {
        "Server": f"{ctx_i.guild.name} ({ctx_i.guild.id})",
        "Command": ctx_i.command.name,
        "Author": f"{str(user)} ({user.id})",
    }
    if isinstance(ctx_i, commands.Context):
        data["Original message"] = ctx_i.message.content
        data["Link to message"] = ctx_i.message.jump_url

    if (config.log.create_invite
            and ctx_i.channel.permissions_for(ctx_i.guild.me).create_instant_invite):
        data["Invite"] = await ctx_i.channel.create_invite(
            reason=t(ctx_i, "command_error.invite_message"),
            max_age=604800,
            max_uses=1,
            temporary=True,
            unique=False)

    await log_data(
        bot,
        f"{ctx_i.command.name!r} "
        f"{'app ' if isinstance(ctx_i, discord.Interaction) or ctx_i.interaction else ''}"
        f"command failed for {str(user)!r} ({user.id!r})",
        data, logger=logger, exc_info=(type(err), err, err.__traceback__))


async def log_data(
        bot: commands.Bot, message: str, data: dict,
        logger: logging.Logger = logging.getLogger(__name__),
        level: int = logging.ERROR,
        exc_info: Union[bool, tuple] = True) -> None:
    """
    Logs data to the console and to the log channel

    :param bot: The bot instance
    :param message: The message to log
    :param data: The contextual information to log
    :param logger: The logger to use
    :param level: The level of the log
    :param exc_info: The exception information, if any
    :return: None
    """

    if exc_info is True:
        exc_info = sys.exc_info()

    traceback = message
    data["Date"] = datetime.today().strftime(config.log.date_format)

    if exc_info:
        err_type, err_value, err_traceback = exc_info
        tb_infos = tb.extract_tb(err_traceback)[1]
        unenclosed_tb = (
                "".join(tb.format_tb(err_traceback))
                + "".join(tb.format_exception_only(err_type, err_value)))

        traceback = f"```\n{sanitize(unenclosed_tb, 1992)}\n```"

        data["File"] = tb_infos.filename
        data["Line"] = tb_infos.lineno
        data["Error"] = err_type.__name__
        data["Description"] = str(err_value)

    logger.log(
        level,
        (
            message + "\n"
            + "\n".join(
                f"\t{key}: {value!r}" for key, value in data.items())
        ),
        exc_info=exc_info
    )

    if not config.log.channel:
        return

    embed = discord.Embed(title=message, color=config.color or None)
    embed.set_footer(
        text=bot.user.name + (
            f" | ver. {config.version}" if config.version else ""),
        icon_url=bot.user.display_avatar.url
    )

    for key, value in data.items():
        embed.add_field(name=key, value=value, inline=False)

    await bot.get_channel(config.log.channel).send(traceback, embed=embed)
