#-----------------------------------------------------------------------------
#
# This work is licensed under a GNU Affero General Public License v3.0. See
# the GitHub repo for more details:
# https://github.com/ljhopkins2/BArT/blob/master/LICENSE
#
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
#
# The _B_roadcastify _AR_chive _T_oolkit
# v1.0-beta
#
#   |\/\/\/|  +------------------------+
#   |      |  | Eat my shortwave, man. |
#   |      |  +------------------------+
#   | (o)(o)    /
#   C      _)  /
#    | ,___|
#    |   /
#   /____\
#  /      \
#
# Artwork source: https://www.asciiart.eu/cartoons/simpsons
#
#-----------------------------------------------------------------------------


# Throughout the file, "ATT" is short for "archiveTimes table", which contains
# archive entry information for the date selected in the navigation calendar


#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
#
#
#
# Imports
#-----------------------------------------------------------------------------
import errno as _errno
import os as _os
import re as _re
import requests as _requests
import datetime as _dt

from configparser import ConfigParser as _ConfigParser, \
                         ExtendedInterpolation as _ExtendedInterpolation
from IPython.display import clear_output as _clear_output
from time import time as _timer

from bs4 import BeautifulSoup as _BeautifulSoup

from selenium import webdriver as _webdriver
from selenium.webdriver.support import wait as _wait
from selenium.webdriver.common.keys import Keys as _Keys
from selenium.webdriver.support.ui import WebDriverWait as _WebDriverWait
from selenium.webdriver.support import expected_conditions as _EC
from selenium.webdriver.common.by import By as _By
from selenium.webdriver.chrome.options import Options as _Options
from selenium.common.exceptions import NoSuchElementException as _NSEE, \
                                       ElementNotInteractableException as _ENI





#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
#
#
#
# Constants & Configs
#-----------------------------------------------------------------------------
_CONFIG_FILENAME = 'config.ini'
_MONTHS = ['','January', 'February', 'March',
      'April', 'May', 'June',
      'July', 'August', 'September',
      'October', 'November', 'December']

_NO_ATT_DATA = -1

_config = _ConfigParser(interpolation=_ExtendedInterpolation())
_config_result = _config.read(_CONFIG_FILENAME)

if len(_config_result) == 0:
    raise FileNotFoundError(_errno.ENOENT,
                            _os.strerror(_errno.ENOENT),
                            _CONFIG_FILENAME)

# Base URLs
_FEED_URL_STEM = _config['base_urls']['FEED_URL_STEM']
_ARCHIVE_FEED_STEM = _config['base_urls']['ARCHIVE_FEED_STEM']
_ARCHIVE_DOWNLOAD_STEM = _config['base_urls']['ARCHIVE_DOWNLOAD_STEM']
_LOGIN_URL = _config['base_urls']['LOGIN_URL']

# Throttle times
_FILE_REQUEST_WAIT = _config.getfloat('throttle_times',
                                      'FILE_REQUEST_WAIT',
                                      fallback=5)
_PAGE_REQUEST_WAIT = _config.getfloat('throttle_times',
                                      'PAGE_REQUEST_WAIT',
                                      fallback=2)
_DATE_NAV_WAIT = _config.getfloat('throttle_times',
                                      'DATE_NAV_WAIT',
                                      fallback=0.1)

# Selenium
_WEBDRIVER_PATH = _config.get('selenium_config',
                              'WEBDRIVER_PATH',
                              fallback=None)

if _WEBDRIVER_PATH == '':
    _WEBDRIVER_PATH = None

_FIRST_URI_IN_ATT_XPATH = "//a[contains(@href,'/archives/download/')]"

# Output path
_MP3_OUT_PATH = _config['output_path']['MP3_OUT_PATH']

# Authentication data
_AUTH_DATA_PATH = _config['authentication_path']['AUTH_DATA_PATH']





#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
#
#
#
# Functions
#-----------------------------------------------------------------------------
def _login_credentials_present(username, password):
    if not username or not password:
        raise _NavigatorException(
                "No login credentials supplied.")
    else:
        return True

def _get_feed_name(feed_id):
    s = _requests.Session()
    with s:
        r = s.get(_FEED_URL_STEM + feed_id)
        if r.status_code != 200:
            raise ConnectionError(f'Problem connecting: {r.status_code}')

        soup = _BeautifulSoup(r.text, 'lxml')

        return soup.find('span', attrs={'class':'px13'}).text

