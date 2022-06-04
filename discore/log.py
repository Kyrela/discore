"""
Represents the log class and all side-utilities related to the help
"""

from __future__ import annotations
import datetime
import time
import addict
from textwrap import shorten
import traceback as tb
import sys

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

    def write_error(self, err: Exception) -> None:
        # TODO: to rewrite
        """
        print the error in the console and add it to the log file, with the current timestamp

        :param err: the error to log
        :return: None
        """

        self.write(f"Error raised:", file=sys.stderr)
        tb.print_exception(type(err), err, err.__traceback__, file=sys.stderr)
        if self.config.log.file:
            with open(self.config.log.file, "a+", encoding="utf-8") as f:
                tb.print_exception(type(err), err, err.__traceback__, file=f)

    async def command_error(self, ctx: commands.Context, err: Exception) -> None:
        """
        Sends the internal command error to the raising channel and to the error channel

        :param ctx: the context of the command invocation
        :param err: the raised error
        :return: None
        """

        self.write(f"{repr(ctx.command.name)} command failed for {repr(str(ctx.author))} ({repr(ctx.author.id)}) "
                   f": {err.__class__.__name__}")
        self.write_error(err)
        error_datas = tb.extract_tb(err.__traceback__)[1]
        error_file_path = error_datas.filename.split("\\")
        public_prompt = (
            f"File {repr(error_file_path[len(error_file_path) - 1])}, "
            f"line {error_datas.lineno}, "
            f"command {repr(error_datas.name)}\n"
            f"{err.__class__.__name__} : {err}"
        )
        if ctx.guild.me.guild_permissions.manage_guild and await ctx.guild.invites():
            invite = (await ctx.guild.invites())[0].url
        elif ctx.channel.permissions_for(ctx.guild.me).create_instant_invite:
            invite = await ctx.channel.create_invite(
                reason=self.config.error.invite_message,
                max_age=86400,
                max_uses=1,
                temporary=True,
                unique=False
            )
        else:
            invite = None

        if self.config.log.channel:
            embed = discord.Embed(title="Bug raised")
            embed.set_footer(
                text=f"{self.bot.user.name}" + (f" | ver. {self.config.version}" if self.config.version else ""),
                icon_url=self.bot.user.avatar_url
            )
            embed.add_field(name="Date", value=str(datetime.datetime.today())[:-7])
            embed.add_field(name="Server", value=f"{ctx.guild.name} ({ctx.guild.id})")
            embed.add_field(name="Command", value=error_datas.name)
            embed.add_field(name="Author", value=f"{str(ctx.author)} ({ctx.author.id})")
            embed.add_field(name="File", value=error_datas.filename)
            embed.add_field(name="Line", value=str(error_datas.lineno))
            embed.add_field(name="Error", value=err.__class__.__name__)
            embed.add_field(name="Description", value=str(err))
            embed.add_field(name="Original message", value=ctx.message.content)
            embed.add_field(name="Link to message", value=ctx.message.jump_url)
            if invite:
                embed.add_field(name="Link to server", value=invite)
            await self.bot.get_channel(self.config.log.channel).send(
                "```\n" + "".join(tb.format_tb(err.__traceback__)) + "\n```", embed=embed)

        self.write(f"Error context:\n"
                   f"\tDate: {str(datetime.datetime.today())}\n"
                   f"\tServer: {ctx.guild.name} ({ctx.guild.id})\n"
                   f"\tCommand: {error_datas.name}\n"
                   f"\tAuthor: {str(ctx.author)} ({ctx.author.id})\n"
                   f"\tFile: {error_datas.filename}\n"
                   f"\tLine: {error_datas.lineno}\n"
                   f"\tError: {err.__class__.__name__}\n"
                   f"\tDescription: {str(err)}\n"
                   f"\tOriginal message: {ctx.message.content}\n"
                   f"\tLink to message: {ctx.message.jump_url}" +
                   (f"\n\tLink to server: {invite}" if invite else ""), file=sys.stderr)

        try:
            await ctx.reply(self.config.error.exception.format(public_prompt), mention_author=False)
        except discord.errors.HTTPException:
            await ctx.send(self.config.error.exception.format(public_prompt))

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
            elif not isinstance(error, commands.CommandNotFound):
                if isinstance(error, commands.CommandInvokeError):
                    error = error.original
                await self.command_error(ctx, error)

        @self.bot.event
        async def on_error(event, *args, **kwargs):
            err = sys.exc_info()[2]
            self.write_error(sys.exc_info()[1])
            self.write(f"Error context:\n\targs: {repr(args)}\n\tkargs: {repr(kwargs)}", file=sys.stderr)
            if self.config.log.channel:
                embed = discord.Embed(title="Bug raised")
                embed.set_footer(
                    text=f"{self.bot.user.name}" + (f" | ver. {self.config.version}" if self.config.version else ""),
                    icon_url=self.bot.user.avatar_url
                )
                embed.add_field(name="Date", value=str(datetime.datetime.today())[:-7])
                embed.add_field(name="Event", value=event)
                embed.add_field(name="File", value=tb.extract_tb(err)[1].filename)
                embed.add_field(name="Line", value=str(tb.extract_tb(err)[1].lineno))
                embed.add_field(name="Error", value=sys.exc_info()[0].__name__)
                embed.add_field(name="Description", value=str(sys.exc_info()[1]))
                embed.add_field(name="Arguments", value=f"{repr(args)}\n\n{repr(kwargs)}")
                await self.bot.get_channel(self.config.log.channel).send(
                    "```" + "".join(tb.format_tb(err)) + "```", embed=embed)
