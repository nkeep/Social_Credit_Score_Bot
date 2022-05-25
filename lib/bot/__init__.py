from asyncio import sleep
from datetime import datetime
from glob import glob
from random import randint

from discord import Intents, ClientUser
from discord.ext.commands import Bot as BotBase
from discord.ext.commands import CommandNotFound, BadArgument, MissingRequiredArgument
from discord.ext.commands import when_mentioned_or, command, has_permissions
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import os
import discord

from ..db import db
from ..groups import sc as slashsc


from config import token, default_prefix, path_separator

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
cogs = os.path.join(THIS_FOLDER, ".." + path_separator + "cogs" + path_separator + "*.py")
print(cogs)
OWNER_IDS = [143919895694802944]
COGS = [path.split(path_separator)[-1][:-3] for path in glob(cogs)]
print(COGS)
IGNORE_EXCEPTIONS = (CommandNotFound, BadArgument)


def get_prefix(bot, message):
    prefix=""
    try:
        prefix = db.field(f"SELECT Prefix FROM guilds WHERE GuildID = {message.guild.id}")
    except:
        prefix = default_prefix
    if not prefix:
        prefix = default_prefix
    print(prefix)
    return when_mentioned_or(prefix)(bot, message)

class Ready(object):
    def __init__(self):
        for cog in COGS:
            setattr(self, cog, False)

    def ready_up(self, cog):
        setattr(self, cog, True)
        print(f"{cog} cog ready")

    def all_ready(self):
        return all([getattr(self, cog) for cog in COGS])

class Bot(BotBase):
    def __init__(self):
        self.ready = False
        self.cogs_ready = Ready()
        self.guild = None
        self.scheduler = AsyncIOScheduler()

        db.autosave(self.scheduler)

        super().__init__(
        command_prefix=get_prefix,
        ownder_ids = OWNER_IDS,
        intents=Intents.all(),
        )

    async def setup(self):
        print(COGS)
        for cog in COGS:
            await self.load_extension(f"lib.cogs.{cog}")
            print(f"{cog} cog loaded")
        print("setup complete")

        self.tree.add_command(slashsc.sc(self), guild=discord.Object(id=533019434491576323))
        self.tree.add_command(slashsc.sc(self), guild=discord.Object(id=220180151315595264))

        await self.tree.sync(guild=discord.Object(id=533019434491576323))
        await self.tree.sync(guild=discord.Object(id=220180151315595264))

    def run(self, version):
        self.VERSION = version


        self.TOKEN = token

        print("running bot...")
        super().run(self.TOKEN, reconnect=True)

    async def print_message(self):
        pass

    async def on_connect(self):
        print("running setup")
        await self.setup()
        print("bot connected")

    async def on_disconnect(self):
        print("bot disconnected")

    async def on_error(self, err, *args, **kwargs):
        if err == "on_command_error":
            await args[0].send("Something went wrong.")

        raise

    async def on_command_error(self, ctx, exc):

        if any([isinstance(exc, error) for error in IGNORE_EXCEPTIONS]):

            pass

        elif isinstance(exc, CommandNotFound):
            await ctx.send("Hey pal, you just blow in from stupid town?")
            #pass

        elif isinstance(exc, BadArgument):
            pass
        elif isinstance(exc, MissingRequiredArgument):
            await ctx.send("One or more required arguments are missing.")
        elif isinstance(exc.original, HTTPException):
            await ctx.send("Unable to send message")
        elif isinstance(exc.original, Forbidden):
            await ctx.send("I do not have permission to do that")
        else:
            raise exc

    async def on_ready(self):
        if not self.ready:

            self.scheduler.start()
            #self.guild = self.get_guild()

            while not self.cogs_ready.all_ready():
                await sleep(0.5)

            self.ready = True
            print("bot ready")
        else:
            print("bot reconnected")

    async def on_message(self, message):
        if not message.author.bot: #ignores other bots
            if not message.author.id == 143865454212022272 and not message.author.id == 144630299353939968:
                await self.process_commands(message)

    async def on_guild_join(self, guild): #Add all members to the guild on guild join
        for member in guild.members:
            user = db.field(f"SELECT 1 FROM members WHERE id={member.id}")
            if not user and not member.bot:
                db.execute(f"INSERT INTO members VALUES({member.id}, 1000, 3)")

            # db.execute(f"UPDATE guilds SET members = array_append(members, {member.id}) WHERE GuildID = {guild.id}") #Append each user to the array

    async def on_member_join(member):
        user = db.field(f"SELECT 1 FROM members WHERE id={member.id}")
        if not user and not member.bot:
            db.execute(f"INSERT INTO members VALUES({member.id}, 1000, 3)")


bot = Bot()
