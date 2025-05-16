-- Migration script to move data from the old schema to the new schema

-- Step 1: Create the users table and migrate data from players
CREATE TABLE IF NOT EXISTS users (
    id LONGINT,
    name TEXT,
    telegram_user TEXT,
    gender TEXT,
    notification INT DEFAULT 1,
    language_pack TEXT NOT NULL DEFAULT 'default',
    hidden INT DEFAULT 0,
    PRIMARY KEY(id)
);

INSERT INTO users (id, name, telegram_user, gender, notification, language_pack, hidden)
SELECT id, name, telegram_user, gender, notification, language_pack, hidden
FROM players;

-- Step 2: Drop the players table
DROP TABLE players;

-- Step 3: Modify existing tables to use user_id instead of player_id
ALTER TABLE attendance RENAME TO temp_attendance;
CREATE TABLE attendance (
    event_id LONGINT,
    user_id LONGINT,
    status INT,
    reason TEXT,
    PRIMARY KEY(event_id, user_id),
    FOREIGN KEY (event_id) REFERENCES events(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
INSERT INTO attendance (event_id, user_id, status, reason)
SELECT event_id, player_id, status, reason
FROM temp_attendance;
DROP TABLE temp_attendance;

ALTER TABLE access_control RENAME TO temp_access_control;
CREATE TABLE access_control (
    user_id LONGINT,
    control_id INT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (control_id) REFERENCES access_control_description(id)
);
INSERT INTO access_control (user_id, control_id)
SELECT player_id, control_id
FROM temp_access_control;
DROP TABLE temp_access_control;

ALTER TABLE kaypoh_messages RENAME TO temp_kaypoh_messages;
CREATE TABLE kaypoh_messages (
    user_id LONGINT,
    event_id LONGINT,
    message_id LONGINT,
    PRIMARY KEY(user_id, event_id),
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(event_id) REFERENCES events(id)
);
INSERT INTO kaypoh_messages (user_id, event_id, message_id)
SELECT player_id, event_id, message_id
FROM temp_kaypoh_messages;
DROP TABLE temp_kaypoh_messages;

-- End of migration script

