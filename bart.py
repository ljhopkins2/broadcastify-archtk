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
from selenium.common.exceptions import NoSuchElementException as _NSEE

#-----------------------------------------------------------------------------
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

# Selenium config
_WEBDRIVER_PATH = _config.get('selenium_config',
                              'WEBDRIVER_PATH',
                              fallback=None)

if _WEBDRIVER_PATH == '':
    _WEBDRIVER_PATH = None

# Output path
_MP3_OUT_PATH = _config['output_path']['MP3_OUT_PATH']

# Authentication data
_AUTH_DATA_PATH = _config['authentication_path']['AUTH_DATA_PATH']


#-----------------------------------------------------------------------------
# Variables
#-----------------------------------------------------------------------------
_first_uri_in_att_xpath = "//a[contains(@href,'/archives/download/')]"


#-----------------------------------------------------------------------------
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
# CLASSES
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
    A CUSTOM Selenium expectation for checking whether the ArchiveTimesTable has
    been updated.
    """
    def __init__(self, archive_navigator):
        self.an = archive_navigator
        self.page_last_updated = self.an.page_last_updated

    def __call__(self, driver):
        try:
            return self.page_last_updated != self.an._set_last_page_update()
        except:
            return False

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
    Limits the pace with which requests are sent to Broadcastify's servers
    """
    def __init__(self):
        self.last_file_req = _timer()
        self.last_page_req = _timer()

    def throttle(self, type='page', wait=None):
        if wait:
            start = _timer()
            while not _timer() - start >= wait:
                pass
            return None

        if type == 'page':
            while not _timer() - self.last_page_req >= _PAGE_REQUEST_WAIT:
                pass
            self.last_page_req = _timer()
        else:
            while not _timer() - self.last_file_req >= _FILE_REQUEST_WAIT:
                pass
            self.last_file_req = _timer()

