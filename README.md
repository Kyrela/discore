# Discore

![License](https://img.shields.io/github/license/kyrela/discore)
![Development](https://img.shields.io/badge/Development%20Status-Beta-orange)

A core for initialise, run and tracks errors of discord.py bots, with a "Convention over configuration" philosophy

## Features

- One-line bot initialisation and one-line run
- better default help hybrid command
- All information stored in a configuration file
- Automatic error handling and responses
- Automatic logs storage for each command called, completed and failed
- localisation automatic detection and support
- Multiple environment support
- Backwards compatibility with discord.py

## Installation

**Python 3.6 or above is required**

Just run the following command
```bash
pip install git+https://github.com/Kyrela/discore
```

## Usage example

project architecture
```
project
├─ main.py   # name can be anything
├─ config.yml   # if name is different from it, it should be passed as an argument to the class
├─ cogs   # the name has to be 'cogs'
│  ├─ cog1.py   # the cog class contained by the file should be equal to filename.title() 
│  └─ cog2.py   # example : 'cog2.py' contains the cog 'Cog2'
└─ locales   # the name has to be 'locales'
   ├─ en-US.yml   # the locale file should be named with the language code
   └─ fr.yml   # example : 'fr.yml' contains the locale for french
```

`main.py` code:
```python
import discore
bot = discore.Bot()  # if the name of the config file is different from 'config.toml', it should be passed as an argument here. 

# Your usual commands here, or in a cog

bot.run()
```

`config.yml`:
```yaml
prefix: "!"
token: "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
description: "A basic test bot"
version: "1.0"
color: 0x35901E
hot_reload: true
case_insensitive: true
locale: "en-US"

help:
    cog: "system"
    name: "help"
    help: "Shows this message"
    description: "Shows help about the bot, a command, or a category"
    usage: "[command | category]"
    brief: "Shows help about the bot"
    aliases: ["h", "hp"]
    cooldown: null
    enabled: true
    hidden: false

log:
    channel: 1111111111111
    file: "log.txt"
    level: "INFO"
    root: true
    stream_to_err: true
    format: "[{asctime}] {levelformat} {name}: {message}"
    date_format: "%d/%m/%Y %H:%M:%S"
    create_invite: true
    level_format:
        debug: "[{bg_black}{bold}DEBUG{no_bold}{bg_normal}]   "
        info: "[{blue}{bold}INFO{no_bold}{normal}]    "
        warning: "[{yellow}{bold}WARNING{no_bold}{normal}] "
        error: "[{red}ERROR{normal}]   "
        critical: "[{bg_red}CRITICAL{bg_normal}]"
```

> Note : the log file is created if it does not exist, and all variables are optional except 'token'.
> If a variable isn't provided, its value is set to the value showed in this example, except for
> `log.channel`, `log.file`, `version`, `color` and `description`, `help.*`, as they are
> set to `None`. More information on used variables below.
> You can of course store additional information in the file and access them at anytime, anywhere.

`cog1.py`:
```py
import discore
class Cog1(discore.Cog, name="cog1", description="the cog containing some commands"):
    @discore.command(
        name="say",
        brief="Say something",
        description="Sends a message containing the string passed as an argument, and deletes the original message.",
        help="- `message` : The string to send"
    )
    async def say(self, ctx, *, message: str):
        await ctx.message.delete()
        await ctx.send(message)
    
    @discore.command(
      name="ping",
      brief="check if the bot is online",
      description="Responds with a simple message, useful to see if the bot is online"
    )
    async def ping(self, ctx):
      await ctx.message.reply("Pong!")
```

`en-US.yml`:
```yaml
help:
  no_commands: "*No commands*"
  bot:
    title: "Help menu"
    description: "Use `%{help_command} [command]` for more info on a command.\nYou can also use `%{help_command} [category]` for more info on a category."
    no_category: "No category"
  cog:
    title: "%{cog} commands"
    commands: "Commands"
  group:
    title: "%{group} group"
  command:
    title: "%{command} command"
    not_found: "No command called `%{command}` found."
  subcommand:
    not_found: "Command `%{command}` has no subcommand named `%{subcommand}`"
    no_subcommand: "Command `%{command}` has no subcommands."

command_error:
  bad_argument: "One or more arguments are incorrect.\nTry \n```\n%{command_usage}\n```\nFor more information on usage, send\n```\n%{help_command}\n```"
  missing_argument: "One or more arguments are missing.\nTry \n```\n%{command_usage}\n```\nFor more information on usage, send\n```\n%{help_command}\n```"
  not_found: "Sorry, I couldn't find anything that matched what you indicated."
  exception: "An exceptional error has occurred. The bug has been automatically reported, please be patient. Detail of the error :```\nFile '%{file}', line '%{line}', command '%{command}'\n%{error}: %{error_message}\n```"
  invite_message: "A bug has occurred. This invitation will allow, if needed, the developer to access the server, to understand why the bug occurred. This invitation is limited to one use, grants only the status of temporary member, and lasts maximum 1 day."
  on_cooldown: "This command is on cooldown. Try again %{cooldown_time}."
  invalid_quoted_string: "Sorry, but I couldn't correctly process the arguments. Maybe you forgot to put a space after a closing quote ?"
  bot_missing_permission: "I do not have the necessary permissions to perform this action (role not high enough or permission not granted)"
  user_missing_permission: "You do not have the necessary permissions to perform this action (role not high enough or permission not granted)"
  private_message_only: "This command can only be used in private messages."
  no_private_message: "This command cannot be used in private messages."

app_error:
  transformer: "The argument `%{argument_value}` is incorrect.\nTry \n```\n%{command_usage}\n```\nFor more information on usage, send\n```\n%{help_command}\n```"
  no_private_message: "This command cannot be used in private messages."
  missing_role: "You need the role `%{role}` to use this command."
  missing_any_role: "You need one of the following roles to use this command: `%{roles_list}`."
  missing_permissions: "You need the following permissions to use this command: `%{permissions_list}`."
  bot_missing_permissions: "I need the following permissions to use this command: `%{permissions_list}`."
  on_cooldown: "This command is on cooldown. Try again %{cooldown_time}."
  command_not_found: "Command not found, please refresh your discord client."
```

> The localisations provided here are the default one, and are used if they're not provided in the locale file.

## List of variables contained in the configuration file

- `prefix`: the bot's command prefix
- `token`: the token of the bot (required)
- `description`: the description of the bot, if any
- `version`: the version of the bot, if any
- `color`: the color that should be used in embeds, if any
- `help_cog`: the name of the cog containing the help command. If not provided, no cog will be assigned.
- `hot_reload`: whether or not the bot should reload the cogs when they are modified. Also describe if 
  localisations should be loaded from memory or from the disk.
- `case_insensitive`: whether the prefix and the commands should be case insensitive (e.g. `!ping` and `!PING` are
  equivalent)
- `locale`: The default locale of the bot, if none is found at the command's call
- `help` : the help command's configuration - below configuration is a non-exhaustive list of the available options 
  (passed as kwargs to the `HelpCommand` constructor)
  - `cog`: the name of the cog to which the command should belong, if any. Correspond to the class name
  - `name`: the name of the help command
  - `help`: the help message for the help command
  - `description`: the description of the help command
  - `usage`: the usage of the help command
  - `brief`: the short description of the help command
  - `aliases`: the aliases of the help command
  - `cooldown`: the cooldown of the help command
  - `enabled`: whether the help command should be enabled
  - `hidden`: whether the help command should be hidden
- `log`
  - `channel`: the channel where the information and errors should be logged, if any (int)
  - `file`: the file where the information and errors should be logged, if any
  - `level`: the level of logs to be displayed in the console. Can be one of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
  - `root`: whether the whole hierarchy of the bot should be logged
  - `stream_to_err`: whether the logs should be streamed to the error stream (stderr) or the output stream (stdout)
  - `format`: the format of the logs. The following variables can (but don't have to) be used:
    - `{asctime}`: the date and time of the log
    - `{name}`: the name of the logger
    - `{levelname}`: the level of the log
    - `{message}`: the message of the log
    - `{levelformat}`: the level of the log, formatted according to the `level_format` variable
  - `date_format`: the format of the date and time of the log
  - `create_invite`: whether or not an invite should be created when an error occurs
  - `level_format`:
    - `debug`: the format of the debug level
    - `info`: the format of the info level
    - `warning`: the format of the warning level
    - `error`: the format of the error level
    - `critical`: the format of the critical level

## List of localisation variables

- `help`
  - `no_commands`: the message that should appear when there is no commands in the bot, cog or group
  - `bot`
    - `title`: the title that should appear at the top of the help message
    - `description`: the description of the help message. Can be information on his usages.  `%{help_command}` is
      the invocation of the help command
    - `no_category`: the title that should appear on top of the 'No cog-related' section
  - `cog`
    - `title`: the title that should appear at the top of the help message related to a cog. `%{cog}` is the name of the
      cog
    - `commands`: the of the commands section
  - `group`
    - `title`: the title that should appear at the top of the help message related to a command group. `%{group}` is the
      name of the command group
  - `command`
    - `title`: the title that should appear at the top of the help message related to a command. `%{command}` is the
      name of the command
    - `not_found`: the message that should appear if no command corresponding to a name is found. `%{command}` is the
      name of the searched command
  - `subcommand`
    - `not_found`: the message that should appear if no subcommand of a command corresponding to a name is found.
      `%{command}` is the name of the searched command, `%{subcommand}` of the searched subcommand
    - `no_subcommand`: the message that should appear if a command doesn't have any subcommand. `%{command}` is the name
      of the command
- `command_error`
  - `bad_argument`: the message that should be sent if a command is used with the wrong arguments. `%{command_usage}` is
    the command signature, `%{help_command}` is the help command to get help on this command
  - `missing_argument`: the message that should be sent if a command is used with not enough arguments.
    `%{command_usage}` is the command signature, `%{help_command}` is the help command to get help on this command
  - `not_found`: the message that should be sent if a command is used with unknown arguments (ex: discord member that
    doesn't exist)
  - `exception`: the message that should be sent if a command raises an internal error. `%{file}` is the file where the
    error has been raised, `%{line}` is the line where the error has been raised, `%{command}` is the name of the
    command, `%{error}` is the error type, `%{error_message}` is the error message
  - `invite_message`: the message that should be used as a reason to justify the creation of an invitation to the
    server where the bug as been raised
  - `on_cooldown`: the message that should be sent if a command is used while it is on cooldown. `%{cooldown_time}` is
    the cooldown duration in seconds
  - `invalid_quoted_string`: the message that should be sent if a quoted string is badly or not closed
  - `bot_missing_permission`: the message that should be sent if the bot doesn't have the necessary rights to execute
    this command
  - `user_missing_permission`: the message that should be sent if the user that called the command doesn't have the
    necessary rights to use this command
- `app_error`
  - `transformer`: the message that should be sent if a transformer raises an error. `%{argument_value}` is the value
    that has been passed to the transformer, `%{command_usage}` is the command signature, `%{help_command}` is the help
    of the command
  - `no_private_message`: the message that should be sent if a command is used in a private message and can't be used
    in this context
  - `missing_role`: the message that should be sent if a command is used by a user that doesn't have the necessary
    role to use this command. `%{role}` is the name of the role
  - `missing_any_role`: the message that should be sent if a command is used by a user that doesn't have any of the
    necessary roles to use this command. `%{roles_list}` is the list of the roles
  - `missing_permissions`: the message that should be sent if a command is used by a user that doesn't have the
    necessary permissions to use this command. `%{permissions_list}` is the list of the permissions
  - `bot_missing_permissions`: the message that should be sent if the bot doesn't have the necessary permissions to
    execute this command. `%{permissions_list}` is the list of the permissions
  - `cooldown`: the message that should be sent if a command is used while it is on cooldown. `%{cooldown_time}` is
    the cooldown duration in seconds
  - `command_not_found`: the message that should be sent if a command doesn't exist but is still cached and called by a
    discord client


## Links

- [Github](https://github.com/Kyrela/discore)
