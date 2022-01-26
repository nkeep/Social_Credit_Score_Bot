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
                    144128948685504521, #Modifyed
                    143933191948992512 #Jasho
                    ]

reaction_scaling = [0,1,1,2,3,5,8,13,21,34,55,89,144,233]


class General(Cog):
    def __init__(self, bot):
    	self.bot = bot


    @command(name="rules")
    async def rules(self, ctx):
        try:
            pos_rules = db.records(f"SELECT * FROM rules WHERE value > 0")
            neg_rules = db.records(f"SELECT * FROM rules WHERE value < 0")
            text = "DOs: \n"
            for i in range(len(pos_rules)):
                text += str(i+1) + ". " + "+" + str(pos_rules[i][0]) + " " + pos_rules[i][1] + "\n"

            text += "DON'Ts: \n"

            for j in range(len(neg_rules)):
                text += str(i+2+j) + ". " + str(neg_rules[j][0]) + " " + neg_rules[j][1] + "\n"

            await ctx.send(f"```{text}```")
        except Exception as e:
            await ctx.send("Command failed")

    @command(name="addrule")
    async def add_rule(self, ctx, value, *, rule):
        try:
            if value != 0 and int(value) >= -30 and int(value) <= 30:
                rule = rule.replace("'", r"\'")
                db.execute(f"INSERT INTO RULES(value, rule) VALUES({int(value)}, E'{rule}')")
                await ctx.send("Successfully added rule")
        except Exception as e:
            await ctx.send("Invalid point value")

    @command(name="removerule")
    async def remove_rule(self, ctx, num):
        try:
            rules = db.records(f"SELECT * FROM rules WHERE value > 0") + db.records(f"SELECT * FROM rules WHERE value < 0")
            print(rules)
            rule = rules[int(num)-1][1]
            db.execute(f"DELETE FROM rules WHERE rule = '{rule}'")
            await ctx.send("Successfully removed rule")
        except Exception as e:
            await ctx.send("Failed to remove rule")

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

    @command(name="ratio")
    async def ratio(self, ctx):
        try:
            if ctx.message.reference: #What the message is replying to
                if ctx.author.id != ctx.message.reference.resolved.author.id and not ctx.message.reference.resolved.author.bot:
                    await ctx.message.add_reaction("✅")
                    await ctx.message.add_reaction("❌")
                    now = datetime.now()
                    future = now + timedelta(hours=2)
                    # future = now + timedelta(minutes=1)
                    job = self.bot.scheduler.add_job(self.determine_ratio, CronTrigger(month=future.month, day=future.day, hour=future.hour, minute=future.minute), [ctx.channel, ctx.message.id], id=str(ctx.message.id))
                    #Remove any scores previously gained from these messages and set the points awarded to -1
                    message_1 = db.record(f"SELECT * FROM messages WHERE id = {ctx.message.id}")
                    if message_1:
                        db.execute(f"UPDATE members SET score = score - {message_1[2]} WHERE id = {ctx.author.id}")
                        db.execute(f"UPDATE messages SET points_awarded = -1 WHERE id = {ctx.message.id}")
                    else:
                        db.execute(f"INSERT INTO messages VALUES ({ctx.message.id}, {ctx.author.id}, -1)")

                    message_2 = db.record(f"SELECT * FROM messages WHERE id = {ctx.message.reference.message_id}")
                    if message_2:
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
        if net > 1:
            update_score(reaction_scaling[net], message.author)
            update_score(-1 * reaction_scaling[net], message.reference.resolved.author)
            await channel.send(f"{message.author.name} ratio'd {message.reference.resolved.author.name} and gained {str(reaction_scaling[net])} social credit! {message.reference.resolved.author.name} lost {str(reaction_scaling[net])} social credit")
        elif net < -1:
            update_score(-1 * reaction_scaling[abs(net)], message.author)
            update_score(reaction_scaling[abs(net)], message.reference.resolved.author)
            await channel.send(f"{message.author.name} failed to ratio {message.reference.resolved.author.name} and lost {str(reaction_scaling[abs(net)])} social credit! {message.reference.resolved.author.name} gained {str(reaction_scaling[abs(net)])} social credit!")

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
        if not user.bot:
            message = reaction.message
            prev_score = None

            try:
                prev_score = db.record(f"SELECT * FROM messages WHERE id = {message.id}")[2]
            except:
                print("no record found")

            if prev_score != -1: #If the score is -1, then this message is disabled (It might be part of a 'ratio' or something else)
                highest_reaction_count = 0
                for item in message.reactions: #find the highest number of rt's, true's, or tjbased's
                    try:
                        if "rt" == item.emoji.name or "TRUE" == item.emoji.name or "tjbased" == item.emoji.name:
                            if item.count > highest_reaction_count:
                                highest_reaction_count = item.count
                    except:
                        print("emoji not found")

                if highest_reaction_count: #Update the user's score based on the reaction_scaling table
                    if prev_score == None:
                        db.execute(f"INSERT INTO messages VALUES ({message.id}, {message.author.id}, {reaction_scaling[highest_reaction_count-1]})")
                    else:
                        db.execute(f"UPDATE messages SET points_awarded = {reaction_scaling[highest_reaction_count-1]} WHERE id = {message.id}")
                        db.execute(f"UPDATE members SET score = score + {reaction_scaling[highest_reaction_count-1] - prev_score} WHERE id = {message.author.id}")



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
            return record[0] + num
        else:
            add_user(member.id, 1000+num)
            return (1000+num)
