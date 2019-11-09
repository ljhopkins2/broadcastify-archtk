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
import warnings as _warnings

from configparser import ConfigParser as _ConfigParser#, \
                         # ExtendedInterpolation as _ExtendedInterpolation
from time import time as _timer
from tqdm.auto import tqdm as _tqdm

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
# Constants
#-----------------------------------------------------------------------------
_MONTHS = ['','January', 'February', 'March',
      'April', 'May', 'June',
      'July', 'August', 'September',
      'October', 'November', 'December']

_FEED_URL_STEM = 'https://www.broadcastify.com/listen/feed/'
_ARCHIVE_FEED_STEM = 'https://www.broadcastify.com/archives/feed/'
_ARCHIVE_DOWNLOAD_STEM = 'https://m.broadcastify.com/archives/id/'
_LOGIN_URL = 'https://www.broadcastify.com/login/'

# Throttle times
_FILE_REQUEST_WAIT = 5
_PAGE_REQUEST_WAIT = 0.5
_DATE_NAV_WAIT = 0.1




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
                 login_cfg_path=None, show_browser_ui=False,
                 webdriver_path=None):
        """
        A container for Broadcastify feed archive data, and an engine for re-
        trieving archive entry information & downloading the corresponding mp3
        files. Populates feed name, feed & archive URLs, and start & end dates
        on initialization.

        Init Parameters
        ---------------
        feed_id : str
            The unique feed identifier the container will represent, taken from
            https://www.broadcastify.com/listen/feed/[feed_id].
        username : str
            The username for a valid Broadcastify premium account.
        password : str
            The password for a valid Broadcastify premium account. Note that
            getting the property value will return only "True" (if set) or
            "False" (if not set) to maintain confidentiality.
        login_cfg_path : str
            An absolute path to a password configuration file. Allows the user
            to keep their login information outside the script using the archive
            for privacy reasons.
        show_browser_ui : bool
            If True, scraping done during initialization and build (which use
            the Selenium webdriver) will be done with the "headless" option set
            to False, resulting in a visible browser window being open in the UI
            during scraping. Otherwise, scraping will be done "invisibly".

            Note that no browser will be shown during download, since
            requests.Session() is used, not Selenium.
        webdriver_path : str
                Optional absolute path to WebDriver if it's not located in a
                directory in the PATH environment variable


        Other Attributes & Properties
        -----------------------------
        feed_url : str
            Full https URL for the feed's main "listen" page.
        archive_url : str
            Full https URL for the feed's archive page.
        entries : dictionary
            Container for archive entry information.
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
        earliest_entry : datetime
        latest_entry   : datetime
            The datetime of the earliest/latest archive entry currently in
            `entries`.
        start_date : datetime
        end_date   : datetime
            The datetime of the earliest/latest dates on the archive's calendar.
        throttle : _RequestThrottle
            (INTERNAL USE ONLY) Throttle http requests to the Broadcastify
            servers.
        """
        self.show_browser_ui = show_browser_ui
        if webdriver_path is None:
            self.webdriver_path = 'chromedriver'
        else:
            self.webdriver_path = webdriver_path

        self._feed_id = None

        self.feed_url = _FEED_URL_STEM + feed_id
        self.archive_url = _ARCHIVE_FEED_STEM + feed_id
        self.username = username
        self.password = password
        self.entries = []
        self.earliest_entry = None
        self.latest_entry = None
        self.start_date = None
        self.end_date = None
        self.throttle = _RequestThrottle()

        # If username or password was not passed...
        if (username is None or password is None) and login_cfg_path is not None:
            # ...try to get it from the pwd.ini file
            _config = _ConfigParser()
            config_result = _config.read(login_cfg_path)

            if len(config_result) != 0:
                # Replace only if argument was not passed
                if not(username):
                    self.username = _config['authentication_data']['username']
                if not(password):
                    self.password = _config['authentication_data']['password']

        self.feed_id = feed_id
        self._get_feed_name(feed_id)

    def build(self, start=None, end=None, days_back=None, chronological=False,
              rebuild=False):
        """
        Build archive entry data for the BroadcastifyArchive's feed_id and
        populate as a dictionary to the .entries attribute.

        Parameters
        ----------
            start : datetime.date
                The earliest date for which to populate the archive. If None,
                go from the earliest date on the calendar (inclusive).
            end : datetime.date
                The latest date for which to populate the archive. If None,
                go to the latest date on the calendar (inclusive).
            days_back : int
                The number of days before the current day to retrieve informa-
                tion for. A value of `0` retrieves only archive entries corres-
                ponding to the current day. Pass either days_back OR a valid
                combination of start/end dates.
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
                             f' this BroadcastifyArchive. To erase and rebuild,'
                             f' specify `rebuild=True` when calling .build()')

        # Make sure valid arguments were passed
        ## Either start/end or days_back; not both
        if (start or end) and days_back:
            raise ValueError(f'Expected either `days_back` OR a `start`/`end` '
                             f'combination. Both were passed.')

        ## `days_back` must be a non-negative integer
        if days_back is not None:
            bad_days_back = False
            try:
                if days_back < 0:
                    bad_days_back = True
            except:
                bad_days_back = True

            if bad_days_back:
                raise TypeError(f'`days_back` must be a non-negative integer.')

            # Capture the archive end date to count back from
            end = self.end_date

            # Make sure days_back is no larger than the archive date range size
            start = self.start_date
            archive_size = (end - start).days
            if days_back > archive_size:
                _warnings.warn(f"The number of days_back passed ({days_back}) "
                               f"exceeds the size of the archive's date range ("
                               f"{archive_size}). Only valid dates will be "
                               f"built.")
                days_back = archive_size

        else:
            ## Check that `start` and `end` within archive's start/end dates
            ## If they weren't passed, set them to the archive's start/end dates
            out_of_range = ''

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

            ## `start` cannot be > `end`
            if start > end:
                raise AttributeError(f'`start` date ({start}) cannot be after '
                                     f'`end` date ({end}).')

            # Get size of the date range
            days_back = (end - start).days

        # Adjust for exclusive end of range()
        days_back += 1

        # Build the list of dates to scrape
        date_list = sorted([end - _dt.timedelta(days=x)
                           for x in range(days_back)],
                           reverse=not(chronological))

        archive_entries = []

        # Spin up a browser and an ArchiveCalendar
        # Set whether to show browser UI while fetching
        print('Launching webdriver...')
        options = _Options()
        if not self.show_browser_ui:
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')

        with _webdriver.Chrome(executable_path=self.webdriver_path,
                               chrome_options=options) as browser:
            browser.get(self.archive_url)
            self.arch_cal = ArchiveCalendar(self, browser)

            # Get archive entries for each date in list
            t = _tqdm(date_list, desc=f'Building dates', leave=True,
                      dynamic_ncols=True)
            for date in t:
                t.set_description(f'Building {date}', refresh=True)
                self.arch_cal.go_to_date(date)

                if self.arch_cal.entries_for_date:
                    archive_entries.extend(self.arch_cal.entries_for_date)

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

        self.earliest_entry = min([entry['end_time']
                                   for entry in self.entries]).date()
        self.latest_entry = max([entry['end_time']
                                 for entry in self.entries]).date()

        print(self)

    def download(self, start=None, end=None, all_entries=False,
             output_path=None):
        """
        Retrieve URIs and downloads mp3 files for the Broadcastify archive.

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
            The absolute path to which archive entry mp3 files will be written.
        """
        # Make sure arguments were passed in a valid combination
        if not all_entries:
            if all([not(start), not(end)]):
                raise ValueError(f'One of `start` or `end` dates must be '
                                   f'supplied, or all_entries must be set to '
                                   f'True.')

        # Make sure start and end are either None or a datetime
        if not((isinstance(start, _dt.datetime) or start is None) and (
            isinstance(end, _dt.datetime) or end is None)):
            raise TypeError(f'`start` and `end` must be of type `datetime`.')

        # Make sure an output_path was given
        if output_path == '':
            raise TypeError(f'No output path was given. Supply one as an '
                            f'argument or in the initialization file.')

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
                               password=self.__password)

        # Pass them to _DownloadNavigator to get the files
        dn.get_archive_mp3s(filtered_entries, output_path)

    def _get_archive_dates(self):
        # Initialize calendar navigation
        print(f'Initializing calendar navigation for {self.feed_name}...')

        # Set whether to show browser UI while fetching
        options = _Options()
        if not self.show_browser_ui:
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')

        # Launch Chrome
        with _webdriver.Chrome(executable_path=self.webdriver_path,
                               chrome_options=options) as browser:
            browser.get(self.archive_url)
            self.archive_calendar = ArchiveCalendar(self, browser,
                                                    get_dates=True)
            self.start_date = self.archive_calendar.start_date
            self.end_date = self.archive_calendar.end_date

        self.archive_calendar = None

        print('Initialization complete.\n')
        print(self)

    def _get_feed_name(self, feed_id):
        s = _requests.Session()
        with s:
            r = s.get(_FEED_URL_STEM + feed_id)
            if r.status_code != 200:
                raise ConnectionError(f'Problem connecting while getting feed name: '
                                      f' {r.status_code}')

            soup = _BeautifulSoup(r.text, 'lxml')
            try:
                feed_name = soup.find('span', attrs={'class':'px13'}).text
            except AttributeError:
                raise NavigatorException(f'Invalid feed_id ({feed_id}).')

            self.feed_name = feed_name

    @property
    def feed_id(self):
        # Unique ID for the Broadcastify feed. Taken from
        # https://www.broadcastify.com/listen/feed/[feed_id]
        return self._feed_id
    @feed_id.setter
    def feed_id(self, value):
        # Changing the feed_id re-initializes the object's other properties
        if value != self._feed_id:
            self._feed_id = value
            self._get_feed_name(value)
            self.feed_url = _FEED_URL_STEM + value
            self.archive_url = _ARCHIVE_FEED_STEM + value
            self.earliest_entry = None
            self.latest_entry = None
            self.start_date = None
            self.end_date = None
            self.entries = []
            self.earliest_entry = None
            self.latest_entry = None

            self._get_archive_dates()
        else:
            print('New Feed ID same as old Feed ID.')
            print(self)

    @property
    def password(self):
        # Password for Broadcastify premium account. Getting the property
        # will return a Boolean indicating whether the password has been set.
        if self.__password:
            return True
        else:
            return False
    @password.setter
    def password(self, value):
        self.__password = value

    def __repr__(self):
        repr = f'BroadcastifyArchive\n' + \
               f' (Feed ID = {self.feed_id}\n' + \
               f'  Feed Name = {self.feed_name}\n' + \
               f'  Feed URL = "{self.feed_url}"\n' + \
               f'  Archive URL = "{self.archive_url}"\n' + \
               f'  Start Date: {str(self.start_date)}\n' + \
               f'  End Date:   {str(self.end_date)}\n' + \
               f'  Username = "{self.username}" Password = [{self.password}]\n' + \
               f"  {'{:,}'.format(len(self.entries))} built archive entries "

        if not(self.earliest_entry is None and self.latest_entry is None):
            if self.earliest_entry == self.latest_entry:
                repr += f'on {self.earliest_entry}'
            else:
                repr += f'between {self.earliest_entry} and {self.latest_entry}'

        return repr





#-----------------------------------------------------------------------------
#-----------------------------------------------------------------------------
#
#
#
# ArchiveDownloader
#-----------------------------------------------------------------------------
class ArchiveDownloader:
    def __init__(self, parent, login=False, username=None, password=None):
        self._parent = parent

        self.download_page_soup = None
        self.current_archive_id = None
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

            self._login_credentials_present(username, password)

            self._parent.throttle.throttle('page')
            r = s.post(_LOGIN_URL, data=login_data)

            if r.status_code != 200:
                raise ConnectionError(f'Encountered a problem connecting '
                                      f'during ArchiveDownloader initialization:'
                                      f' code = {r.status_code}, login = {l}')
            # Check successful login
            soup = _BeautifulSoup(r.text, 'lxml')

            if soup(text='Log in Failed!'):
                raise NavigatorException(f'Login credentials rejected by the '
                                         f'server.')

    def get_download_soup(self, archive_id):
        self.current_archive_id = archive_id
        s = self.session

        self._parent.throttle.throttle()
        r = s.get(_ARCHIVE_DOWNLOAD_STEM + archive_id)
        if r.status_code != 200:
            raise ConnectionError(f'Problem connecting while getting soup from '
                    f'{_ARCHIVE_DOWNLOAD_STEM + archive_id}: {r.status_code}')

        self.download_page_soup = _BeautifulSoup(r.text, 'lxml')

        return self.download_page_soup

    def get_archive_mp3s(self, archive_entries, filepath):
        start = _timer()
        earliest_download = min([entry['start_time']
                                 for entry in archive_entries]
                                 ).strftime('%m-%d-%y %H:%M')
        latest_download = max([entry['start_time']
                            for entry in archive_entries]
                            ).strftime('%m-%d-%y %H:%M')

        t = _tqdm(archive_entries, desc='Overall progress',
                  leave=True, dynamic_ncols=True)

        t.write(f'Downloading {earliest_download} to {latest_download}')
        t.write(f'Storing at {filepath}.')

        for file in t:
            feed_id =  self._parent.feed_id
            archive_uri = file['uri']
            file_date = self._format_entry_date(file['end_time'])

            # Build the path for saving the downloaded .mp3
            out_file_name = filepath + '-'.join([feed_id, file_date]) + '.mp3'

            # Get the URL of the mp3 file
            mp3_soup = self.get_download_soup(archive_uri)
            file_url = self._parse_mp3_path(mp3_soup)

            self._fetch_mp3([out_file_name, file_url], t)

    def _parse_mp3_path(self, download_page_soup):
        try:
            return download_page_soup.find('a',
                                           {'href': _re.compile('.mp3')}
                                           ).attrs['href']
        except AttributeError:
            if download_page_soup.find('div', {'class': 'alert-warning'}):
                raise NavigatorException(f'Premium subscription required.')

    def _fetch_mp3(self, entry, main_progress_bar):
        path, url = entry
        file_name = url.split('/')[-1]

        if not _os.path.exists(path):
            self._parent.throttle.throttle('file')

            r = _requests.get(url, stream=True)
            file_size = int(r.headers['Content-Length'])

            t = _tqdm(total=file_size,
                      desc=f'Downloading {file_name}', dynamic_ncols=True)

            if r.status_code == 200:
                self._parent.throttle.got_last_file = True
                with open(path, 'wb') as f:
                    for chunk in r:
                        f.write(chunk)
                        t.update(len(chunk))
            elif r.status_code == 403:
                t.write(f'\tReceived 403 on {file_name}. Archive file does not '
                        f' exist. Skipping.')
            else:
                t.write(f'\tCould not retrieve {url} (code {r.status_code}'
                      f'). Skipping.')
        else:
            main_progress_bar.write(f'\t{file_name} already exists. Skipping.')

    def _format_entry_date(self, date):
        # Format the ArchiveEntry end time as YYYYMMDD-HHMM
        year = date.year
        month = date.month
        day = date.day
        hour = date.hour
        minute = date.minute

        return '-'.join([str(year) + str(month).zfill(2) + str(day).zfill(2),
                         str(hour).zfill(2) + str(minute).zfill(2)])

    def _login_credentials_present(self, username, password):
        if not username or not password:
            raise NavigatorException(
                f"Login credentials were not supplied or are incomplete: "
                f"username={self._parent.username}; "
                f"password_supplied={self._parent.password}")
        else:
            return True

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
        self._parent = parent
        self._browser = browser
        self.active_date = None

        ## Wait for calendar to load on navigation page
        element = _WebDriverWait(self._browser, 10).until(
                                 _EC.presence_of_element_located((
                                 _By.CLASS_NAME, 'datepicker-switch')))

        # Initialize object attributes
        self._scrape_contents()        # Initializes _contents
        self._parse_calendar_attrs()   # Initializes _calendar, displayed_month,
                                       # & active_date
        if not(self.active_date):
            # When the calendar initially loaded, no active_date was displayed.
            # This means the archive is no longer available.
            raise NavigatorException(
                f'Archive at {self._parent.archive_url} is no longer available '
                f'(no active date appears when loading the calendar).')

        if get_dates:
            self.end_date = self.active_date
            self._get_start_date()     # Initializes start_date
        else:
            self.end_date = self._parent.end_date
            self.start_date = self._parent.start_date

        self._att = ArchiveTimesTable(self, browser)

    def update(self):
        self._wait_for_refresh()
        self._scrape_contents()
        self._parse_calendar_attrs()

    def go_to_date(self, date):
        ### Navigate to & click on a date in the archive calendar; the clicked-
        ### on date becomes the new active_date, which is returned

        # If date is "today" or equal to end_date, take the shortcut
        if date == 'today':
            date = self.end_date

        if date == self.end_date:
            try:
                self._parent.throttle.throttle('date_nav')
                self._browser.find_element_by_class_name('today').click()
                # Check that we need to wait for a refresh
                if (self.active_date.month != self._displayed_month_dt.month
                  ) or (self.active_date.year != self._displayed_month_dt.year):
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
        months_to_traverse = self._diff_month(self.active_date, date)

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
        self._parent.throttle.throttle('date_nav')
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

        return self._displayed_month_dt

    def _diff_month(self, d1, d2):
        return (d2.year - d1.year) * 12 + d2.month - d1.month

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
            self._parent.throttle.throttle('date_nav')
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
        self._parent = parent
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
            # Look for "No archives available" (dataTables_empty)
            if row.find_all('td', {'class': 'dataTables_empty'}):
                # Stop looking for entries
                break

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
            _first_uri_xpath = "//a[contains(@href,'/archives/download/')]"

            # ...wait until the first entry URI is different
            element = _WebDriverWait(self._browser, 5).until_not(
                            _text_to_be_present_in_href((
                                _By.XPATH, _first_uri_xpath),
                                self.current_first_uri))
        else:
            # ...otherwise wait until ATT data has been refreshed
            element = _WebDriverWait(self._browser, 5).until_not(
                            _att_to_be_updated((self.last_refresh)))

    def _get_entry_datetimes(self, times):
        # Convert the archive entry start & end times from a list of strings
        # to a tuple of datetimes

        # Set date component to the date currently displayed
        date = self._parent.active_date

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
# NavigatorException
#-----------------------------------------------------------------------------
class NavigatorException(Exception):
    pass



#-----------------------------------------------------------------------------
# _RequestThrottle
#-----------------------------------------------------------------------------
class _RequestThrottle:
    # Limits the pace with which requests are sent to Broadcastify's servers.

    def __init__(self):
        self.last_file_req = _timer()
        self.last_page_req = _timer()
        self.got_last_file = False

    def throttle(self, type='page', wait=None):
        """
        Throttle various types of requests to Broadcastify. Valid types are:
            - 'page': throttle html requests
            - 'file': throttle mp3 downloads
            - 'date_nav': throttle clicks on elements of the ArchiveCalendar
        """
        duration = wait

        if type == 'page':
            duration = _PAGE_REQUEST_WAIT
            self._wait(duration)
        elif type == 'file':
            if self.got_last_file == True:
                duration = _FILE_REQUEST_WAIT
                self.got_last_file = False
            else:
                duration = _PAGE_REQUEST_WAIT
            self._wait(duration)
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

        try:
            # Check for displayed_month changes first
            is_fresh = driver.find_element_by_class_name(
                        'datepicker-switch').text != self.displayed_month

            # If that hasn't changed...
            if not is_fresh:
                # ...see if the active day has
                is_fresh = driver.find_element_by_class_name(
                            'active').text != self.active_day
        except:
            is_fresh = False

        return is_fresh
