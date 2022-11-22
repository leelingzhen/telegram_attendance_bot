SELECT id, telegram_user FROM players
JOIN access_control ON players.id = access_control.player_id
WHERE access_control.control_id >= 4 
AND players.notification = 1
ORDER BY
gender DESC,
name
