upgrade manager for alliance telegram bot, used to do automatic updates of the DB, config files and other stuff that is not so easily controlled using git with docker environments

## To upgrade:
1. write code for the upgrades in `upgrade.py`
2. increment the version in the `UpgradeManager` instantiation of the main function in both `training_bot.py` and `admin_bot.py`


