SELECT * FROM players
JOIN access_control ON players.id = access_control.player_id
WHERE access_control.control_id >= ?
AND players.notification >= ?
AND players.hidden = 0
ORDER BY
gender DESC,
name

