
import logging
import sqlite3


def upgrade_script(prev_ver, cur_ver, testing):
    if testing:
        return
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
    )
    logger = logging.getLogger(__name__)
    logger.info('upgrading from %.2f to %.2f', prev_ver, cur_ver)
    con = sqlite3.connect('resources/attendance.db')
    cur = con.cursor()
    cur.execute('BEGIN TRANSACTION')
    cur.execute("""
                CREATE TABLE IF NOT EXISTS 'event_poll_options' (
                    event_id LONGINT,
                    poll_id INT,
                    poll_description TEXT,
                    FOREIGN KEY(event_id) REFERENCES events(id)
                    )
                """
                )
    con.commit()
