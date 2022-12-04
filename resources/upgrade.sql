ALTER TABLE players ADD hidden INT DEFAULT 0;
UPDATE access_control_description SET description = 'Team Manager' WHERE id = 7;
INSERT INTO access_control_description VALUES (100, 'Super User');
UPDATE access_control SET control_id = 100 WHERE player_id = '89637568'
