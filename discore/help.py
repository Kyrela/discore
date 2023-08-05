"""
Represents the help class and all side-utilities related to the help
"""

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands.parameters import Parameter, Signature
from discord.ext.commands.core import get_signature_parameters, Command

import itertools
import copy
import functools
from typing import Any, Dict, Generator, Callable, List, Optional, Union, Iterable
from i18n import t

from .utils import config, fallback_reply, set_embed_footer


__all__ = ('EmbedHelpCommand', 'HelpHybridCommand')


# All code below belongs to InterStella0 and is licensed under the MIT license
# https://github.com/InterStella0/starlight-dpy
# Except for the class EmbedHelpCommand, which is written by me


CommandTextApp = Union[commands.Command, app_commands.Command, app_commands.Group]


def get_app_signature(command: app_commands.Command) -> str:
    """To retrieve app command signature similar to :attr:`~discord.ext.commands.Command.signature`.

    Parameters
    -----------
        command: :class:`~discord.app_commands.Command`
            App command to get signature from.

    Returns
    -------
    :class:`str`
        Parameter string that was extracted.
    """

    result = []
    for param in command.parameters:
        name = param.display_name
        if param.type is discord.AppCommandOptionType.attachment:
            # For discord.Attachment we need to signal to the user that it's an attachment
            # It's not exactly pretty but it's enough to differentiate
            if not param.required:
                result.append(f'[{name} (upload a file)]')
            else:
                result.append(f'<{name} (upload a file)>')
            continue

        # for typing.Literal[...], typing.Optional[typing.Literal[...]], and Greedy[typing.Literal[...]], the
        # parameter signature is a literal list of it's values
        if param.choices:
            name = '|'.join(f'"{v.value}"' if isinstance(v.value, str) else v.name for v in param.choices)

        if not param.required:
            # We don't want None or '' to trigger the [name=value] case and instead it should
            # do [name] since [name=None] or [name=] are not exactly useful for the user.
            if param.default is not discord.utils.MISSING and param.default not in ('', None):
                result.append(f'[{name}={param.default}]')
                continue
            else:
                result.append(f'[{name}]')
        else:
            result.append(f'<{name}>')

    return ' '.join(result)


class _InjectorCallback:
    # This class is to ensure that the help command instance gets passed properly
    # The final level of invocation will always leads back to the _original instance
    # hence bind needed to be modified before invoke is called.
    def __init__(self, original_callback, bind):
        self.callback = original_callback
        self.bind = bind

    async def invoke(self, *args, **kwargs):
        # don't put cog in command_callback
        # it used to be that i could do this in parse_arguments, but appcommand extracts __self__ directly from callback
        if self.bind.cog is not None:
            cog, *args = args

        return await self.callback.__func__(self.bind, *args, **kwargs)


def _method_partial(inject):
    # The reason this is here is
    # method cannot be modified which is required for AppCommand callback
    # Due to the shaky implementation of help command, the callback gets copied several
    # times before getting called.
    try:
        inject.__original_callback__
    except AttributeError:
        inject.__original_callback__ = _InjectorCallback(inject.command_callback, inject)

    invoker = inject.__original_callback__
    original_callback = invoker.callback

    async def invoke(*args, **kwargs):  # allows __signature__ modification
        return await invoker.invoke(*args, **kwargs)

    callback = copy.copy(invoke)
    # retrieve original signature so the user can modify if they want.
    # also good for AppCommand compatibility
    original_signature = Signature.from_callable(original_callback).parameters.values()
    callback.__signature__ = Signature.from_callable(callback).replace(parameters=original_signature)
    inject.command_callback = callback
    return callback