def _diff_month(d1, d2):
    return (d2.year - d1.year) * 12 + d2.month - d1.month




#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
#
#
#
# CLASSES
#-----------------------------------------------------------------------------





#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
#
#
#
# BroadcastifyArchive
#-----------------------------------------------------------------------------
class BroadcastifyArchive:
    def __init__(self, feed_id, username=None, password=None,
                 show_browser_ui=False, verbose=True):
        """
        A container for Broadcastify feed archive data, and an enginge for re-
        trieving archive entry information and downloading the corresponding mp3
        files. Initializes to an empty container. See user documentation for
        information about dependencies (including Selenium, the WebDriver for
        Chrome, and BeautifulSoup 4).

        Parameters
        ----------
        feed_id : str
            The unique feed identifier the container will represent, taken from
            https://www.broadcastify.com/listen/feed/[feed_id].
        username : str
            The username for a valid Broadcastify premium account.
        password : str
            The password for a valid Broadcastify premium account.
        verbose : bool
            If True, the system will generate more verbose output during longer
            operations.

        Attributes & Properties
        -----------------------
        feed_id  : str
        username : str
        password : str
            Same as init parameter
        feed_url : str
            Full https URL for the feed's main "listen" page.
        archive_url : str
            Full https URL for the feed's archive page.
        entries : dictionary
            Container for archive entry information.
            feed_id : str
                [Populated at .build] Same as feed_id parameter.
            uri : str
                [Populated at .build] The unique ID for an individual archive
                file page, which corresponds to a feed's transmissions over a
                ~30-minute period on a given date. Can be used to find the mp3
                file's individual download page. This page is password protected
                and limited to premium account holders.
            start_time : datetime
                [Populated at .build] Beginning time of the archive entry.
            end_time : datetime
                [Populated at .build] Ending time of the archive entry.
            mp3_url : str
                [Populated at .download] The URL of the corresponding mp3 file.
        earliest_entry : datetime
        latest_entry   : datetime
            The datetime of the earliest/latest archive entry currently in
            `entries`.
        show_browser_ui : Boolean
            If true, Selenium will open a Chrome browser window in the UI and
            display browser activity during .build() navigation page scraping;
            otherwise, scraping will happen "invisibly". Note that no browser
            will be shown during archive initialization or .download(), since
            requests.Session() is used for those activities.
        """

        self.feed_id = feed_id
        self.feed_name = _get_feed_name(feed_id)
        self.feed_url = _FEED_URL_STEM + feed_id
        self.archive_url = _ARCHIVE_FEED_STEM + feed_id
        self.username = username
        self.password = password
        self.entries = []
        self.earliest_entry = None
        self.latest_entry = None
        self.start_date = None
        self.end_date = None
        self.show_browser_ui = show_browser_ui
        self.throttle = _RequestThrottle()

        self._verbose = verbose

        # If username or password was not passed...
        if not username or not password:
            # ...try to get it from the pwd.ini file
            config_result = _config.read(_AUTH_DATA_PATH)

            if len(config_result) == 0:
                raise FileNotFoundError(_errno.ENOENT,
                                        _os.strerror(_errno.ENOENT),
                                        _AUTH_DATA_PATH)

            self.username = _config['authentication_data']['username']
            self.password = _config['authentication_data']['password']

        # If still no username/password, set it to null and work it out
        # later during download().
        if self.username == '':
            self.username = None

        if self._password == '':
            self.password = None

        # Initialize calendar navigation
        if self._verbose:
            print(f'Initializing calendar navigation...')

        # Set whether to show browser UI while fetching
        options = _Options()
        if not self.show_browser_ui:
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')

        # Launch Chrome
        with _webdriver.Chrome(chrome_options=options) as browser:
            browser.get(self.archive_url)
            self.archive_calendar = ArchiveCalendar(self, browser,
                                                    get_dates=True)
            self.start_date = self.archive_calendar.start_date
            self.end_date = self.archive_calendar.end_date

        self.archive_calendar = None

        if self._verbose:
            print('Initialization complete.\n')
            print(self)

    def build(self, start=None, end=None, days_back=0, chronological=False,
              rebuild=False):
        """
        Build archive entry data for the BroadcastifyArchive's feed_id and
        populate as a dictionary to the .entries attribute.

        Parameters
        ----------
            start : datetime.date
                The earliest date for which to populate the archive
            end : datetime.date
                The earliest date for which to populate the archive
            days_back : int
                The number of days before the current day to retrieve informa-
                tion for. A value of `0` retrieves only archive entries corres-
                ponding to the current day.
            chronological : bool
                By default, start with the latest date and work backward in
                time. If True, reverse that.
            rebuild : bool
                Specifies that existing data in the `entries` list should be
                overwritten with data newly fetched from Broadcastify.
        """
        # Prevent the user from unintentionally erasing existing archive info
        if self.entries and not rebuild:
            raise ValueError(f'Archive already built: Entries already exist for'
                             f'this BroadcastifyArchive. To erase and rebuild, '
                             f'specify `rebuild=True` when calling .build()')

        # Make sure valid arguments were passed
        ## Either start/end or days_back; not both
        if (start or end) and days_back:
            raise ValueError(f'Expected either `days_back` OR a `start`/`end` '
                             f'combination. Both were passed.')

        ## `days_back` must be a non-negative integer
        if days_back:
            try:
                days_back = int(days_back)
                if days_back < 0: days_back = 0
            except:
                raise TypeError(f'`days_back` must be a non-negative integer.')

        # Build the list of dates to scrape
        ## If we're using start & end dates (not days back)...
        out_of_range = ''

        if not days_back:
            # Check that `start` and `end` within archive's start & end dates
            if start:
                if start < self.start_date:
                    out_of_range = (f'start date out of archive range: '
                                    f'{start} < {self.start_date}\n')
                elif start > self.end_date:
                    out_of_range = (f'start date out of archive range: '
                                    f'{start} > {self.end_date}\n')
            else:
                start = self.start_date

            if end:
                if end > self.end_date:
                    out_of_range += (f'end date out of archive range: '
                                     f'{end} > {self.end_date}')
                elif end < self.start_date:
                    out_of_range += (f'end date out of archive range: '
                                     f'{end} < {self.start_date}')
            else:
                end = self.end_date

            if out_of_range:
                raise AttributeError(out_of_range)

            # Get the size of the date range
            days_back = (end - start).days

        ## `start` cannot be > `end`
        if start > end:
            raise AttributeError(f'`start` date ({start}) cannot be after `end` '
                                 f'date ({end}).')

        # Adjust for the exclusive end of range()
        days_back += 1

        date_list = sorted([end - _dt.timedelta(days=x) for x in range(days_back)],
                           reverse=not(chronological))

        archive_entries = []

        # Spin up a browser and an ArchiveCalendar
        # Set whether to show browser UI while fetching
        options = _Options()
        if not self.show_browser_ui:
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')

        # with _webdriver.Chrome(chrome_options=options) as browser:
        browser = _webdriver.Chrome(chrome_options=options)
        browser.get(self.archive_url)
        self.arch_cal = ArchiveCalendar(self, browser)

        # Get archive entries for each date in list
        for i, date in enumerate(date_list):
            ####_clear_output(wait=True)
            if self._verbose: print(f'Parsing archive entry for {date} '
                                    f'({i + 1} of {len(date_list)})')

            self.arch_cal.go_to_date(date)

            if self.arch_cal.entries_for_date:
                archive_entries.extend(self.arch_cal.entries_for_date)

        if self._verbose: print('Processing archive entries...')

        # Empty & replace the current archive entries
        self.entries = []

        # Store URIs and end times in the entries attritbute
        for entry in archive_entries:
            entry_dict = {
                'uri': entry[0],
                'start_time': entry[1],
                'end_time': entry[2]
            }

            self.entries.append(entry_dict)

        ####_clear_output(wait=True)

        self.earliest_entry = max(self.start_date, start)
        self.latest_entry = min(self.end_date, end)

        if self._verbose:
            print(f'Archive build complete.\n')
            print(self)

    def download(self, start=None, end=None, all_entries=False,
             output_path=_MP3_OUT_PATH):
        """
        Retrieve URIs and download mp3 files for the Broadcastify archive.

        Parameters
        ----------
        start : datetime.datetime
            The earliest date & time for which to download files
        end : datetime.datetime
            The latest date & time for which to retrieve files
        all_entries : boolean
            Download all available archive files

          Behavior
          --------
            Omit   `start` ---------> retrieve from the earliest archive
            Supply `end`              file through the file covering `end`

            Supply `start` ---------> retrieve from the archive file
            Omit   `end`              containing `start` through the last archive
                                      file

           `all_entries` is True --> retrieve all files; ignore other arguments

           `all_entries` is False -> raise an error
            Omit `start`
            Omit `end`
          --------

        output_path : str (optional)
            The local path to which archive entry mp3 files will be written. The
            path must exist before calling the method. Defaults to the value
            supplied in config.ini -> _MP3_OUT_PATH.
        """
        # Make sure arguments were passed in a valid combination
        if not all_entries:
            if all([not(start), not(end)]):
                raise ValueError(f'One of `start`, `end`, or `dates` must be'
                                   f'supplied.')

        # Make sure everything is a datetime
        if not all([isinstance(start, _dt.datetime), isinstance(end, _dt.datetime)]):
            raise TypeError(f'`start` and `end` must be of type `datetime`.')

        # Build the list of download dates; store in filtered_entries
        if all_entries:
            filtered_entries = self.entries
        else:
            filter_start = _dt.datetime.combine(self.earliest_entry,
                                            _dt.datetime(1,1,1,0,0).time())

            filter_end = _dt.datetime.combine(self.latest_entry,
                                          _dt.datetime(1,1,1,0,0).time())

            if start:
                filter_start = start
            if end:
                filter_end = end

            filtered_entries = [entry for entry in self.entries if
                                entry['start_time'] >= filter_start and
                                entry['end_time'] <= filter_end]

        # Retrieve the file URIs
        dn = ArchiveDownloader(self, login=True, username=self.username,
                               password=self._password, verbose=self._verbose)

        if self._verbose:
            print(f'{len(filtered_entries)} archive entries matched.')

        # Pass them to _DownloadNavigator to get the files
        dn.get_archive_mp3s(filtered_entries, output_path)

    @property
    def feed_id(self):
        """
        Unique ID for the Broadcastify feed. Taken from
        https://www.broadcastify.com/listen/feed/[feed_id]
        """
        return self._feed_id
    @feed_id.setter
    def feed_id(self, value):
        self._feed_id = value
        self.feed_name = _get_feed_name(value)
        self.start_date = None
        self.end_date = None
        self.entries = []
        self.earliest_entry = None
        self.latest_entry = None
        self.feed_url = _FEED_URL_STEM + value
        self.archive_url = _ARCHIVE_FEED_STEM + value
        self._an = None

    @property
    def password(self):
        """
        Password for Broadcastify premium account. Getting the property
        will return a Boolean indicating whether the password has been set.
        """
        if self._password:
            return True
        else:
            return False
    @password.setter
    def password(self, value):
        self._password = value

    def __repr__(self):
        repr = f'BroadcastifyArchive\n' + \
               f' (Feed ID = {self.feed_id}\n' + \
               f'  Feed Name = {self.feed_name}\n' + \
               f'  Feed URL = "{self.feed_url}"\n' + \
               f'  Archive URL = "{self.archive_url}"\n' + \
               f'  Start Date: {str(self.start_date)}\n' + \
               f'  End Date:   {str(self.end_date)}\n' + \
               f'  Username = "{self.username}" Password = [{self.password}]\n' + \
               f"  {'{:,}'.format(len(self.entries))} parsed archive entries "

        if not(self.earliest_entry is None and self.latest_entry is None):
            repr += f'between {self.earliest_entry} and {self.latest_entry}'

        repr += f'\n  Verbose = {self._verbose})'

        return repr

