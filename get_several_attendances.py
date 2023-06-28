import os
import sqlite3
import argparse
import sys
import helpers
import csv
from datetime import datetime

from src.event_manager import TrainingEventManager


db = sqlite3.connect("resources/attendance.db", check_same_thread=False)


def get_attendance_by_month(target_month: datetime) -> list:
    db.row_factory = lambda cursor, row: row[0]
    target_month = target_month.strftime("%m%Y")
    event_id_list = db.execute(
        "SELECT id FROM events WHERE strftime('%m%Y', event_date) = ?", (target_month, )).fetchall()

    return event_id_list


def get_attendance(event_id_list: list) -> dict:
    output = dict()
    for event_id in event_id_list:

        event = TrainingEventManager(event_id=event_id)

        male_records, female_records, absent, unindicated = event.curate_attendance(
            attach_usernames=False)

        player_data = {
                'Male': male_records,
                'Female': female_records,
                'Absent': absent,
                'unindicated': unindicated
                }

        output[event_id] = player_data
    return output


def write_csv_attendance(
        attendance_dict: dict,
        target_month: str,
        out_file: str) -> None:

    if out_file is None:
        out_file = os.path.expanduser(os.path.join(
            "~", 'Desktop', f'attendance_{target_month}.csv'))

    output_rows = list()
    for event_date in attendance_dict:
        pretty_date = datetime.strptime(
            str(event_date), "%Y%m%d%H%M").strftime("%-d-%b-%y, %a")

        for field in attendance_dict[event_date]:
            row = attendance_dict[event_date][field]
            row.insert(0, field)
            row.insert(0, pretty_date)
            output_rows.append(row)

    with open(out_file, 'w', encoding='UTF8') as f:
        writer = csv.writer(f)
        writer.writerows(output_rows)

        """
    input_file = csv.reader(open(out_file, 'r',))
    print(input_file)
    transposed_input = zip(*input_file)
    os.remove(out_file)
    with open(out_file, "w", encoding='UTF8') as f:
        writer = csv.writer(f)
        writer.writerows(transposed_input)
        """

    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", type=str, help='input a month year format in the form mm-yy',
                        default=datetime.now().strftime("%m-%y"))
    parser.add_argument("--weekday", type=int,
                        help="input an int that corresponds to the weekday", default=None)
    parser.add_argument("--out_file", type=str,
                        help="outpath to the file created", default=None)
    args = parser.parse_args()
    target_month = datetime.strptime(args.month, "%m-%y")
    event_id_list = get_attendance_by_month(target_month=target_month)

    attendance_dict = get_attendance(event_id_list)
    write_csv_attendance(
        attendance_dict, target_month=args.month, out_file=args.out_file)


if __name__ == "__main__":
    main()
