import os
import sys
import time

from discord.ext import commands

from .cog import Cog


__all__ = ('Utils',)


def get_proprer_delay(delay: int):
    minutes = delay // 60
    seconds = delay % 60
    hours = minutes // 60
    minutes %= 60
    days = hours // 24
    hours %= 24
    months = days // 30
    days %= 30
    years = months // 12
    months %= 12
    composed_string = []
    if years:
        composed_string.append(f"{years} years")
    if months:
        composed_string.append(f"{months} months")
    if days:
        composed_string.append(f"{days} days")
    if hours:
        composed_string.append(f"{hours} hours")
    if minutes:
        composed_string.append(f"{minutes} minutes")
    if seconds or not composed_string:
        composed_string.append(f"{seconds} seconds")
    return ", ".join(composed_string)


class Utils(Cog,
            name="utils",
            description="A collection of useful default commands"):

    @commands.command(name="ping",
                      brief="Get the bot latency",
                      description="Returns, in milliseconds, the bot's reaction time")
    async def ping(self, ctx):
        latence = round(self.bot.latency * 1000)
        await ctx.reply(f"Pong ! {latence}ms of latency registered", mention_author=False)

    @commands.command(name="uptime",
                      brief="renvoie la durée durant laquelle le bot est up",
                      description="Permet de connaitre la durée depuis laquelle le bot est opérationnel")
    @commands.is_owner()
    async def uptime(self, ctx):
        await ctx.reply(get_proprer_delay(int(time.time() - self.bot.log.start_time)), mention_author=False)

    @commands.command(name="starttime",
                      brief="Renvoie la date de démarrage",
                      description="Permet de connaître la date à laquelle le bot s'est connecté a Discord")
    @commands.is_owner()
    async def starttime(self, ctx):
        await ctx.reply(time.ctime(self.bot.log.start_time), mention_author=False)

    @commands.command(name="restart",
                      brief="Redémarre le bot",
                      description="Exécute le script du bot, ce qui coupe l'original")
    @commands.is_owner()
    async def restart(self, ctx):
        await ctx.reply(f"redémarrage en cours...", mention_author=False)
        await self.bot.close()
        self.bot.log.write("Restarting script...\n\t" + sys.executable + " \"" + "\" \"".join(sys.argv) + "\"")
        os.system(sys.executable + " \"" + "\" \"".join(sys.argv) + "\"")
        exit(0)
