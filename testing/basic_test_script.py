import sys
import os
sys.path.insert(1, '/Users/joseph/data_science/personal_projects/broadcastify-archtk/code/')

from broadcastify_archtk import BroadcastifyArchive
import datetime as dt
# TEST_FEED_ID = '14439' # Travis County, Austin, TX
TEST_FEED_ID = '591' # Boulder County, CO

login_path = '/Users/joseph/data_science/personal_projects/broadcastify-archtk/private/pwd.ini'
# driver_path = '/Users/joseph/GA-DSI/projects/project_5/police-radio-to-mapping/assets/chromedriver'
# archive = BroadcastifyArchive(TEST_FEED_ID, username='ljhopkins2', password='S7!z2jHBuS6GBnR')
# archive = BroadcastifyArchive(TEST_FEED_ID, username='foo', password='bar')
archive = BroadcastifyArchive(
    TEST_FEED_ID,
    login_cfg_path=login_path,
#     webdriver_path=driver_path
)

archive.build(days_back=7, rebuild=True)

mp3_path = '/Users/joseph/data_science/personal_projects/broadcastify-archtk/testing/mp3_downloads/'

archive.download(start=dt.datetime(2019,10,31,20,0), end=dt.datetime(2019,11,1,2,0),
                output_path=mp3_path)
