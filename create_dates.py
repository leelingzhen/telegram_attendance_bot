import sqlite3
import json
from datetime import datetime, date, timedelta

with open("config.json") as f:
    CONFIG = json.load(f)


def create_dates(
        weekday,
        hour,
        min,
        duration_h,
        duration_m,
        n_events,
        location="TBC",
        access=2,
        event_type="Field Training"
) -> int:
    """
    function will create n_events on weekdays,
    hour and min in 24 hour timing

    return the number of events created
    """
    with sqlite3.connect(CONFIG['database']) as db:
        db.row_factory = sqlite3.Row
        existing_dates = set()
        db_output = db.execute(
            "SELECT event_date, event_type FROM events WHERE event_date >= '2023-05-01'").fetchall()
        for row in db_output:
            date_exist = datetime.strptime(row['event_date'], "%Y-%m-%d")

            existing_dates.add(date_exist)

    target_dates = list()
    for i in range(n_events):
        days = (weekday - datetime.today().weekday() + 7) % 7
        target_date = datetime.today() + timedelta(days=days + i * 7)

        # to compare
        target_date = target_date.replace(
            hour=0, minute=0, second=0, microsecond=0)
        if target_date in existing_dates:
            continue

        target_date = target_date.replace(hour=hour, minute=min)
        target_dates.append(target_date)

    with sqlite3.connect(CONFIG['database']) as db:
        db.execute("BEGIN TRANSACTION")
        for target_date in target_dates:
            start = target_date.strftime("%H:%M")
            end = (target_date + timedelta(hours=duration_h,
                   minutes=duration_m)).strftime("%H:%M")
            data = [
                int(target_date.strftime("%Y%m%d%H%M")),
                event_type,
                target_date.strftime("%Y-%m-%d"),
                start,
                end,
                location,
                None,
                access
            ]
            db.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?)", data)

    return len(target_dates)


if __name__ == "__main__":
    output = create_dates(
        weekday=5,
        hour=14,
        min=0,
        duration_h=1,
        duration_m=30,
        n_events=4,
        location="TBC",
        access=2,
        event_type="Field Training"
    )
    print(output)