#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
#
#
#
# ArchiveDownloader
#-----------------------------------------------------------------------------
class ArchiveDownloader:
    def __init__(self, parent, login=False, username=None, password=None,
                 verbose=False):
        self._parent = parent

        self.download_page_soup = None
        self.current_archive_id = None
        self.verbose = verbose
        self.throttle = t = _RequestThrottle()
        self.session = s = _requests.Session()
        self.login = l = login

        # If login requested, populated login info
        if l:
            # Set post parameters
            login_data = {
                'username': username,
                'password': password,
                'action': 'auth',
                'redirect': '/'
            }

            headers = {
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) ' +
                              'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/' +
                              '75.0.3770.142 Safari/537.36'
            }

            _login_credentials_present(username, password)

            t.throttle('file')
            r = s.post(_LOGIN_URL, data=login_data, headers=headers)

            if r.status_code != 200:
                raise ConnectionError(f'Problem connecting: {r.status_code}')

    def get_download_soup(self, archive_id):
        self.current_archive_id = archive_id
        s = self.session
        t = self.throttle

        t.throttle()
        r = s.get(_ARCHIVE_DOWNLOAD_STEM + archive_id)
        if r.status_code != 200:
            raise ConnectionError(f'Problem connecting to ' +
                    f'{_ARCHIVE_DOWNLOAD_STEM + archive_id}: {r.status_code}')

        self.download_page_soup = _BeautifulSoup(r.text, 'lxml')

        return self.download_page_soup

    def get_archive_mp3s(self, archive_entries, filepath):
        start = _timer()

        for file in archive_entries:
            feed_id =  self._parent.feed_id
            archive_uri = file['uri']
            file_date = self.__format_entry_date(file['end_time'])

            print(f'Downloading {archive_entries.index(file) + 1} of '
                  f'{len(archive_entries)}')

            # Build the path for saving the downloaded .mp3
            out_file_name = filepath + '-'.join([feed_id, file_date]) + '.mp3'

            # Get the URL of the mp3 file
            mp3_soup = self.get_download_soup(archive_uri)
            file_url = self.__parse_mp3_path(mp3_soup)

            if self.verbose:
                print(f'\tfrom {file_url}')
                print(f'\tto {out_file_name}')

            self.__fetch_mp3([out_file_name, file_url])

        duration = _timer() - start

        if len(archive_entries) > 0: print('\nDownloads complete.')
        if self.verbose:
            print(f'\nRetrieved {len(archive_entries)} files in '
                  f'{round(duration,4)} seconds.')

    def __parse_mp3_path(self, download_page_soup):
        """Parse the mp3 filepath from a BeautifulSoup of the download page"""
        return download_page_soup.find('a',
                                       {'href': _re.compile('.mp3')}
                                       ).attrs['href']

    def __fetch_mp3(self, entry):
        # h/t https://markhneedham.com/blog/2018/07/15/python-parallel-
        # download-files-requests/
        path, uri = entry

        if not _os.path.exists(path):
            self.throttle.throttle('file')
            r = _requests.get(uri, stream=True)
            if r.status_code == 200:
                with open(path, 'wb') as f:
                    for chunk in r:
                        f.write(chunk)
        else:
            print('\tFile already exists. Skipping.')

        return path

    def __format_entry_date(self, date):
        # Format the ArchiveEntry end time as YYYYMMDD-HHMM
        year = date.year
        month = date.month
        day = date.day
        hour = date.hour
        minute = date.minute

        return '-'.join([str(year) + str(month).zfill(2) + str(day).zfill(2),
                         str(hour).zfill(2) + str(minute).zfill(2)])

    def __repr__(self):
        return(f'_DownloadNavigator(Current Archive: '
               f'{self.current_archive_id})')

