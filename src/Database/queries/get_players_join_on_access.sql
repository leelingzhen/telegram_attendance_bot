SELECT * FROM players
JOIN access_control ON players.id = access_control.player_id
WHERE control_id = ?
ORDER BY
name COLLATE NOCASE

