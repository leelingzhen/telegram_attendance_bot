.open attendance.db
CREATE TABLE IF NOT EXISTS players(
    id LONGINT,
    name TEXT, 
    gender TEXT, 
    notification INT, 
    language_pack INT, 
    PRIMARY KEY(id)
);
CREATE TABLE events(
    id LONGINT, 
    event_type TEXT, 
    event_date DATE, 
    start_time TIME, 
    end_time TIME, 
    description TEXT, 
    PRIMARY KEY(id)
);
CREATE TABLE attendance(
    event_id LONGINT, 
    player_id LONGINT, 
    status INT, 
    reason TEXT, 
    FOREIGN KEY(event_id) REFERENCES events(id), 
    FOREIGN KEY(player_id) REFERENCES players(id)
);
CREATE TABLE access_control(
    player_id LONGINT,
    control_id INT,
    FOREIGN KEY(player_id) REFERENCES players(id),
    FOREIGN KEY(control_id) REFERENCES access_control_description(id)
);
CREATE TABLE access_control_description(
    id INT,
    description TEXT,
    PRIMARY KEY (id)
);
CREATE TABLE gym_exercises(
    id INT,
    routine TEXT
);
CREATE TABLE gym_tracker(
    player_id LONGINT,
    routine_id LONGINT,
    completions INT
);

