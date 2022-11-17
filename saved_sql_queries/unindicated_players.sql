SELECT id, name, telegram_user, language_pack FROM players 
JOIN access_control on players.id = access_control.player_id
WHERE name NOT IN 
(
	SELECT name FROM players 
	JOIN attendance ON players.id = attendance.player_id 
	JOIN access_control ON players.id = access_control.player_id
	WHERE event_id=? 
)
AND notification == 1
AND access_control.control_id >= 4

