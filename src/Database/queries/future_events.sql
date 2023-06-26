SELECT id, event_type
FROM events
WHERE
	id > ?
AND 
	access_control <= ?
ORDER BY id
 
