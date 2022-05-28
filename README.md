# Discore

![License](https://img.shields.io/github/license/kyrela/discore)
![Development](https://img.shields.io/badge/Development%20Status-Production%2FBeta-orange)

A core for initialise, run and tracks errors of discord.py bots, with a "Convention over configuration" philosophy

## Features

- One-line bot initialisation and one-line run
- All information stored in a configuration file
- Automatic error handling and responses
- Automatic logs storage for each command called, completed and failed
- Basic, well-designed commands such as a help command, a ping command and a restart command

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
├─ main.py
└─ config.toml
```

`main.py` code:
```python
import discore

bot = discore.Bot('config.toml') 

# Your usual commands here, or in a cog

bot.run()
```

`config.toml`:
```toml
prefix = "!"
token = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
description = "A basic test bot"
```

> Note :  all variables are optional except 'token'.

## Links

- [Github](https://github.com/Kyrela/discore)