class _HelpHybridCommandImpl(commands.HybridCommand):
    # Most of this is copied from HelpCommandImpl with a bit modification
    def __init__(self, inject: commands.HelpCommand, *args: Any, **kwargs: Any) -> None:
        _method_partial(inject)
        super().__init__(inject.command_callback, *args, **kwargs)
        self._original: commands.HelpCommand = inject
        self._injected: commands.HelpCommand = inject
        self.params: Dict[str, Parameter] = get_signature_parameters(
            inject.__original_callback__.callback, globals(), skip_parameters=1  # type: ignore
        )

    async def prepare(self, ctx: commands.Context) -> None:
        self._injected = injected = self._original.copy()
        injected.context = ctx
        self._original.__original_callback__.bind = injected  # type: ignore
        self.params = get_signature_parameters(
            self._original.__original_callback__.callback, globals(), skip_parameters=1  # type: ignore
        )

        on_error = injected.on_help_command_error
        if not hasattr(on_error, '__help_command_not_overridden__'):
            if self.cog is not None:
                self.on_error = self._on_error_cog_implementation
            else:
                self.on_error = on_error

        await super().prepare(ctx)

    async def _on_error_cog_implementation(self, _, ctx: commands.Context, error: commands.CommandError) -> None:
        await self._injected.on_help_command_error(ctx, error)

    def _inject_into_cog(self, cog: commands.Cog) -> None:
        # Warning: hacky

        # Make the cog think that get_commands returns this command
        # as well if we inject it without modifying __cog_commands__
        # since that's used for the injection and ejection of cogs.
        def wrapped_get_commands(
                *, _original: Callable[[], List[commands.Command[Any, ..., Any]]] = cog.get_commands
        ) -> List[commands.Command[Any, ..., Any]]:
            ret = _original()
            ret.append(self)
            return ret

        # Ditto here
        def wrapped_walk_commands(
                *, _original: Callable[[], Generator[commands.Command[Any, ..., Any], None, None]] = cog.walk_commands
        ):
            yield from _original()
            yield self

        functools.update_wrapper(wrapped_get_commands, cog.get_commands)
        functools.update_wrapper(wrapped_walk_commands, cog.walk_commands)
        cog.get_commands = wrapped_get_commands
        cog.walk_commands = wrapped_walk_commands
        self.cog = cog

    def _eject_cog(self) -> None:
        if self.cog is None:
            return

        # revert back into their original methods
        cog = self.cog
        cog.get_commands = cog.get_commands.__wrapped__
        cog.walk_commands = cog.walk_commands.__wrapped__
        self.cog = None


