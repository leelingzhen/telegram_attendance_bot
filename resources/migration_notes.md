# SQLite Database Schema Documentation

## Introduction

This document outlines the updated database schema after migrating from the old schema. It includes the structure of the updated tables and explains the migration process from the old schema to the new one.

### Updated Database Schema

#### Users Table

The players table has been dropped and replaced by the users table.
The users table stores similar data as the players table with the same structure.

``` sql
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

#### Attendance Table

The attendance table has been modified to replace player_id with user_id to maintain consistency with the users table.
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

The access_control table also replaced player_id with user_id.

```sql
CREATE TABLE access_control (
    user_id LONGINT,
    control_id INT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (control_id) REFERENCES access_control_description(id)
);
```

#### Kaypoh Messages Table

The kaypoh_messages table was updated to use user_id instead of player_id.

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

## Migration Process

Create the users table and copy data from players.

Drop the players table.

Update attendance, access_control, and kaypoh_messages tables to use user_id instead of player_id.

Rename old tables to temporary versions, copy data, and drop the temporary tables.

Purpose of the Update

The primary goal of this migration was to standardize the database schema by:

Introducing the users table to consolidate player data.

Updating references from player_id to user_id for consistency.

Maintaining data integrity through foreign key constraints.

For more details on the migration script, refer to the accompanying code file.


