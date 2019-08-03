# <span style="font-size:larger;"><i>B</i></span>roadcastify <span style="font-size:larger;"><i>AR</i></span>chive <span style="font-size:larger;"><i>T</i></span>oolkit<br>Documentation

**Version 0.1**

## <span style="color:red">**DOCUMENTATION UNDER DEVELOPMENT**</span>

**_This project is just getting under way. A minimal level of documentation is included in the `.py` file. Stay tuned for user documentation._**

## Preface

The Broadcastify Archive Tool (BArT) automates downloading audio archives from [Broadcastify](www.broadcastify.com), "the world's largest source of Public Safety, Airline, Rail, and Marine live audio streams".

BArT was initially developed as part of a group project during a [General Assembly Data Science Immersive program](https://generalassemb.ly/education/data-science-immersive/), in response to a client's need to visualize the locations to which first responders were being dispatched during an emergency. We sought out a large repository of emergency radio dispatches to train our audio-to-text-to-geolocation algorithm.

Although Broadcastify's archive was the clear winner in terms of breadth and depth for this data, the lack of an API for downloading audio files meant that the process for acquiring the archive files highly manual and time-consuming. BArT solves that problem.

## Quick-start Guide

If you want quickly make use of BArT in your own Jupyter Notebook, this section is for you!

1. **Copy library and config files.** You'll need the source code and config initializer.
    - Put `bart.py` and `config.ini` into the directory with your `.ipynb` file<br><br>

1. **Install selenium**. Selenium is a browser emulator used to interact with Broadcastify's archive navigation tools.
    - Install with `pip install -U selenium`<br><br>
    
1. **Get a browser driver**. Selenium requires a driver to interface with your chosen browser. All testing for BArT is done with the Chrome browser driver (currently v76.0)
    - Install [Chrome's browser driver](https://sites.google.com/a/chromium.org/chromedriver/downloads), or the browser of your choice (see [the list on the selenium pyPI page](https://pypi.org/project/selenium/)
    - You must either 
      1. ensure the driver is in your computer's `PATH` (here's [a great resource for Mac users](https://www.architectryan.com/2012/10/02/add-to-the-path-on-mac-os-x-mountain-lion/#.Uydjga1dXDg) on that front) OR
      1. supply a relative path to the driver (including driver name) in `config.ini` > `[selenium_config]` > `WEBDRIVER_PATH`.<br><br>

1. **Fulfill dependencies**. Ensure you've installed and upgraded the following Python libraries:
    - `BeautifulSoup`
    - `collections`
    - `configparser`
    - `datetime`
    - `IPython.display`
    - `os`
    - `re`
    - `requests`
    - `time`

## Longer, but More Thorough, Guide

### Object Model

### Use Case Walk-throughs

## FAQ

