CREATE TABLE IF NOT EXISTS users(
    id LONGINT,
    name TEXT,
    telegram_user TEXT,
    gender TEXT,
    notification INT DEFAULT 1,
    language_pack TEXT NOT NULL DEFAULT "default",
    hidden INT DEFAULT 0,
    PRIMARY KEY(id)
);

INSERT INTO users SELECT * FROM players;

CREATE TABLE IF NOT EXISTS new_attendance( 
    event_id LONGINT,
    user_id LONGINT,
    status INT,
    reason TEXT,
    PRIMARY KEY(event_id, user_id), 
    FOREIGN KEY (event_id) REFERENCES events(id), 
    FOREIGN KEY (user_id) REFERENCES users(id)
);

INSERT INTO new_attendance (event_id, user_id, status, reason) 
    SELECT event_id, player_id, status, reason FROM attendance;

CREATE TABLE IF NOT EXISTS new_access_control(
    user_id LONGINT,
    control_id INT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (control_id) references access_control_description(id)
);

INSERT INTO new_access_control (user_id, control_id)
    SELECT player_id, control_id FROM access_control;
 

-- for some reason "event_id" has been mapped to  players(id)/ users(id) 
CREATE TABLE new_kaypoh_messages(
    user_id LONGINT,
    event_id LONGINT,
    message_id LONGINT,
    FOREIGN KEY(user_id) REFERENCES users(id)
    FOREIGN KEY(event_id) REFERENCES events(id)
    PRIMARY KEY(user_id, event_id)
);

INSERT INTO new_kaypoh_messages(user_id, event_id, message_id)
    SELECT player_id, event_id, message_id FROM kaypoh_messages;

CREATE TABLE new_announcement_entities(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id LONGINT,
    entity_type TEXT,
    offset INT,
    entity_length INT,
    FOREIGN KEY(event_id) REFERENCES events(id)
);

INSERT INTO new_announcement_entities(event_id, entity_type, offset, entity_length)
    SELECT event_id, entity_type, offset, entity_length FROM announcement_entities;

-- last step to change everything 

-- DROP TABLE attendance;
-- ALTER TABLE new_attendance RENAME TO attendance;
--
-- DROP TABLE players;
--
-- DROP TABLE access_control;
-- ALTER TABLE new_access_control RENAME TO access_control;
--
-- DROP TABLE kaypoh_messages;
-- ALTER TABLE kp_messages RENAME TO kaypoh_messages;
--
-- DROP TABLE announcement_entities;
-- ALTER TABLE new_announcement_entities RENAME TO announcement_entities;