#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
#
#
#
# ArchiveCalendar
#-----------------------------------------------------------------------------
class ArchiveCalendar:
    def __init__(self, parent, browser, get_dates=False):
        self.parent = parent
        self._browser = browser

        ## Wait for calendar to load on navigation page
        element = _WebDriverWait(self._browser, 10).until(
                                 _EC.presence_of_element_located((
                                 _By.CLASS_NAME, 'datepicker-switch')))

        # Initialize object attributes
        self._scrape_contents()        # Initializes _contents
        self._parse_calendar_attrs()   # Initializes _calendar, displayed_month,
                                       # & active_date
        if get_dates:
            self.end_date = self.active_date
            self._get_start_date()     # Initializes start_date
        else:
            self.end_date = self.parent.end_date
            self.start_date = self.parent.start_date

        self._att = ArchiveTimesTable(self, browser)

    def update(self):
        self._wait_for_refresh()
        self._scrape_contents()
        self._parse_calendar_attrs()

    def go_to_date(self, date):
        ### Navigate to & click on a date in the archive calendar; the clicked-
        ### on date becomes the new active_date, which is returned.

        # If date is "today" or equal to end_date, take the shortcut
        if date == 'today' or date == self.end_date:
            try:
                self.parent.throttle.throttle('date_nav')
                self._browser.find_element_by_class_name('today').click()
                self._wait_for_refresh()
                return self._displayed_month_dt
            except _NSEE:
                return False

        # Check that the date is valid (between start & end dates)
        if not (self.start_date <= date <= self.end_date):
            raise ValueError(f'`date` argument must be between start and end '
                             f' dates ({self.start_date} to {self.end_date}).')

        # Get the day to click on
        new_day = date.day

        # Get the number of months to traverse...
        months_to_traverse = _diff_month(self.active_date, date)

        if months_to_traverse >= 0:
            step_direction = 1
            button_name = 'next'
        else:
            step_direction = -1
            button_name = 'prev'

        # ...and do so.
        for _ in range(0, months_to_traverse, step_direction):
            self._traverse_month(button_name)

        # Click the day
        self.parent.throttle.throttle('date_nav')
        try:
            self._browser.find_element_by_xpath(f"//td[@class='day' "
                                    f"and contains(text(), '{new_day}')]"
                                    ).click()
        except:
            self._browser.find_element_by_xpath(f"//td[@class='active day' "
                                    f"and contains(text(), '{new_day}')]"
                                    ).click()
        self.update()
        self._att.update()

    def _get_start_date(self):
        ### Return the earliest navigable date in the archive
        start_date = None

        # Navigate backward to the beginning month of the archive
        while self._traverse_month('prev'):
            pass

        # Grab the beginning month
        start_month = self._displayed_month_dt

        # Parse the lowest valid day
        disabled_found = False
        for day in self._calendar:
            if day['class'][0] == 'disabled':
                disabled_found = True
            elif day['class'][0] in 'day active'.split():
                start_date = day.text
                break
            elif day['class'][0] != 'old' and disabled_found:
                start_date = day.text
                break

        # Turn it into a date
        if start_date:
            start_date = _dt.date(self._displayed_month_dt.year,
                                  self._displayed_month_dt.month,
                                  int(start_date))

        # Navigate back to the current date
        self.go_to_date('today')

        # Return the start date
        self.start_date = start_date

    def _parse_calendar_attrs(self):
        """
        Populates the following ArchiveCalendar attributes:
            _calendar: bs4 ResultSet
                The <td> tags of the currently displayed calendar. See below
                for details.
            displayed_month: str
                The month currently shown in the calendar, as 'Mmmm YYYY'
            active_date: date
                If the calendar is displaying the active date, update its value.
                The active date is always the date for which ATT entries are
                displayed.

        The _calendar attribute entries have the format

            `<td class="[class]">[D]</td>`

        where
         - [D] is the one- or two-digit day (as a string) and
         - [class] is one of
             "old day"          = a day with archives but in a prior month
                                  (clicking will refresh the calendar)
             "day"              = a day in the current month other than the
                                  active day
             "active day"       = the day currently displayed in the ATT
             "disabled day"     = a day for which no archive is available in a
                                  month (past or future) that has other days
                                  with archives. For example, if today is July
                                  27, July 28-31 will be disabled days, as will
                                  January 1-26 (since the archive goes back only
                                  180 days). December 31 would be an "old dis-
                                  abled day".
             "new disabled day" = a day in a future month
             "old disabled day" = see explanation in "disabled day"
        """
        # Get the tags representing the days currently displayed on the calendar
        self._calendar = self._contents.find_all('td')

        # Get the displayed month
        self.displayed_month = self._contents.find('th',
                                                  {'class': 'datepicker-switch'}
                                                  ).text
        # Get the active date, if shown
        active_day = None
        for day in self._calendar:
            if day['class'][0] == 'active':
                active_day = int(day.text)
        if active_day:
            self.active_date = _dt.date(self._displayed_month_dt.year,
                                    self._displayed_month_dt.month,
                                    active_day)

    def _scrape_contents(self):
        ### Scrape the contents of the currently displayed calendar
        # Scrape the nav page
        soup = _BeautifulSoup(self._browser.page_source, 'lxml')

        # Isolate & store the calendar contents
        self._contents = soup.find('table', {'class': 'table-condensed'})

    def _traverse_month(self, direction):
        ### Click on the 'prev' or 'next' arrow
        try:
            self.parent.throttle.throttle('date_nav')
            self._browser.find_element_by_class_name(direction).click()
            self._wait_for_refresh()
            self._scrape_contents()
            self._parse_calendar_attrs()
            return self._displayed_month_dt
        except _ENI:
            return False

    def _wait_for_refresh(self):
        # Wait for calendar widget to refresh
        element = _WebDriverWait(self._browser, 5
                    ).until(_calendar_to_be_refreshed(self.displayed_month,
                                                      str(self.active_date.day)
                                                      ))

    @property
    def displayed_month(self):
        return self._displayed_month
    @displayed_month.setter
    def displayed_month(self, value):
        self._displayed_month = value

        if value:
            month, year = value.split(' ')
            displayed_month = _MONTHS.index(month)
            displayed_year = int(year)

            self._displayed_month_dt =  _dt.date(displayed_year,
                                                 displayed_month, 1)

    @property
    def entries_for_date(self):
        return self._att.current_entries
    @entries_for_date.setter
    def entries_for_date(self, value):
        raise AttributeError("archive_entries is read only and cannot be set.")

    def __repr__(self):
        return (f'ArchiveCalendar(from {self.start_date} to {self.end_date}, '
                f'active date={self.active_date})')

