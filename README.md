# Discore

![License](https://img.shields.io/github/license/kyrela/discore)
![Development](https://img.shields.io/badge/Development%20Status-Production%2FBeta-orange)

A core for initialise, run and tracks errors of discord.py bots, with a "Convention over configuration" philosophy

## Features

- One-line bot initialisation and one-line run
- All information stored in a configuration file
- Automatic error handling and responses
- Automatic logs storage for each command called, completed and failed
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
├─ config.toml   # if name is different from it, it should be passed as an argument to the class
└─ cogs   # the name has to be 'cogs'
   ├─ cog1.py   # the cog class contained by the file should be equal to filename.title() 
   └─ cog2.py   # example : 'cog2.py' contains the cog 'Cog2'
 
```

`main.py` code:
```python
import discore
bot = discore.Bot()  # if the name of the config file is different from 'config.toml', it should be passed as an argument here. 

# Your usual commands here, or in a cog

bot.run()
```

`config.toml`:
```toml
prefix = "!"
token = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
description = "A basic test bot"
version = "1.0"
color = 0x35901E
[help]
    no_commands = "*No commands*"
    [help.meta]
        help = "Shows this message"
        usage = "[command]"
        description = "displays a list of commands"
        brief = "Shows this message"
        cog = "cog1"
    [help.bot]
        title = "Help menu"
        description = "Use `{} [command]` for more info on a command.\nYou can also use `{} [category]` for more info on a category."
        cog_title = "{} commands"
        no_category = "No category"
    [help.cog]
        title = "{} commands"
        commands = "Commands"
    [help.group]
        title = "{} group"
    [help.command]
        title = "{} command"
        not_found = "No command called `{}` found."
    [help.subcommand]
        not_found = "Command `{}` has no subcommand named `{}`"
        no_subcommand = "Command `{}` has no subcommands."
[error]
    bad_argument = "One or more arguments are incorrect.\nTry ```{}```\nFor more information on usage, send```{}```"
    missing_argument = "One or more arguments are missing.\nTry ```{}```\nFor more information on usage, send```{}```"
    not_found = "Sorry, I couldn't find anything that matched what you indicated."
    exception =  "An exceptional error has occurred. The bug has been automatically reported, please be patient. Detail of the error :```{}```"
    invite_message = "A bug has occurred. This invitation will allow, if needed, the developer to access the server, to understand why the bug occurred. This invitation is limited to one use, grants only the status of temporary member, and lasts maximum 1 day."
    [error.bot]
        missing_permission = "I do not have the necessary permissions to perform this action (role not high enough or permission not granted)"
    [error.user]
        missing_permission = "You do not have the necessary permissions to perform this action (role not high enough or permission not granted)"
[log]
    channel = 1111111111111
    file = "log.txt"
```

> Note : the log file is created if it does not exist, and all variables are optional except 'token'.
> If a variable isn't provided is provided, its value is set to the value showed in this example, except for
> `log.channel`, `log.file`, `version`, `color`, `help.meta.cog`, `help.meta.description`, `help.meta.brief` and 
> `description`, as they are set to `None`. More information on used variables below.
> You can of course store additional information in the file and access them at anytime, anywhere.
> 
`cog1.py`:
```py
import discore
class Cog1(discore.Cog, name="cog1", description="the cog containing some commands"):
    @discore.command(
        name="say",
        brief="Say something",
        description="Sends a message containing the string passed as an argument, and deletes the original message.",
        help="- <message> : The string to send"
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

## List of variables contained in the configuration file

- `prefix`: the bot's command prefix
- `token`: the token of the bot (required)
- `description`: the description of the bot, if any
- `version`: the version of the bot, if any
- `color`: the color that should be used in embeds, if any
- `help`
  - `no_commands`: the message that should appear when there is no commands in the bot, cog or group
  - `meta`
    - `cog`: the name of the cog to which the command should belong, if any. Correspond to the class name
    - `help`: the help message for the help command
    - `description`: the description of the help command
    - `usage`: the usage of the help command
    - `brief`: the short description of the help command
  - `bot`
    - `title`: the title that should appear at the top of the help message
    - `description`: the description of the help message. Can be information on his usages
    - `cog_title`: the title that should appear on top of cog sections. `{0}` is the name of the cog
    - `no_category`: the title that should appear on top of the 'No cog-related' section
  - `cog`
    - `title`: the title that should appear at the top of the help message related to a cog. `{0}` is the name of the 
      cog
    - `commands`: the of the commands section
  - `group`
    - `title`: the title that should appear at the top of the help message related to a command group. `{0}` is the
      name of the command group
  - `command`
    - `title`: the title that should appear at the top of the help message related to a command. `{0}` is the name
      of the command
    - `not_found`: the message that should appear if no command corresponding to a name is found. `{0}` is the name
      of the searched command
  - `subcommand`
    - `not_found`: the message that should appear if no subcommand of a command corresponding to a name is found.
      `{0}` is the name of the searched command, `{1}` of the searched subcommand
    - `no_subcommand`: the message that should appear if a command doesn't have any subcommand.
    `{0}` is the name of the command
- `error`
  - `bad_argument`: the message that should be sent if a command is used with the wrong arguments. `{0}` is the
    command signature, `{1}` is the help command to get help on this command
  - `missing_argument`: the message that should be sent if a command is used with not enough arguments. `{0}` is the
    command signature, `{1}` is the help command to get help on this command
  - `not_found`: the message that should be sent if a command is used with unknown arguments (ex: discord member that
    doesn't exist)
  - `exception`: the message that should be sent if a command raises an internal error. `{0}` contains the log of the
    error (with abstracted path and without full traceback)
  - `invite_message`: the message that should be used as a reason to justify the creation of an invitation to the
    server where the bug as been raised
  - `bot`
    - `missing_permission`: the message that should be sent if the bot doesn't have the necessary rights to execute
      this command
  - `user`
    - `missing_permission`: the message that should be sent if the user that called the command doesn't have the
      necessary rights to use this command
- `log`
  - `channel`: the channel where the information and errors should be logged, if any (int)
  - `file`: the file where the information and errors should be logged, if any

> Note : All format arguments are optional

## Links

- [Github](https://github.com/Kyrela/discore)