class HelpHybridCommand(commands.HelpCommand):
    """The base class for help command with HybridCommand implementation. This should be the best way
    to make a help hybrid command.

    Generally, this would include command, hybrid command, and app command compared to the :class:`~discord.ext.commands.HelpCommand`
    class. There is helpful methods for easier integration between app command and text command.

    If you have no control of the inheritance, you should use :func:`convert_help_hybrid` instead.

    Parameters
    -----------
        with_app_command: :class:`bool`
            Whether to include app command implementation in your tree. Defaults to False. A shortcut to
            `command_attrs=dict(with_app_command)`.
        include_apps: :class:`bool`
            Whether to include app commands. Only applicable if help command is invoked with app command.
            Defaults to True.
        **options: Any
            Passed keyword arguments are sent to :class:`~discord.ext.commands.HelpCommand`.
    """
    def __init__(self, *, with_app_command: bool = False, **options: Any):
        super().__init__(**options)
        self.command_attrs['with_app_command'] = with_app_command
        self._command_impl = _HelpHybridCommandImpl(self, **self.command_attrs)
        self._command_prefix: Optional[str] = None
        self.include_apps: bool = options.pop('include_apps', True)

    async def command_callback(self, ctx: commands.Context, /, *, command: Optional[str] = None) -> None:
        """|coro|

        The actual implementation of the help hybrid command.

        It is not recommended to override this method and instead change
        the behaviour through the methods that actually get dispatched.

        - :meth:`send_bot_help`
        - :meth:`send_cog_help`
        - :meth:`send_group_help`
        - :meth:`send_command_help`
        - :meth:`get_destination`
        - :meth:`command_not_found`
        - :meth:`subcommand_not_found`
        - :meth:`send_error_message`
        - :meth:`on_help_command_error`
        - :meth:`prepare_help_command`

        """
        await self.prepare_help_command(ctx, command)

        bot = ctx.bot

        if command is None:
            mapping = self.get_bot_mapping()
            if self.include_apps:
                app_mapping = self.get_bot_app_mapping()
                for cog, app_cmds in app_mapping.items():
                    mapping.setdefault(cog, []).extend(app_cmds)

            return await self.send_bot_help(mapping)

        # Check if it's a cog
        cog = bot.get_cog(command)
        if cog is not None:
            return await self.send_cog_help(cog)

        maybe_coro = discord.utils.maybe_coroutine

        # If it's not a cog then it's a command.
        # Since we want to have detailed errors when someone
        # passes an invalid subcommand, we need to walk through
        # the command group chain ourselves.
        keys = command.split(' ')
        base_cmd = keys[0]
        cmd = bot.all_commands.get(base_cmd)
        if self.include_apps:
            guild_id = getattr(ctx.guild, "id", None)
            guild_based = guild_id in (getattr(self._command_impl.app_command, '_guild_ids', None) or [])
            if cmd is None:
                if guild_based:
                    cmd = bot.tree.get_command(base_cmd, guild=discord.Object(guild_id))

            if cmd is None:
                cmd = bot.tree.get_command(base_cmd)

        if cmd is None:
            string = await maybe_coro(self.command_not_found, self.remove_mentions(base_cmd))
            return await self.send_error_message(string)

        for key in keys[1:]:
            try:
                d = (getattr(cmd, 'all_commands', None) or cmd._children) if self.include_apps else cmd.all_commands  # type: ignore
                found = d.get(key)  # type: ignore
            except AttributeError:
                string = await maybe_coro(self.subcommand_not_found, cmd, self.remove_mentions(key))
                return await self.send_error_message(string)
            else:
                if found is None:
                    string = await maybe_coro(self.subcommand_not_found, cmd, self.remove_mentions(key))
                    return await self.send_error_message(string)
                cmd = found

        if isinstance(cmd, (commands.Group, app_commands.Group)):
            return await self.send_group_help(cmd)
        else:
            return await self.send_command_help(cmd)

    async def prepare_help_command(self, ctx: commands.Context, command: Optional[str] = None, /) -> None:
        self._command_prefix = '/' if ctx.interaction is not None else await ctx.bot.get_prefix(ctx.message)

    def get_cog(self, command: CommandTextApp, /) -> Optional[commands.Cog]:
        """Retrieves the proper cog that should be associated with the command.

        Parameters
        -----------
            command: Union[:class:`~discord.ext.commands.Command`, :class:`~discord.app_commands.Command`, :class:`~discord.app_commands.Group`]
                The command for cog retrieval

        Returns
        ---------
            Optional[:class:`~discord.ext.commands.Cog`]
                Return associate cog instance. `None` if it has no associate cog.
        """

        cog_or_group = command.cog if isinstance(command, commands.Command) else getattr(command, 'binding', None)
        if isinstance(cog_or_group, commands.Cog):
            return cog_or_group

    def get_prefix(self, command: CommandTextApp, /) -> str:
        """Retrieves the proper prefix that should be associated with the command.

        Parameters
        -----------
            command: Union[:class:`~discord.ext.commands.Command], :class:`~discord.app_commands.Command`, :class:`~discord.app_commands.Group`]
                The command for prefix retrieval.

        Returns
        ---------
            :class:`str`
                Return the proper prefix. App command should be strictly `/`.
        """
        if isinstance(command, (app_commands.Command, app_commands.Group)):
            return '/'

        ctx = self.context
        cmd_prefix = self._command_prefix if ctx.interaction is not None else ctx.clean_prefix
        return cmd_prefix

    async def filter_commands(self, commands: Iterable[CommandTextApp], /, *, sort: bool = False,
                              key: Optional[Callable[[CommandTextApp], Any]] = None,
                              ) -> List[Union[Command, app_commands.Command]]:
        """|coro|

        Returns a filtered list of commands and optionally sorts them.

        This takes into account the :attr:`verify_checks` and :attr:`show_hidden`
        attributes.

        This has support for app commands filtering for command hybrids.

        .. warning::
            `verify_checks` are not possible for app commands without slash invocation. The app command gets filtered
            when an app command have a check or interaction checks without slash invocation.

        Parameters
        ------------
        commands: Iterable[Union[:class:`~discord.ext.commands.Command`, :class:`~discord.app_commands.Command`, :class:`~discord.app_commands.Group`]]
            An iterable of commands that are getting filtered.
        sort: :class:`bool`
            Whether to sort the result.
        key: Optional[Callable[[Union[:class:`~discord.ext.commands.Command`, :class:`~discord.app_commands.Command`, :class:`~discord.app_commands.Group`]], Any]]
            An optional key function to pass to :func:`py:sorted` that
            takes a Union[:class:`~discord.ext.commands.Command`, :class:`~discord.app_commands.Command`, :class:`~discord.app_commands.Group`] as its sole parameter. If ``sort`` is passed as ``True`` then this
            will default as the command name.

        Returns
        ---------
        List[Union[:class:`~discord.ext.commands.Command`, :class:`~discord.app_commands.Command`]
            A list of commands that passed the filter.
        """

        if sort and key is None:
            key = lambda c: c.name

        iterator = commands if self.show_hidden else filter(lambda c: not getattr(c, 'hidden', None), commands)

        if self.verify_checks is False:
            # if we do not need to verify the checks then we can just
            # run it straight through normally without using await.
            return sorted(iterator, key=key) if sort else list(iterator)  # type: ignore # the key shouldn't be None

        if self.verify_checks is None and not self.context.guild:
            # if verify_checks is None and we're in a DM, don't verify
            return sorted(iterator, key=key) if sort else list(iterator)  # type: ignore

        # if we're here then we need to check every command if it can run
        async def predicate(cmd: Union[Command[Any, ..., Any], app_commands.Command]) -> bool:
            ctx = self.context
            if isinstance(cmd, Command):
                try:
                    return await cmd.can_run(ctx)
                except discord.ext.commands.CommandError:
                    return False

            no_interaction = ctx.interaction is None
            if not cmd.checks and no_interaction:
                binding = cmd.binding
                if cmd.parent is not None and cmd.parent is not binding:
                    return False  # it has group command interaction check

                if binding is not None:
                    check = getattr(binding, 'interaction_check', None)
                    if check:
                        return False  # it has cog interaction check

                return True

            if no_interaction:
                return False

            try:
                return await cmd._check_can_run(ctx.interaction)
            except app_commands.AppCommandError:
                return False

        ret = []
        for cmd in iterator:
            valid = await predicate(cmd)
            if valid:
                ret.append(cmd)

        if sort:
            ret.sort(key=key)
        return ret

    def get_command_signature(self, command: CommandTextApp, /) -> str:
        """Implementation signature that is compatible with `~discord.app_commands.Command`.

        Parameters
        ------------
            command: Union[:class:`~discord.ext.commands.Command`, :class:`~discord.app_commands.Command`, :class:`~discord.app_commands.Group`]
                Command to get the signature from.

        Returns
        --------
            :class:`str`
                The command signature in str form.
        """
        signature = ' '
        if isinstance(command, commands.Command):
            signature += command.signature
        elif isinstance(command, app_commands.Group):
            signature = ''
        else:
            signature += get_app_signature(command)

        return f'{self.get_prefix(command)}{command.qualified_name}{signature}'

    def get_command_description(self, command: CommandTextApp, /, *, brief: bool = False
                                ) -> Optional[str]:
        """Helper method to resolve command description from a given command.

        Parameters
        ------------
            command: Union[:class:`~discord.ext.commands.Command`, :class:`~discord.app_commands.Command`, :class:`~discord.app_commands.Group`]
                Command to get the documentation from.

            brief: :class:`bool`
                Indicates whether to get the short documentation or long documentation for
                :class:`~discord.ext.commands.Command`, :class:`~discord.app_commands.Command`, and
                :class:`~discord.app_commands.Group`. Defaults to False.

        Returns
        --------
            Optional[:class:`str`]
                An str that describes the command.
        """
        if isinstance(command, (app_commands.Command, app_commands.Group)):
            return command.description

        if brief:
            return command.short_doc

        return command.help

    def get_bot_app_mapping(self) -> Dict[Optional[commands.Cog], List[Union[app_commands.Command, app_commands.Group]]]:
        """Retrieves the app command bot mapping.

        Returns
        --------
            Dict[Optional[:class:`~discord.ext.commands.Cog`], List[:class:`~discord.app_commands.Command`]]
                A mapping of cog with app commands associated with it.
        """
        ctx = self.context
        bot = ctx.bot
        mapping = {}

        for cog in bot.cogs.values():
            cmds = cog.get_app_commands() if not isinstance(cog, commands.GroupCog) else cog.app_command.commands
            mapping.setdefault(cog, []).extend(cmds)

        def get_cmds(with_guild=None):
            return [c for c in bot.tree.get_commands(guild=with_guild)
                    if isinstance(c, app_commands.Command) and c.binding is None]

        guild = ctx.guild
        mapping[None] = []
        if guild is not None:
            mapping[None].extend(get_cmds(guild))

        mapping[None].extend(get_cmds())

        return mapping

    def get_destination(self) -> discord.abc.Messageable:
        # Well behave help command should use this method as a sender
        destination = super().get_destination()
        ctx = self.context
        if getattr(destination, "id", None) == ctx.channel.id:  # there is a chance destination does not have an id.
            return ctx

        return destination

    def _add_to_bot(self, bot: commands.bot.BotBase) -> None:
        command = _HelpHybridCommandImpl(self, **self.command_attrs)
        self._command_impl = command
        bot.add_command(command)

    def _remove_from_bot(self, bot: commands.bot.BotBase) -> None:
        impl = self._command_impl
        bot.remove_command(impl.name)
        app = impl.app_command
        for snowflake in app._guild_ids or []:
            bot.tree.remove_command(app.name, guild=discord.Object(snowflake))
        impl._eject_cog()


