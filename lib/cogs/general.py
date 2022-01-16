from discord import Member, ChannelType, File
from discord.ext.commands import Cog
from discord.ext.commands import command, has_permissions
from table2ascii import table2ascii as t2a, PresetStyle

from ..db import db

import re
import os

path_separator = "/"
if os.name == 'nt':
    path_separator = "\\"

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
files = os.path.join(THIS_FOLDER, ".." + path_separator + "files" + path_separator + "db" + path_separator)

credit_score_mods = [143919895694802944, #Nate Keep
                    ]


class General(Cog):
    def __init__(self, bot):
    	self.bot = bot

    @command(name="updatescore", aliases=["addscore", "subtractscore"])
    async def updatescore(self, ctx, num, member: Member):
        try:
            if ctx.author.id in credit_score_mods:
                score = update_score(int(num), member)
                await ctx.send(f"{member.name}'s score is now {str(score)}!")
            else:
                await ctx.send("You must be a moderator of John Xina's army to use this command")
        except Exception as e:
            print(e)

    @command(name="scores")
    async def scores(self, ctx):
        members = ctx.guild.members
        ranked_list = []
        for member in members:
            if not member.bot:
                score = db.record(f"SELECT score, level FROM members WHERE id = {member.id}")
                if score:
                    ranked_list.append([member.name, score[0], score[1]]) #not sure why it's a tuple
                else: #add member to list if they aren't in the database for some reason
                    add_user(member.id, 1000)
                    score = db.record(f"SELECT score, level FROM members WHERE id = {member.id}")
                    ranked_list.append([member.name, score[0], score[1]]) #not sure why it's a tuple


        ranked_list = sorted(ranked_list, key=lambda item: item[1], reverse=True)
        output = t2a(
            header = ["Member", "Score", "Level"],
            body = ranked_list,
            style=PresetStyle.thin_compact
        )
        await ctx.send(f"```\n{output}\n```")

    @Cog.listener("on_message")
    async def on_message(self, message):
        if re.search("(jonah)", message.content, re.IGNORECASE):
            update_score(-5, message.author)
            await message.channel.send("Oh no, you said the bad word, -5 social credit")

    @Cog.listener()
    async def on_reaction_add(self, reaction, user):
        message = reaction.message
        # print(message.reactions)
        for item in message.reactions:
            try:
                if "rt" == item.emoji.name or "TRUE" == item.emoji.name:
                    if item.count >= 4:
                        if change_credit_for_message(5, reaction.message.author.id, message.id):
                            await reaction.message.channel.send(f"{reaction.message.author.name} gained 5 social credit!")
            except Exception as e:
                print(e)
                print("emoji added is not custom")

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("general")


def setup(bot):
	bot.add_cog(General(bot))

def add_user(id, score):
    db.execute(f"INSERT INTO members VALUES({member.id}, {score}, 3)")

def change_credit_for_message(num, user_id, message_id): #This function is used for giving credit to someone for a specific message, the message is then logged so it can't be used againt to gain credit
    message = db.record(f"SELECT 1 FROM messages WHERE id = {message_id}")
    print(message)
    if not message: #Prevents people from removing and adding messages to farm credit.
        score = (db.record(f"SELECT score FROM members WHERE id = {user_id}"))[0]
        print(score)
        score += num
        db.execute(f"UPDATE members SET score={score} WHERE id = {user_id}")
        db.execute(f"INSERT INTO messages VALUES ({message_id})")
        return True
    return False

def update_score(num, member):
    score = db.record(f"SELECT score, level FROM members WHERE id = {member.id}")[0]
    if score:
        score += num
        db.execute(f"UPDATE members SET score={score} WHERE id = {member.id}")
        return score
    else:
        add_user(member.id, 1000+num)
        return (1000+num)