#-----------------------------------------------------------------------------
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

        # Instantiate the _ArchiveNavigator
        if self._verbose:
            print(f'Initializing archive navigation...')

        self._an = _ArchiveNavigator(self.archive_url,
                                    self._verbose,
                                    show_browser_ui=self.show_browser_ui)

        self._an.get_archive_start()

        self.start_date = self._an.archive_start_date
        self.end_date = self._an.archive_end_date

        if self._verbose:
            print('Initialization complete.\n')
            print(self)

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
        if not days_back:
            # Bookend `start` and `end` with the archive's start & end dates
            if start:
                start = max(start, self.start_date)
            else:
                start = self.start_date
            if end:
                end = min(end, self.end_date)
            else:
                end = self.end_date

            # Get the size of the date range
            days_back = (end - start).days

        ## `start` cannot be > `end`
        if start > end:
            raise AttributeError(f'`start` date cannot be after `end` date.')

        # Adjust for the exclusive end of range()
        days_back += 1

        date_list = sorted([end - _dt.timedelta(days=x) for x in range(days_back)],
                           reverse=not(chronological))

        archive_entries = []

        # Navigate to, scrape, and parse archive entries for each date in list
        for i, date in enumerate(date_list):
            _clear_output(wait=True)
            if self._verbose: print(f'Parsing archive entry for {date} '
                                    f'({i + 1} of {len(date_list)})')

            self._an.navigate_to_date(date)

            if not(self._an.no_att_data):
                archive_entries.extend(self.__parse_att(self._an.att_soup))

        self._an.close_browser()

        if self._verbose: print('Processing archive entries...')

        # Empty & replace the current archive entries
        self.entries = []

        # Store URIs and end times in the entries attritbute
        for entry in archive_entries:
            entry_dict = {
                'feed_id': self.feed_id,
                'uri': entry[0],
                'end_time': entry[2],
                'start_time': entry[1]
            }

            self.entries.append(entry_dict)

        _clear_output(wait=True)

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
        start       : datetime.datetime
            The earliest date & time for which to download files
        end         : datetime.datetime
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


        output_path : str (optional)
            The local path to which archive entry mp3 files will be written. The
            path must exist before calling the method. Defaults to the value
            supplied in config.ini's _MP3_OUT_PATH.
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
        dn = _DownloadNavigator(login=True,
                                username=self.username,
                                password=self._password,
                                verbose=self._verbose)

        if self._verbose:
            print(f'{len(filtered_entries)} archive entries matched.')

        # Pass them to _DownloadNavigator to get the files
        dn.get_archive_mp3s(filtered_entries, output_path)

    def __parse_att(self, att_soup):
        """
        Generates Broadcastify archive file information from the `archiveTimes`
        table ("ATT") on a feed's archive page. Returns a list of lists
        containing three elements:
            - The URI for the file, which can be used to find the file's
              individual download page
            - Start and end date/time of the transmission as datetime objects

        Parameters
        ----------
        att_soup : bs4.BeautifulSoup
            A BeautifulSoup object containing the ATT source code, obtained
            from _ArchiveNavigator.att_soup
        """

        # Set up a blank list to return
        att_entries = []

        # Loop through all rows of the table
        for row in att_soup.find_all('tr'):
            # Grab the start & end times from the row's <td> tags
            file_start, file_end = self.__get_entry_datetime(
                                    [(each.text) for each
                                     in row.find_all('td')])

            # Grab the file ID
            file_uri = row.find('a')['href'].split('/')[-1]

            # Put the file date/time and URL leaf (as a list) into the list
            att_entries.append([file_uri,
                                file_start,
                                file_end])

        return att_entries

    def __get_entry_datetime(self, time):
        """
        Convert the archive entry start & end times from a list of strings
        to a tuple of datetimes
        """
        # Set date component to the date currently displayed
        date = self._an.active_date

        # Get time objects from the HH:MM AM/PM text
        hhmm_start, hhmm_end = [ _dt.datetime.strptime(each, '%I:%M %p').time()
                                for each in time]

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
        repr = f'BroadcastifyArchive\n' + \
               f' (Feed ID = {self.feed_id}\n' + \
               f'  Feed Name = {self.feed_name}\n' + \
               f'  Feed URL = "{self.feed_url}"\n' + \
               f'  Archive URL = "{self.archive_url}"\n' + \
               f'  Start Date: {str(self.start_date)}\n' + \
               f'  End Date:   {str(self.end_date)}\n' + \
               f'  Username = "{self.username}" Password = [{self.password}]\n' + \
               f"  {'{:,}'.format(len(self.entries))} parsed archive entries "

        if not (self.earliest_entry and self.latest_entry):
            repr += f'between {self.earliest_entry} and {self.latest_entry}'

        repr += f'\n  Verbose = {self._verbose})'

        return repr