class EmbedHelpCommand(HelpHybridCommand):
    """
    represents a discord.py help system
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("with_app_command", True)
        super().__init__(**kwargs)

    async def send_bot_help(self, mapping):
        """
        send the main help message

        :param mapping: contains unused informations
        :return: None
        """

        ctx = self.context
        bot = ctx.bot

        def get_category(command):
            cog = command.cog
            return cog.qualified_name if cog is not None else t("help.bot.no_category")

        filtered = await self.filter_commands(bot.commands, sort=True, key=get_category)
        to_iterate = itertools.groupby(filtered, key=get_category)

        e = discord.Embed(
            title=t("help.bot.title"),
            description=(
                ((bot.description + "\n\n") if bot.description else "") +
                t("help.bot.description", help_command=self.context.clean_prefix + self.invoked_with))
        )

        for category, commands in to_iterate:
            e.add_field(
                name=category,
                value=("`" + "`, `".join(elem.name for elem in commands) + "`")
                if commands else t("help.no_commands"),
                inline=False
            )

        set_embed_footer(self.context.bot, e)
        await fallback_reply(ctx, embed=e)

    async def send_cog_help(self, cog):
        """
        send the cog help message

        :param cog: the cog on which the help is called
        :return: None
        """

        ctx = self.context

        filtered = await self.filter_commands(cog.get_commands())

        e = discord.Embed(
            title=t("help.cog.title", cog=cog.qualified_name),
            description=cog.description
        )

        e.add_field(
            name=t("help.cog.commands"),
            value=("`" + "`, `".join(elem.name for elem in filtered) + "`")
            if filtered else t("help.no_commands"),
            inline=False
        )

        set_embed_footer(self.context.bot, e)
        await fallback_reply(ctx, embed=e)

    async def send_command_help(self, command: commands.Command):
        """
        Send the command help message

        :param command: the command on which the help is called
        :return: None
        """

        ctx = self.context

        e = discord.Embed(
            title=t("help.command.title", command=command.name),
            description=(
                    (command.description + "\n\n" if command.description else "") +
                    f"```{self.get_command_signature(command)}```" +
                    ("\n" + command.help if command.help else "")
            )
        )

        set_embed_footer(self.context.bot, e)
        await fallback_reply(ctx, embed=e)

    async def send_group_help(self, group: commands.Group):
        """
        Send the command group help message

        :param group: the group on which the help is called
        :return: None
        """

        ctx = self.context

        filtered = await self.filter_commands(group.commands)

        e = discord.Embed(
            title=group.qualified_name,
            description=group.description
        )

        e.add_field(
            name=t("help.group.title", group=group.qualified_name),
            value=("`" + "`, `".join(elem.name for elem in filtered) + "`")
            if filtered else t("help.no_commands"),
            inline=False
        )

        set_embed_footer(self.context.bot, e)
        await fallback_reply(ctx, embed=e)

    async def command_not_found(self, command_name):
        """
        Return a message error when no corresponding command is found

        :param command_name: the called unknown command, cog or group
        :return: the message to send
        """

        return t("help.command.not_found", command=command_name)

    async def subcommand_not_found(self, command, subcommand_name):
        """
        Return a message error when no corresponding subcommand is found

        :param command: the base command
        :param subcommand_name: the unknown subcommand
        :return: the message to send
        """

        ctx = self.context

        if isinstance(command, commands.Group) and len(command.all_commands) > 0:
            return t("help.subcommand.not_found", command=command.qualified_name, subcommand=subcommand_name)
        return t("help.subcommand.no_subcommand", command=command.qualified_name)

    async def send_error_message(self, error: commands.CommandError):
        """
        Send the error message

        :param error: the error to send
        :return: None
        """

        e = discord.Embed(
            title=t("help.bot.title"),
            description=error
        )

        set_embed_footer(self.context.bot, e)
        await fallback_reply(self.context, embed=e)
