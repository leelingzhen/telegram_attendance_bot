SELECT
	id, name, gender, telegram_user,
	access_control.control_id AS access,
	attendance.status, attendance.reason
FROM players
JOIN attendance on players.id = attendance.player_id
JOIN access_control on players.id = access_control.player_id
WHERE event_id = ?
AND players.hidden = 0
AND attendance.status = ?
AND gender = ?
AND access_control.control_id >= 2
AND access_control.control_id <4
ORDER BY
players.name COLLATE NOCASE,
players.gender DESC


