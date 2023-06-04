-- ALTER TABLE players ADD hidden INT DEFAULT 0;
-- UPDATE access_control_description SET description = 'Team Manager' WHERE id = 7;
-- INSERT INTO access_control_description VALUES (100, 'Super User');
-- UPDATE access_control SET control_id = 100 WHERE player_id = '89637568'


CREATE TABLE kaypoh_messages(
    player_id LONGINT,
    message_id LONGINT,
    event_id LONGINT,
    FOREIGN KEY(player_id) REFERENCES players(id)
    FOREIGN KEY(event_id) REFERENCES players(id)
);
