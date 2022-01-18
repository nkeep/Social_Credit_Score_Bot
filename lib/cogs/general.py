from discord import Member, ChannelType, File
from discord.ext.commands import Cog
from discord.ext.commands import command, has_permissions
from table2ascii import table2ascii as t2a, PresetStyle
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta

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

reaction_scaling = [0,1,1,2,3,5,8,13,21,34,55,89,144,233]


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

    @command(name="ratio")
    async def ratio(self, ctx):
        try:
            if ctx.message.reference: #What the message is replying to
                if ctx.author.id != ctx.message.reference.resolved.author.id or ctx.message.reference.resolved.author.bot:
                    await ctx.message.add_reaction("✅")
                    await ctx.message.add_reaction("❌")
                    now = datetime.now()
                    # future = now + timedelta(hours=2)
                    future = now + timedelta(minutes=1)
                    print(type(future))
                    job = self.bot.scheduler.add_job(self.determine_ratio, CronTrigger(month=future.month, day=future.day, hour=future.hour, minute=future.minute), [ctx.channel, ctx.message.id], id=str(ctx.message.id))
                    #Remove any scores previously gained from these messages and set the points awarded to -1
                    message_1 = db.record(f"SELECT * FROM messages WHERE id = {ctx.message.id}")
                    if message_1:
                        print(message_1)
                        db.execute(f"UPDATE members SET score = score - {message_1[2]} WHERE id = {ctx.author.id}")
                        db.execute(f"UPDATE messages SET points_awarded = -1 WHERE id = {ctx.message.id}")
                    else:
                        db.execute(f"INSERT INTO messages VALUES ({ctx.message.id}, {ctx.author.id}, -1)")

                    message_2 = db.record(f"SELECT * FROM messages WHERE id = {ctx.message.reference.message_id}")
                    if message_2:
                        print(message_2)
                        db.execute(f"UPDATE members SET score = score - {message_2[2]} WHERE id = {ctx.message.reference.resolved.author.id}") #?????? could be wrong
                        db.execute(f"UPDATE messages SET points_awarded = -1 WHERE id = {ctx.message.reference.message_id}")
                    else:
                        db.execute(f"INSERT INTO messages VALUES ({ctx.message.reference.message_id}, {ctx.message.reference.resolved.author.id}, -1)")
                else:
                    await ctx.send("You cannot ratio yourself or a bot")

        except Exception as e:
            print(e)

    async def determine_ratio(self, channel, message_id):
        message = await channel.fetch_message(message_id)
        upvotes = 0
        downvotes = 0
        for item in message.reactions:
            if item.emoji == "✅":
                upvotes = item.count
            elif item.emoji == "❌":
                downvotes = item.count

        net = upvotes - downvotes
        print(net)
        if net > 0:
            update_score(reaction_scaling[net-1], message.author)
            update_score(-1 * reaction_scaling[net-1], message.reference.resolved.author)
            await channel.send(f"{message.author.name} ratio'd {message.reference.resolved.author.name} and gained {str(reaction_scaling[net-1])} social credit! {message.reference.resolved.author.name} lost {str(reaction_scaling[net-1])} social credit")
        elif net < 0:
            update_score(-1 * reaction_scaling[net-1], message.author)
            update_score(reaction_scaling[net-1], message.reference.resolved.author)
            await channel.send(f"{message.author.name} failed to ratio {message.reference.resolved.author.name} and lost {str(reaction_scaling[net-1])} social credit! {message.reference.resolved.author.name} gained {str(reaction_scaling[net-1])} social credit!")

        else:
            await channel.send("There was either no ratio or not a big enough ratio")

        self.bot.scheduler.remove_job(str(message.id))


    @Cog.listener("on_message")
    async def on_message(self, message):
        if re.search("(jonah)", message.content, re.IGNORECASE):
            update_score(-5, message.author)
            await message.channel.send("Oh no, you said the bad word, -5 social credit")

    @Cog.listener()
    async def on_reaction_add(self, reaction, user):
        self.bot.scheduler.print_jobs()
        if not user.bot:
            message = reaction.message
            prev_score = None

            try:
                prev_score = db.record(f"SELECT * FROM messages WHERE id = {message.id}")[2]
            except:
                pass

            if prev_score != -1: #If the score is -1, then this message is disabled (It might be part of a 'ratio' or something else)
                highest_reaction_count = 0
                for item in message.reactions: #find the highest number of rt's, true's, or tjbased's
                    try:
                        if "rt" == item.emoji.name or "TRUE" == item.emoji.name or "tjbased" == item.emoji.name:
                            if item.count > highest_reaction_count:
                                highest_reaction_count = item.count
                    except:
                        pass

                if highest_reaction_count: #Update the user's score based on the reaction_scaling table
                    if prev_score == None:
                        db.execute(f"INSERT INTO messages VALUES ({message.id}, {user.id}, {reaction_scaling[highest_reaction_count-1]})")
                    else:
                        db.execute(f"UPDATE messages SET points_awarded = {reaction_scaling[highest_reaction_count-1]} WHERE id = {message.id}")
                        db.execute(f"UPDATE members SET score = score + {reaction_scaling[highest_reaction_count-1] - prev_score} WHERE id = {user.id}")



    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("general")


def setup(bot):
	bot.add_cog(General(bot))

def add_user(id, score):
    db.execute(f"INSERT INTO members VALUES({id}, {score}, 3)")


def update_score(num, member):
    if not member.bot:
        record = db.record(f"SELECT score, level FROM members WHERE id = {member.id}")
        if record:
            db.execute(f"UPDATE members SET score= score + {num} WHERE id = {member.id}")
            return record[0]
        else:
            add_user(member.id, 1000+num)
            return (1000+num)
