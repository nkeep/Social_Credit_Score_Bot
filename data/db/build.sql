CREATE TABLE IF NOT EXISTS guilds (
	GuildID bigint PRIMARY KEY,
	Prefix text DEFAULT '+',
	reminderchannel bigint
);

CREATE TABLE IF NOT EXISTS members(
	id bigint PRIMARY KEY,
	score integer DEFAULT 1000,
	level integer DEFAULT 3
);

CREATE TABLE IF NOT EXISTS messages(
	id bigint PRIMARY KEY
);