#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
#
#
#
# ArchiveTimesTable
#-----------------------------------------------------------------------------
class ArchiveTimesTable:
    def __init__(self, parent, browser):
        self.parent = parent
        self._browser = browser

        ## Wait for ATT to load on navigation page
        element = _WebDriverWait(self._browser, 10).until(
                                 _EC.presence_of_element_located((
                                 _By.CLASS_NAME, 'cursor-link')))

        # Initialize object attributes
        self._scrape_contents() # Initializes _contents
        self._parse_entries()   # Initializes current_entries
        self.last_refresh = None

        # Set up MutationObserver to handle refresh waits for consecutive dates
        # with no data
        self._browser.execute_script(
        """ new MutationObserver(() => {
                window.lastRefresh = new Date()
            }).observe(
            document.querySelector(
            "table.table.table-striped.table-bordered.hover.dataTable.no-footer"
            ), {attributes: true, childList: true, subtree: true } )
        """
        )

    def update(self):
        self._wait_for_refresh()
        self._scrape_contents()
        self._parse_entries()

    def _parse_entries(self):
        """
        Parses file information from the ATT into a list of lists containing
        three elements:
            - URI for the mp3 file of the archived radio transmission, which
              will be used later to find the file's individual download page
            - Start date & time of the archive file
            - End date & time of the archive file
        """
        # Set up a blank list to return
        att_entries = []

        # Loop through all rows of the table
        for row in self._contents.find_all('tr'):
            # Grab the start & end times from the row's <td> tags
            file_start, file_end = self._get_entry_datetimes(
                                    [(each.text) for each
                                     in row.find_all('td')])

            # Grab the file ID
            file_uri = row.find('a')['href'].split('/')[-1]

            # Put the file date/time and URL leaf (as a list) into the list
            att_entries.append([file_uri, file_start, file_end])
        if att_entries:
            self.current_entries = att_entries
            self.current_first_uri = att_entries[0][0]
        else:
            self.current_entries = None
            self.current_first_uri = None

    def _scrape_contents(self):
        ### Scrape the contents of the currently displayed calendar
        # Scrape the nav page
        soup = _BeautifulSoup(self._browser.page_source, 'lxml')

        # Isolate & store the ATT contents
        self._contents = soup.find('table', attrs={'id': 'archiveTimes'}
                                  ).find('tbody')

    def _wait_for_refresh(self):
        # If the ATT previously had entires...
        if self.current_first_uri:
            # ...wait until the first entry URI is different
            element = _WebDriverWait(self._browser, 5).until_not(
                            _text_to_be_present_in_href((
                                _By.XPATH, _FIRST_URI_IN_ATT_XPATH),
                                self.current_first_uri))
        else:
            # ...otherwise wait until ATT data has been refreshed
            element = _WebDriverWait(self._browser, 5).until_not(
                            _att_to_be_updated((self.last_refresh)))

    def _get_entry_datetimes(self, times):
        """
        Convert the archive entry start & end times from a list of strings
        to a tuple of datetimes
        """
        # Set date component to the date currently displayed
        date = self.parent.active_date

        # Get time objects from the HH:MM AM/PM text
        hhmm_start, hhmm_end = [ _dt.datetime.strptime(each, '%I:%M %p').time()
                                for each in times]

        # Set the end time
        end = _dt.datetime.combine(date, hhmm_end)

        # If the start time is bigger than the end time, the archive starts on
        # the previous day
        if hhmm_start > hhmm_end:
            date -= _dt.timedelta(days=1)
            start = _dt.datetime.combine(date, hhmm_start)
        else:
            start = _dt.datetime.combine(date, hhmm_start)

        return (start, end)

    def __repr__(self):
        return (f'ArchiveTimesTable()')





