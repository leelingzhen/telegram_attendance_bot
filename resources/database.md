## SQLite Database Schema Documentation

### Introduction

This document outlines the updated database schema after migrating from the old schema. It includes the structure of the updated tables and explains the migration process from the old schema to the new one.

---

### Updated Database Schema

#### Users Table

* The **players** table has been dropped and replaced by the **users** table.
* The **users** table stores similar data as the **players** table with the same structure.

```sql
CREATE TABLE IF NOT EXISTS users (
    id LONGINT,
    name TEXT,
    telegram_user TEXT,
    gender TEXT,
    notification INT DEFAULT 1,
    language_pack TEXT NOT NULL DEFAULT 'default',
    hidden INT DEFAULT 0,
    PRIMARY KEY(id)
);
```

#### Events Table

* Stores information related to events, including their type, date, time, location, and announcements.

```sql
CREATE TABLE events (
    id LONGINT,
    event_type TEXT,
    event_date DATE,
    start_time TIME,
    end_time TIME DEFAULT '00:00',
    location TEXT,
    announcement TEXT,
    access_control INT DEFAULT 2,
    description TEXT,
    accountable INT DEFAULT 1,
    PRIMARY KEY(id)
);
```

#### Attendance Table

* Tracks attendance of users at events, including status and reason for attendance or absence.

```sql
CREATE TABLE attendance (
    event_id LONGINT,
    user_id LONGINT,
    status INT,
    reason TEXT,
    PRIMARY KEY(event_id, user_id),
    FOREIGN KEY (event_id) REFERENCES events(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### Access Control Table

* Manages permissions for users in the system.

```sql
CREATE TABLE access_control (
    user_id LONGINT,
    control_id INT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (control_id) REFERENCES access_control_description(id)
);
```

#### Gym Exercises Table

* Stores exercise routines used for tracking gym activities.

```sql
CREATE TABLE gym_exercises (
    id INT,
    routine TEXT
);
```

#### Gym Tracker Table

* Tracks the completion of gym routines by users.

```sql
CREATE TABLE gym_tracker (
    user_id LONGINT,
    routine_id LONGINT,
    completions INT
);
```

#### Kaypoh Messages Table

* Logs user messages related to events.

```sql
CREATE TABLE kaypoh_messages (
    user_id LONGINT,
    event_id LONGINT,
    message_id LONGINT,
    PRIMARY KEY(user_id, event_id),
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(event_id) REFERENCES events(id)
);
```

#### Access Control Description Table

* Provides descriptions for each access control level.

```sql
CREATE TABLE access_control_description (
    id INT,
    description TEXT,
    PRIMARY KEY (id)
);
```

#### Announcement Entities Table

* Stores metadata related to event announcements.

```sql
CREATE TABLE announcement_entities (
    event_id LONGINT,
    entity_type TEXT,
    offset INT,
    entity_length INT,
    FOREIGN KEY(event_id) REFERENCES events(id)
);
```

---

### Migration Process

1. Create the **users** table and copy data from **players**.
2. Drop the **players** table.
3. Update **attendance**, **access\_control**, and **kaypoh\_messages** tables to use **user\_id** instead of **player\_id**.
4. Rename old tables to temporary versions, copy data, and drop the temporary tables.

### Purpose of the Update

The primary goal of this migration was to standardize the database schema by:

* Introducing the **users** table to consolidate player data.
* Updating references from **player\_id** to **user\_id** for consistency.
* Maintaining data integrity through foreign key constraints.

For more details on the migration script, refer to the accompanying code file.

