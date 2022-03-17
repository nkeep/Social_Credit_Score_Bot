from discord import Member, ChannelType, File
from discord.enums import AuditLogAction
from discord.ext.commands import Cog
from discord.ext.commands import command, has_permissions
from table2ascii import table2ascii as t2a, PresetStyle
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from googletrans import Translator


from ..db import db

import math
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
good_reactions = ["rt", "TRUE", "tjbased", "LOGGERS", "TJ"]
bad_reactions = ["yaok", "yikes", "garbageTake", "papa", "dooziernotfunny"]
funny_channels = [220180534129590273]
bot_channels = [505589070378958850, 871493456021835797]
mod_channel = 938652436036460564

levels = {-1:[-math.inf,649], 0:[650,749], 1:[750,849], 2:[850,949], 3:[950,1049], 4:[1050, 1149], 5:[1150, 1249], 6:[1250,1349], 7:[1350, math.inf]}

translator = Translator()


class General(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.scheduler.add_job(self.check_weekly_messages, CronTrigger.from_crontab('0 0 * * 0')) #Every sunday at midnight

    async def check_weekly_messages(self):
        members = db.records("SELECT * FROM members")
        for member in members:
            if not member[3]: #They haven't sent a message this week
                await update_score(-5, await self.bot.fetch_user(member[0]), self.bot.get_channel(505589070378958850))

        db.execute(f"UPDATE members SET hasSentMessage = FALSE") #Set all members back to false

    @command(name="rules")
    async def rules(self, ctx):
        if ctx.channel.id in bot_channels:
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
                print(e)
        else:
            await update_score(-2, ctx.author, ctx.channel)
            await send_message(ctx.channel, "You can only use this command in the bot channel. You lost 2 social credit.")

    @command(name="addrule")
    async def add_rule(self, ctx, value, *, rule):
        if ctx.author.id in credit_score_mods:
            try:
                if value != 0 and int(value) >= -30 and int(value) <= 30:
                    rule = rule.replace("'", r"\'")
                    db.execute(f"INSERT INTO RULES(value, rule) VALUES({int(value)}, E'{rule}')")
                    await send_message(ctx.channel, "Successfully added rule")
            except Exception as e:
                await send_message(ctx.channel, "Invalid point value")
        else:
            await send_message(ctx.channel, "You must be a mod to add a rule")

    @command(name="removerule")
    async def remove_rule(self, ctx, num):
        if ctx.author.id in credit_score_mods:
            try:
                rules = db.records(f"SELECT * FROM rules WHERE value > 0") + db.records(f"SELECT * FROM rules WHERE value < 0")
                print(rules)
                rule = rules[int(num)-1][1]
                rule = rule.replace("'", r"\'")
                db.execute(f"DELETE FROM rules WHERE rule = E'{rule}'")
                await send_message(ctx.channel, "Successfully removed rule")
            except Exception as e:
                print(e)
        else:
            await send_message(ctx.channel, "You must be a mod to remove a rule")

    @command(name="togglemandarin")
    async def toggle_mandarin(self, ctx):
        try:
            if db.record(f"SELECT * FROM guilds WHERE GuildID = {ctx.guild.id}"):
                db.execute(f"UPDATE guilds SET mandarinEnabled = NOT mandarinEnabled WHERE GuildID = {ctx.guild.id}")
            else:
                db.execute(f"INSERT INTO guilds(GuildID, mandarinEnabled) VALUES({ctx.guild.id}, TRUE)")
            await send_message(ctx.channel, "Toggled Mandarin")
        except Exception as e:
            print(e)

    @command(name="scores")
    async def scores(self, ctx):
        if ctx.channel.id in bot_channels:
            members = ctx.guild.members
            ranked_list = []
            for member in members:
                if not member.bot:
                    score = db.record(f"SELECT score, level FROM members WHERE id = {member.id}")
                    if score:
                        ranked_list.append([member.name, score[0], score[1] if score[1] > -1 and score[1] < 7 else ("N" if score[1] == -1 else "S")])
                    else: #add member to list if they aren't in the database for some reason
                        add_user(member.id, 1000)
                        score = db.record(f"SELECT score, level FROM members WHERE id = {member.id}")
                        ranked_list.append([member.name, score[0], score[1]]) #not sure why it's a tuple

            ranked_list = sorted(ranked_list, key=lambda item: item[1], reverse=True)
            output = t2a(
                header = ["Member", "Score", "Tier"],
                body = ranked_list,
                style=PresetStyle.thin_compact
            )
            await ctx.send(f"```\n{output}\n```")
        else:
            await update_score(-2, ctx.author, ctx.channel)
            await send_message(ctx.channel, "You can only use this command in the bot channel. You lost 2 social credit.")

    @command(name="updatescore", aliases=["addscore", "subtractscore"])
    async def updatescore(self, ctx, num, member: Member, * , reason):
        try:
            if ctx.author.id in credit_score_mods:
                score = await update_score(int(num), member, ctx.channel)
                db.execute(f"INSERT INTO audit_log VALUES ({ctx.author.id}, {member.id}, {int(num)}, '{reason}')")
                await send_message(ctx.channel, f"{member.name}'s score is now {str(max(0,score))}!")
            else:
                await send_message(ctx.channel, "You must be a moderator of John Xina's army to use this command")
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
                    #Remove any scores previously gained from these messages and set the points awarded to NULL
                    message_1 = db.record(f"SELECT * FROM messages WHERE id = {ctx.message.id}")
                    if message_1:
                        await update_score(-1*message_1[2], ctx.message.author, ctx.channel)
                        #db.execute(f"UPDATE members SET score = score - {message_1[2]} WHERE id = {ctx.author.id}")
                        db.execute(f"UPDATE messages SET points_awarded = NULL WHERE id = {ctx.message.id}")
                    else:
                        db.execute(f"INSERT INTO messages VALUES ({ctx.message.id}, {ctx.author.id}, NULL)")

                    message_2 = db.record(f"SELECT * FROM messages WHERE id = {ctx.message.reference.message_id}")
                    if message_2:
                        await update_score(-1*message_2[2], ctx.message.reference.resolved.author, ctx.channel)
                        #db.execute(f"UPDATE members SET score = score - {message_2[2]} WHERE id = {ctx.message.reference.resolved.author.id}") #?????? could be wrong
                        db.execute(f"UPDATE messages SET points_awarded = NULL WHERE id = {ctx.message.reference.message_id}")
                    else:
                        db.execute(f"INSERT INTO messages VALUES ({ctx.message.reference.message_id}, {ctx.message.reference.resolved.author.id}, NULL)")
                else:
                    await send_message(ctx.channel, "You cannot ratio yourself or a bot")

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
            await update_score(reaction_scaling[net], message.author, channel)
            await update_score(-1 * reaction_scaling[net], message.reference.resolved.author, channel)
            await send_message(channel, f"{message.author.name} ratioed {message.reference.resolved.author.name} and gained {str(reaction_scaling[net])} social credit! {message.reference.resolved.author.name} lost {str(reaction_scaling[net])} social credit")
        elif net < -1:
            await update_score(-1 * reaction_scaling[abs(net)], message.author, channel)
            await update_score(reaction_scaling[abs(net)], message.reference.resolved.author, channel)
            await send_message(channel, f"{message.author.name} failed to ratio {message.reference.resolved.author.name} and lost {str(reaction_scaling[abs(net)])} social credit! {message.reference.resolved.author.name} gained {str(reaction_scaling[abs(net)])} social credit!")

        else:
            await send_message(channel, "There was either no ratio or not a big enough ratio")

        self.bot.scheduler.remove_job(str(message.id))

    # @Cog.listener("on_message_delete")
    # async def on_message_delete(self, message):
    #     async for entry in message.guild.audit_logs(limit=1, oldest_first=False):
    #         if "message_delete" in entry.action:
    #             if not (message.channel.id == 505589070378958850 and message.author.bot): #Only don't dock for deleting bot messages in the bot channel
    #                 print("dock points here")

    @Cog.listener("on_message")
    async def on_message(self, message):
        if not message.author.bot:
            if re.search("(jonah)", message.content, re.IGNORECASE):
                await update_score(-5, message.author, message.channel)
                await send_message(message.channel, "Oh no, you said the bad word, -5 social credit")
            if re.search("^\+funny$", message.content) and message.channel.id not in funny_channels and message.channel.id not in bot_channels:
                await update_score(-2, message.author, message.channel)
                await send_message(message.channel, "You can't use +funny in this channel. You lost 2 social credit.")
            if message.channel.id == mod_channel and message.author.id not in credit_score_mods:
                await update_score(-3, message.author, message.channel)
                await send_message(message.channel, "You must be a mod to use this channel. You lost 3 social credit.")

            db.execute(f"UPDATE members SET hasSentMessage = TRUE WHERE id = {message.author.id}")

    @Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if not user.bot:
            message = reaction.message
            prev_score = 0

            try:
                prev_score = db.record(f"SELECT * FROM messages WHERE id = {message.id}")[2]
            except:
                db.execute(f"INSERT INTO messages VALUES ({message.id}, {message.author.id}, 0)")

            if prev_score != None: #If the score is None, then this message is disabled (It might be part of a 'ratio' or something else)
                highest_pos_reaction_count = 0
                highest_neg_reaction_count = 0
                for item in message.reactions: #find the highest number of good and bad reactions
                    try:
                        if item.emoji.name in good_reactions:
                            users = await item.users().flatten()
                            ids = [x.id for x in users]
                            count = 0
                            if message.author.id in ids:
                                count = item.count -1
                            else:
                                count = item.count
                            if count > highest_pos_reaction_count:
                                highest_pos_reaction_count = count
                        elif item.emoji.name in bad_reactions:
                            users = await item.users().flatten()
                            ids = [x.id for x in users]
                            count = 0
                            if message.author.id in ids:
                                count = item.count -1
                            else:
                                count = item.count
                            if count > highest_neg_reaction_count:
                                highest_neg_reaction_count = count

                    except:
                        print("emoji not found")

                net_reaction = highest_pos_reaction_count - highest_neg_reaction_count

                if net_reaction > 0: #Update the user's score based on the reaction_scaling table
                    db.execute(f"UPDATE messages SET points_awarded = {reaction_scaling[net_reaction-1]} WHERE id = {message.id}")
                    #db.execute(f"UPDATE members SET score = score + {reaction_scaling[net_reaction-1] - prev_score} WHERE id = {message.author.id}")
                    await update_score(reaction_scaling[net_reaction-1] - prev_score, message.author, message.channel)
                elif net_reaction < 0:
                    db.execute(f"UPDATE messages SET points_awarded = {-1 * reaction_scaling[abs(net_reaction)-1]} WHERE id = {message.id}")
                    #db.execute(f"UPDATE members SET score = score + {(-1 * reaction_scaling[abs(net_reaction)-1]) - prev_score} WHERE id = {message.author.id}")
                    await update_score((-1 * reaction_scaling[abs(net_reaction)-1]) - prev_score, message.author, message.channel)
                print(net_reaction)

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("general")


def setup(bot):
	bot.add_cog(General(bot))

def add_user(id, score):
    db.execute(f"INSERT INTO members VALUES({id}, {score}, 3)")


async def update_score(num, member, channel):
    if not member.bot:
        record = db.record(f"SELECT score, level FROM members WHERE id = {member.id}")
        if record:
            db.execute(f"UPDATE members SET score= score + {num} WHERE id = {member.id}")
            score = db.record(f"SELECT score FROM members WHERE id = {member.id}")
            if score[0] < 0: #Force 0 to be the lowest score
                db.execute(f"UPDATE members SET score = 0 WHERE id = {member.id}")
            if (record[0] + num) > levels[int(record[1])][1]: #Check if the user has leveld up
                db.execute(f"UPDATE members SET level = level + 1 WHERE id = {member.id}")
                await send_message(channel, f"BING CHILLING! {member.name} has moved up to tier {str(int(record[1]) + 1)}!") #send a message for level up
            elif (record[0] + num) < levels[int(record[1])][0]:
                db.execute(f"UPDATE members SET level = level - 1 WHERE id = {member.id}")
                await send_message(channel, f"{member.name} has disrespected their famiry and moved down to tier {str(int(record[1] - 1))}.")
            return record[0] + num
        else:
            add_user(member.id, 1000+num)
            return (1000+num)


async def send_message(channel, message):
    if db.record(f"SELECT mandarinEnabled FROM guilds WHERE guildID = {channel.guild.id}")[0]:
        print(message)
        text = translator.translate(message, dest="zh-cn")
        await channel.send(text.text)
    else:
        await channel.send(message)
