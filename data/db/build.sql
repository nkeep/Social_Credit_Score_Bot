CREATE TABLE IF NOT EXISTS guilds (
	GuildID bigint PRIMARY KEY,
	Prefix text DEFAULT '$',
	mandarinEnabled boolean DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS members(
	id bigint PRIMARY KEY,
	score integer DEFAULT 1000,
	level integer DEFAULT 3,
	hasSentMessage boolean DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS messages(
	id bigint PRIMARY KEY,
	user_id bigint,
	points_awarded int
);

CREATE TABLE IF NOT EXISTS rules(
	value int,
	rule text PRIMARY KEY
);
