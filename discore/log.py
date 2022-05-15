"""
Represents the log class and all side-utilities related to the help
"""
from __future__ import annotations

import datetime
import time
import addict
from textwrap import shorten

import discord
from discord.ext import commands


class Log:
    """
    A class for handling a discord.py logging system
    """

    def write(self, *values: object, start: str | None = '', **kwargs) -> None:
        """
        print(value, ..., start='', sep=' ', end='\n', file=sys.stdout, flush=False)

        :param values: The elements to write in the log
        :param start: string appended before the first value, default nothing
        :param file:  a file-like object (stream); defaults to the current sys.stdout.
        :param sep:   string inserted between values, default a space.
        :param end:   string appended after the last value, default a newline.
        :param flush: whether to forcibly flush the stream.
        """

        values = ((start or '') + f"[{str(datetime.datetime.today())}]", *values)

        print(*values, **kwargs)

        if self.config.log.file:
            kwargs.pop('file', None)
            with open(self.config.log.file, "a+", encoding="utf-8") as f:
                print(*values, file=f, **kwargs)

    def __init__(self, bot: commands.Bot, config: addict.Dict):
        """
        the base constructor for the class

        :param bot: The bot on which the logs should be added
        :param config: the configuration
        """

        self.bot = bot
        self.config = config

        @self.bot.event
        async def on_connect():
            self.write(f"Connected to Discord as \"{bot.user.name}\" (id : {bot.user.id})" +
                       (f" ver. {self.config.version}" if self.config.version else ""))

        @self.bot.event
        async def on_ready():
            self.start_time = time.time()
            self.write(f"Bot loaded, ready to use (prefix '{self.config.prefix}')")

        @self.bot.event
        async def on_disconnect():
            self.write(f"Bot disconnected")

        @self.bot.event
        async def on_resumed():
            self.write(f"Bot reconnected")

        @self.bot.event
        async def on_command(ctx: commands.Context):
            self.write(
                f"{repr(ctx.command.name)} command request sent by {repr(str(ctx.author))} ({repr(ctx.author.id)})" +
                f" with invocation {repr(ctx.message.content[len(self.bot.command_prefix):])}")

        @self.bot.event
        async def on_command_completion(ctx: commands.Context):
            rep = None
            async for message in ctx.history(limit=5):
                if message.author == ctx.me and message.reference and message.reference.message_id == ctx.message.id:
                    rep = message
                    break
            message_log_infos = []
            if rep:
                message_log_infos += [" with a response"]
                if rep.content:
                    message_log_infos += [f"starting with the text "
                                          f"'{shorten(repr(rep.content)[1:-1], width=120, placeholder='...')}'"]
                for embed in rep.embeds:
                    message_log_infos += [
                        f"containing an embed with name {repr(embed.title)}, "
                        f"and with description starting with "
                        f"'{shorten(repr(embed.description)[1:-1], width=120, placeholder='...')}'"]
                for attachment in rep.attachments:
                    message_log_infos += [
                        f"containing an file with name {repr(attachment.filename)} (url {repr(attachment.url)})"]

            self.write(
                f"{repr(ctx.command.name)} command succeeded for {repr(str(ctx.author))} ({repr(ctx.author.id)})" +
                ", ".join(message_log_infos))

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
                fmt = '[%s|%s]' % (command.name, aliases)
                if parent:
                    fmt = parent + ' ' + fmt
                alias = fmt
            else:
                alias = command.name if not parent else parent + ' ' + command.name

            return '%s%s %s' % (prefix, alias, command.signature)

        @self.bot.event
        async def on_command_error(ctx, error: Exception):
            if isinstance(error, commands.ConversionError) or isinstance(error, commands.BadArgument):
                await ctx.reply(self.config.error.bad_argument.format(
                    get_command_usage(self.bot.command_prefix, ctx.command),
                    self.bot.command_prefix + "help " + ctx.command.name), mention_author=False)
                self.write(
                    f"{repr(ctx.command.name)} command failed for {repr(str(ctx.author))} ({repr(ctx.author.id)}): "
                    f"Bad arguments given")
            elif isinstance(error, commands.MissingRequiredArgument):
                await ctx.reply(self.config.error.missing_argument.format(
                    get_command_usage(self.bot.command_prefix, ctx.command),
                    self.bot.command_prefix + "help " + ctx.command.name), mention_author=False)
                self.write(
                    f"{repr(ctx.command.name)} command failed for {repr(str(ctx.author))} ({repr(ctx.author.id)}): "
                    f"Missing required argument")
            elif (isinstance(error, commands.CommandInvokeError) and isinstance(error.original, discord.Forbidden)) or \
                    isinstance(error, commands.BotMissingPermissions):
                await ctx.reply(self.config.error.bot.missing_permission, mention_author=False)
                self.write(
                    f"{repr(ctx.command.name)} command failed for {repr(str(ctx.author))} ({repr(ctx.author.id)}): "
                    f"Bot is missing permissions")
            elif isinstance(error, commands.CommandInvokeError) and isinstance(error.original, discord.NotFound):
                await ctx.reply(self.config.error.not_found, mention_author=False)
                self.write(
                    f"{repr(ctx.command.name)} command failed for {repr(str(ctx.author))} ({repr(ctx.author.id)}): "
                    f"No matches for the request")
            elif isinstance(error, commands.NotOwner) or isinstance(error, commands.NotOwner) or \
                    isinstance(error, commands.MissingPermissions):
                await ctx.reply(self.config.error.user.missing_permission, mention_author=False)
                self.write(
                    f"{repr(ctx.command.name)} command failed for {repr(str(ctx.author))} ({repr(ctx.author.id)}): "
                    f"User is missing permissions")
            else:
                await ctx.reply(self.config.error.exception, mention_author=False)
                self.write(
                    f"{repr(ctx.command.name)} command failed for {repr(str(ctx.author))} ({repr(ctx.author.id)}): "
                    f"Unknown exception")