#-----------------------------------------------------------------------------
# _NavigatorException
#-----------------------------------------------------------------------------
class _NavigatorException(Exception):
    pass

#-----------------------------------------------------------------------------
# _RequestThrottle
#-----------------------------------------------------------------------------
class _RequestThrottle:
    """
    Limits the pace with which requests are sent to Broadcastify's servers.
    """
    def __init__(self):
        self.last_file_req = _timer()
        self.last_page_req = _timer()

    def throttle(self, type='page', wait=None):
        """
        Throttle various types of requests. Valid types are:
            - 'page': throttle html requests
            - 'file': throttle mp3 downloads
            - 'date_nav': throttle clicks on elements of the ArchiveCalendar
        """
        duration = wait

        if type == 'page':
            duration = _PAGE_REQUEST_WAIT
        elif type == 'file':
            duration = _FILE_REQUEST_WAIT
        elif type == 'date_nav':
            duration = _DATE_NAV_WAIT


        self._wait(duration)

    def _wait(self, duration):
        while not _timer() - self.last_file_req >= duration:
            pass
        self.last_file_req = _timer()





#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
#
# Custom Selenium Expected Conditions
#-----------------------------------------------------------------------------


#-----------------------------------------------------------------------------
# _text_to_be_present_in_href
#-----------------------------------------------------------------------------
class _text_to_be_present_in_href(object):
    """
    A CUSTOM Selenium expectation for checking if the given text is present in
    the element's locator, href attribute
    """
    def __init__(self, locator, text_):
        self.locator = locator
        self.text = text_

    def __call__(self, driver):
        try:
            element_text = _EC._find_element(driver,
                                         self.locator).get_attribute('href')
            if element_text:
                return self.text in element_text
            else:
                return False
        except:
            return False

