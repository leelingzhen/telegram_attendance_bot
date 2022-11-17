.open attendance.db

.separator ,
.import player_profiles.csv players
DELETE FROM players WHERE telegram_id == "";
CREATE TABLE new_players (
    id LONGINT, 
    name TEXT, 
    telegram_user TEXT,
    gender TEXT, 
    notification INT DEFAULT 1, 
    language_pack TEXT NOT NULL DEFAULT "default",
    PRIMARY KEY(id)
);

INSERT INTO new_players (id, name, telegram_user, gender, notification) SELECT telegram_id, names, telegram_user, gender, status FROM players;

DROP TABLE players;
ALTER TABLE new_players RENAME TO players;

CREATE TABLE IF NOT EXISTS players(
    id LONGINT,
    name TEXT, 
    gender TEXT, 
    notification INT, 
    language_pack INT, 
    PRIMARY KEY(id)
);
CREATE TABLE events(
    id LONGINT, 
    event_type TEXT, 
    event_date DATE, 
    start_time TIME, 
    end_time TIME DEFAULT '00:00', 
    location TEXT,
    announcement TEXT, 
    access_control DEFAULT 2,
    PRIMARY KEY(id)
);
CREATE TABLE attendance(
    event_id LONGINT, 
    player_id LONGINT, 
    status INT, 
    reason TEXT, 
    FOREIGN KEY(event_id) REFERENCES events(id), 
    FOREIGN KEY(player_id) REFERENCES players(id)
);

.import access_control.csv old_access_control

CREATE TABLE access_control(
    player_id LONGINT,
    control_id INT, 
    FOREIGN KEY (player_id) REFERENCES players(id),
    FOREIGN KEY (control_id) references access_control_description(id)
);

INSERT INTO access_control(player_id, control_id)
SELECT player_id, control_id FROM old_access_control;

DROP TABLE old_access_control;

CREATE TABLE access_control_description(
    id INT,
    description TEXT,
    PRIMARY KEY (id)
);

INSERT INTO access_control_description VALUES (0, 'Public');
INSERT INTO access_control_description VALUES (1, 'Pending Registration approval');
INSERT INTO access_control_description VALUES (2, 'Guest');
INSERT INTO access_control_description VALUES (3, 'Pending Membership approval');
INSERT INTO access_control_description VALUES (4, 'Member');
INSERT INTO access_control_description VALUES (5, 'Core');
INSERT INTO access_control_description VALUES (6, 'Admin');
INSERT INTO access_control_description VALUES (7, 'Super User');

CREATE TABLE gym_exercises(
    id INT,
    routine TEXT
);
CREATE TABLE gym_tracker(
    player_id LONGINT,
    routine_id LONGINT,
    completions INT
);

CREATE TABLE announcement_entities(
    event_id LONGINT,
    entity_type TEXT,
    offset INT,
    entity_length INT,
    FOREIGN KEY(event_id) REFERENCES events(id)
);
.separator |
