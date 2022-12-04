SELECT name, gender, telegram_user, access_control.control_id, attendance.status, attendance.reason FROM players
JOIN attendance on players.id = attendance.player_id
JOIN access_control on players.id = access_control.player_id
WHERE event_id = ? 
AND players.hidden = 0
AND access_control.control_id != 7
ORDER BY 
attendance.status DESC,
players.gender DESC,
players.name

