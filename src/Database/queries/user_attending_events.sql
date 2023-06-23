SELECT id, event_type FROM events
JOIN attendance ON events.id = attendance.event_id
WHERE attendance.player_id = ?
AND attendance.event_id >= ?
AND attendance.status = ?
AND events.access_control <= ?
ORDER BY id


