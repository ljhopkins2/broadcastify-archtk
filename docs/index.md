---
layout: default
title: Home
nav_order: 1
---

# The Broadcastify Archive Toolkit (broadcastify-archtk) for python  
{: .fs-9 }
Automate downloading audio archives from [Broadcastify](www.broadcastify.com), "the world's largest source of Public Safety, Airline, Rail, and Marine live audio streams".

[Get Started Now](#get-started){: .btn .btn-purple .mr-4 }[Visit Broadcastify](www.broadcastify.com){: .btn .btn-blue }

## Get Started

- **Install the [`broadcastify-archtk`](https://pypi.org/project/broadcastify-archtk/) package.**
```bash
pip install broadcastify-archtk
```

- **Get a Selenium webdriver**. [Selenium](https://pypi.org/project/selenium/) is a browser automator `broadcastify-archtk` uses to interact with Broadcastify's archive navigation tools. Selenium requires a webdriver to interface with your chosen browser.
    - All testing for `broadcastify-archtk` is done with the Chrome browser driver, so installing the [Chrome webdriver](https://sites.google.com/a/chromium.org/chromedriver/downloads) is strongly recommended. (Other webdrivers are available [on the selenium pyPI page](https://pypi.org/project/selenium/))
    - Ensure the driver is in a folder in your computer's `PATH` (here's [a great resource for Mac users](https://www.architectryan.com/2012/10/02/add-to-the-path-on-mac-os-x-mountain-lion/#.Uydjga1dXDg) on that front)


> _At this point, `broadcastify-archtk` can browse and build the list of archive entries, but it can't download the corresponding audio files._

- **Get a Broadcastify premium account.** Access to the archive audio files is behind a paywall. For $15, you can get 180 days of premium access.
    - More information at https://m.broadcastify.com/premium/
    - Make note of your username and password so the toolkit can use them to log in when finding and downloading archive audio files.


- **Take a test spin.** Give the [broadcastify-archtk demo](https://github.com/ljhopkins2/broadcastify-archtk/blob/master/broadcastify-archtk_demo.ipynb) a try.