#-----------------------------------------------------------------------------
# _att_to_be_updated
#-----------------------------------------------------------------------------
class _att_to_be_updated(object):
    """
    A CUSTOM Selenium expectation for checking whether the ATT has been updated.
    """
    def __init__(self, last_refresh):
        self.last_refresh = last_refresh

    def __call__(self, driver):
        try:
            update = self.browser.execute_script('return window.lastRefresh')

            if update:
                if last_refresh:
                    # Convert to a datetime
                    update = _dt.datetime.strptime(update,
                                                   '%Y-%m-%dT%H:%M:%S.%fZ')
                    return self.last_refresh <= update
                else:
                    return True
        except:
            return False

#-----------------------------------------------------------------------------
# _calendar_to_be_refreshed
#-----------------------------------------------------------------------------
class _calendar_to_be_refreshed(object):
    """
    A CUSTOM Selenium expectation for checking whether the calendar has been
    refreshed.
    """
    def __init__(self, displayed_month, active_day):
        self.active_day = active_day
        self.displayed_month = displayed_month

    def __call__(self, driver):
        is_fresh = False

#         try:
        # Check for displayed_month changes first
        is_fresh = driver.find_element_by_class_name(
                    'datepicker-switch').text != self.displayed_month

        # If that hasn't changed...
        if not is_fresh:
            # ...see if the active day has
            is_fresh = driver.find_element_by_class_name(
                        'active').text != self.active_day
#         except:
#             is_fresh = False
        return is_fresh
