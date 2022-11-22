.separator ,
.import player_profiles.csv players
DELETE FROM players WHERE telegram_id == "";
CREATE TABLE new_players (
    id LONGINT, 
    name TEXT, 
    telegram_user TEXT,
    gender TEXT, 
    notification INT, 
    PRIMARY KEY(id)
);

INSERT INTO new_players (id, name, telegram_user, gender, notification) SELECT telegram_id, names, telegram_user, gender, status FROM players;
.separator |
DROP TABLE players;
ALTER TABLE new_players RENAME TO players;
ALTER TABLE players ADD language_pack TEXT NOT NULL DEFAULT "default";
