.separator ,
.import player_profiles.csv players
DELETE FROM players WHERE telegram_id == "";
CREATE TABLE new_players (
    id LONGINT, 
    name TEXT, 
    gender TEXT, 
    membership_status TEXT, 
    language_pack TEXT,
    PRIMARY KEY(id)
);
INSERT INTO new_players (id, name, gender, membership_status) SELECT telegram_id, names, gender, status FROM players;
.separator |
DROP TABLE players;
ALTER TABLE new_players RENAME TO players;
