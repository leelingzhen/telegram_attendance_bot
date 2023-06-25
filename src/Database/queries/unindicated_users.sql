    SELECT id, name, telegram_user,
    access_control.control_id
    FROM players
    JOIN access_control on players.id = access_control.player_id
    WHERE name NOT IN
    (
	SELECT name FROM players
	JOIN attendance ON players.id = attendance.player_id
	JOIN access_control ON players.id = access_control.player_id
	WHERE event_id = ?
    )
    AND notification == 1
    AND access_control.control_id {access_range}
    AND access_control.control_id != 7
    AND players.hidden = 0
    ORDER BY
    players.gender DESC,
    players.name COLLATE NOCASE


