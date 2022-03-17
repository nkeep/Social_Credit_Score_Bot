from lib.bot import bot

VERSION = "1.8"

bot.run(VERSION)

#Version Notes
#1.1    Add ratio command
#1.2    Add rules commands (rules, addrule, removerule)
#1.3    Added togglemandarin command
#1.4    Add negative reactions removing score, level ranges, and weekly message checker
#1.5    restrict +funny channels, restrict channels that rules and scores commands can be used in, and make addrule and removerule mod only
#1.6    Added audit_log for update_score command
#1.7    Made it so reactions to your own messages don't count
#1.8    Made it so 0 is the lowest score you can have
