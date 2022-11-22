SELECT id, name, gender, telegram_user, access_control.control_id, attendance.status, attendance.reason FROM players
JOIN attendance on players.id = attendance.player_id
JOIN access_control on players.id = access_control.player_id
WHERE event_id = ? 
AND attendance.status = 1 
AND access_control.control_id >= 2
ORDER BY 
players.gender DESC,
players.name
 
