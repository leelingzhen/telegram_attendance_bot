import setuptools
setuptools.setup(name='attendance_telegram_bot',
                 version='0.1',
                 description='a telegram bot used to manage attendances',
                 url='#',
                 author='Lee Ling Zhen',
                 install_requires=['python-telegram-bot==13.14'],
                 author_email='lee.ling.zhenn+telegram_bot@gmail.com',
                 packages=setuptools.find_packages(),
                 zip_safe=False)
