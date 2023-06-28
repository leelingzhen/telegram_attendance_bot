
import logging


def upgrade_script(prev_ver, cur_ver):
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
    )
    logger = logging.getLogger(__name__)
    logger.info('upgrading from %.2f to %.2f', prev_ver, cur_ver)
