import csv
import sqlite3
import pandas as pd
from datetime import datetime
import numpy as np

con_db = sqlite3.connect("attendance.db")
db_cursor = con_db.cursor()

attendance = pd.DataFrame()

def change_headers():
    attendance = pd.read_csv("attendance_data.csv")
    new_columns = list()
    for date_str in attendance.columns[1:]:
        date_object = datetime.strptime(date_str, "%a, %d-%m-%y @ %H:%M")
        new_date_entry = int(date_object.strftime("%Y%m%d%H%M"))
        new_columns.append(new_date_entry)
    new_columns = [0] + new_columns
    attendance.columns = new_columns
    attendance = attendance.iloc[:-1]
    return attendance

def change_index(attendance):
    telegram_ids = db_cursor.execute("SELECT name, id FROM players").fetchall()
    name_array = np.array(telegram_ids)[:,0]
    misssing_names = list()
    for name in attendance[0]:
        if name not in name_array:
            misssing_names.append(name)
    attendance = attendance.set_index(0)
    attendance = attendance.drop(index=misssing_names)
    id_list = list()
    for name in attendance.index:
        for element in telegram_ids:
            if name == element[0]:
                id_list.append(element[1])

    attendance.insert(0, "id", id_list)
    attendance = attendance.set_index("id")
    return attendance

def migrate_events_table(attendance):
    for event_id in attendance.columns:
        date_obj = datetime.strptime(str(event_id), "%Y%m%d%H%M")
        con_db.execute("INSERT OR IGNORE INTO events (id, event_type, event_date, start_time) VALUES(?, 'Field Training', ?, ?)", (event_id, date_obj.strftime("%Y-%m-%d"), date_obj.strftime("%H:%M")))
    con_db.commit()

def migrate_attendance(attendance):
    for player_id in attendance.index:
        for event_id in attendance.loc[player_id].index:
            status = attendance.loc[player_id][event_id]
            if type(status) == float:
                continue
            if "(" in status:
                start_reason = status.find("(")+1
                end_reason = status.find(")")
                reason = status[start_reason:end_reason]
            else:
                reason = ""
            if "Yes" in status:
                status = 1
            elif "No" in status:
                status = 0
            insert_row = (event_id, player_id, status, reason)
            con_db.execute(
                    "INSERT OR IGNORE INTO attendance (event_id, player_id, status, reason) VALUES(?,?,?,?)",
                    insert_row
                    )
    con_db.commit()

def main():
    attendance = change_headers()
    attendance = change_index(attendance)
    migrate_events_table(attendance)
    migrate_attendance(attendance)
    return attendance

if __name__ == "__main__":
    main()