#-----------------------------------------------------------------------------
# _ArchiveNavigator
#-----------------------------------------------------------------------------
class _ArchiveNavigator:
    def __init__(self, url, verbose, show_browser_ui=False):
        """
        Utility for navigating the archive feed.

        Parameters
        ----------
        url : str
            Full https URL for the feed's archive page.
        verbose : bool
            If True, the system will generate more verbose output during longer
            operations.
        """

        self.url = url
        self.calendar_soup = None
        self.att_soup = None
        self.browser = None
        self.show_browser_ui = show_browser_ui
        self.verbose = verbose

        self.active_date = None # currently displayed date
        self.month_max_date = None # latest day w/ entries in displayed month
        self.month_min_date = None # earliest day w/ entries in displayed month

        self.current_first_uri = None
        self.no_att_data = False
        self.page_last_updated = None

        self.throttle = _RequestThrottle()

        # Get initial page scrape & parse the calendar
        self.open_browser()
        self.__load_nav_page()
        self.__scrape_nav_page(wait=False)
        self.__parse_calendar()

        self.archive_end_date = self.active_date

        self.archive_start_date = self.month_min_date

    def get_archive_start(self):
        if self.verbose:
            print(f'\tLooking for archive start date...')

        prev_button = self.calendar_soup.find('th',
                                    attrs={'class': 'prev',
                                           'style': 'visibility: visible;'})

        while prev_button:
            # Click to go to the prior month
            self.__check_browser()
            self.throttle.throttle()
            self.browser.find_element_by_class_name('prev').click()

            # Scrape and parse the new month
            self.__scrape_nav_page(wait=False)
            self.__parse_calendar()

            # Set the archive_start_date to the earliest valid day in the
            # displayed month
            self.archive_start_date = self.month_min_date

            # Get the button to display the previous month; if there isn't one,
            # we're done and the loop will terminate
            prev_button = self.calendar_soup.find('th',
                                        attrs={'class': 'prev',
                                               'style': 'visibility: visible;'})

        if self.verbose:
            print(f'\tFound start date at {self.archive_start_date}.')

        self.navigate_to_date(date=self.archive_end_date,
                              from_date=self.archive_start_date,
                              navigate_only=True)

    def navigate_to_date(self, date, from_date=None, navigate_only=False):
        # Check that the date is valid (between start & end dates)
        if not (self.archive_start_date <= date <= self.archive_end_date):
            raise ValueError(
                    '`date` argument must be between start and end dates')
        # Set blank from dates to the active_day
        if not from_date:
            from_date = self.active_date

        # Get the day
        new_day = date.day

        # Traverse the months, if necessary
        months_to_traverse = _diff_month(from_date, date)
        if months_to_traverse >= 0:
            step_direction = 1
            button_name = 'next'
        else:
            step_direction = -1
            button_name = 'prev'
        for _ in range(0, months_to_traverse, step_direction):
            self.__check_browser()
            self.throttle.throttle(wait=0.1)
            self.browser.find_element_by_class_name(button_name).click()

        # Click the date, if appropriate
        if not(navigate_only):
            self.__check_browser()
            self.throttle.throttle()

            try:
                self.browser.find_element_by_xpath(f"//td[@class='day' "
                                        f"and contains(text(), '{new_day}')]").click()
            except:
                self.browser.find_element_by_xpath(f"//td[@class='active day' "
                                        f"and contains(text(), '{new_day}')]").click()
            finally:
                self._set_last_page_update()

            if date != self.active_date:
                self.__scrape_nav_page()
                self.__parse_calendar()


    def __load_nav_page(self):
        if self.verbose: print('\tLoading navigation page...')
        self.__check_browser()

        # Browse to feed archive page
        self.browser.get(self.url)

        # Wait for page to render
        element = _WebDriverWait(self.browser, 10).until(
                  _EC.presence_of_element_located((_By.CLASS_NAME,
                                                   "cursor-link")))

        # Set up MutationObserver to handle consecutive dates with no data
        self.browser.execute_script(
            """
              new MutationObserver(() => {
                window.lastRefresh = new Date()
              }).observe(document.querySelector("table.table.table-striped.table-bordered.hover.dataTable.no-footer"), {
              attributes: true, childList: true, subtree: true } )
            """
            )

        # Get the timestamp of the last page updated
        self._set_last_page_update()

    def __scrape_nav_page(self, wait=True):
        self.__check_browser()

        # Wait for page to render
        if wait and self.current_first_uri:
            if self.current_first_uri != _NO_ATT_DATA:
                element = _WebDriverWait(self.browser, 10).until_not(
                                _text_to_be_present_in_href((
                                    _By.XPATH, _first_uri_in_att_xpath),
                                    self.current_first_uri))
            else:
                element = _WebDriverWait(self.browser, 10).until_not(
                                _att_to_be_updated((self)))

        # Scrape page content
        soup = _BeautifulSoup(self.browser.page_source, 'lxml')

        # Isolate the calendar and the archiveTimes table
        self.calendar_soup = soup.find('table',
                                       {'class': 'table-condensed'})
        self.att_soup = soup.find('table',
                                  attrs={'id': 'archiveTimes'}
                                  ).find('tbody')

        self.current_first_uri = self.__get_current_first_uri()


    def __parse_calendar(self):
        """
        Uses a bs4 ResultSet of the <td> tags representing days currently dis-
        played on the calendar to set calendarattributes. Items have the format
        of `<td class="[class]">[D]</td>` where
         - [D] is the one- or two-digit day (as a string) and
         - [class] is one of
             "old day"          = a day with archives but in a prior month
                                  (clicking will refresh the calendar)
             "day"              = a past day in the current month
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
        days_on_calendar = self.calendar_soup.find_all('td')

        # Get the month & year currently displayed
        month, year = self.calendar_soup.find('th',
                                              {'class': 'datepicker-switch'}
                                              ).text.split(' ')

        displayed_month = _MONTHS.index(month)
        displayed_year = int(year)

        # Parse the various calendar attributes
        try:
            active_day = int([day.text for day in days_on_calendar
                               if (day['class'][0] == 'active')][0])
        except:
            active_day = None

        month_max_day = int([day.text for day in days_on_calendar
                              if (day['class'][0] == 'day') or
                                 (day['class'][0] == 'active')][::-1][0])

        month_min_day = int(self.__parse_month_min_day(days_on_calendar))

        # Set class attributes
        # If the active day is on the displayed month, reset the attribute;
        # otherwise, leave it alone.
        if active_day:
            self.active_date = _dt.date(displayed_year,
                                    displayed_month,
                                    active_day)

        self.month_min_date = _dt.date(displayed_year,
                                   displayed_month,
                                   month_min_day)

        self.month_max_date = _dt.date(displayed_year,
                                   displayed_month,
                                   month_max_day)

    def __parse_month_min_day(self, days_on_calendar):
        """Parse the lowest valid day in the displayed month"""
        disabled_found = False
        for day in days_on_calendar:
            if day['class'][0] == 'disabled':
                disabled_found = True
            elif day['class'][0] in 'day active'.split():
                return day.text
            elif day['class'][0] != 'old' and disabled_found:
                return day.text

        return None

    def __get_current_first_uri(self):
        try:
            uri = self.browser.find_element_by_xpath(_first_uri_in_att_xpath
                    ).get_attribute('href').split('/')[-1]
            self.no_att_data = False
            return uri
        except _NSEE:
            self.no_att_data = True
            return _NO_ATT_DATA

    def _set_last_page_update(self):
        # Get the last update from the browser; may be None
        last_update = self.browser.execute_script('return window.lastRefresh')

        if last_update:
            # Convert to a datetime
            last_update = _dt.datetime.strptime(last_update,
                                             '%Y-%m-%dT%H:%M:%S.%fZ')

        self.page_last_updated = last_update

        return last_update

    def open_browser(self):
        if self.verbose: print('\tOpening browser...')

        # Set whether to show browser UI while fetching
        options = _Options()
        if not self.show_browser_ui:
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')

        # Launch Chrome
        self.browser = _webdriver.Chrome(chrome_options=options)

    def close_browser(self):
        if self.verbose: print('Closing browser...')
        self.browser.quit()

    def __check_browser(self):
        if not self.browser:
            raise _NavigatorException(f"Please open a browser. And do please "
                                      f"remember to close it when you're done.")

    def __repr__(self):
        return(f'_ArchiveNavigator(URL: {self.url}, '
               f'Currently Displayed: {str(self.active_date)}, '
               f'Start Date:\t{str(self.archive_start_date)}, '
               f'End Date:\t{str(self.archive_end_date)}')

#-----------------------------------------------------------------------------
# _DownloadNavigator
#-----------------------------------------------------------------------------
class _DownloadNavigator:
    def __init__(self, login=False, username=None, password=None,
                 verbose=False):
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

            t.throttle()
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
            feed_id =  file['feed_id']
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
