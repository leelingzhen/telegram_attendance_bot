
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
    cur.execute("ALTER TABLE events ADD COLUMN description TEXT")
    cur.execute('ALTER TABLE events ADD COLUMN accountable INT DEFAULT 1')
    con.commit()
