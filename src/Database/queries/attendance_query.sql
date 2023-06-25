SELECT
	id, name, gender, telegram_user,
	access_control.control_id,
	attendance.status, attendance.reason
FROM players
JOIN attendance on players.id = attendance.player_id
JOIN access_control on players.id = access_control.player_id
WHERE event_id = ?
AND players.hidden = 0
AND access_control.control_id != 7
AND attendance.status = ?
{gender}
AND access_control.control_id {access_range}
ORDER BY
players.gender DESC,
CASE WHEN
	access_control.control_id >= 4 then 0 else 1 end,
players.name

