---
layout: default
title: Installation
parent: User Guide
nav_order: 1
---

# Installation

## Installing the Package

The `broadcastify-archtk` package is hosted on pyPI.org, so it can be installed – along with all its dependencies – using
```bash
pip install broadcastify-archtk
```

## Installing the WebDriver

The toolkit uses [Selenium](https://pypi.org/project/selenium/) to interact with Broadcastify's archive navigation page. In turn, Selenium uses the [WebDriver API](https://www.seleniumhq.org/projects/webdriver/) to interact with the browser in the same way a user would. A WebDriver is required for the toolkit to function, and it must be installed separately from the `broadcastify-archtk` package.

### Download a WebDriver

All testing for the toolkit is done with the Chrome WebDriver, so it's strongly recommended. The version of the WebDriver you download must match the version of the browser installed on your computer. (For example, if you're using Chrome version 78, you must download ChromeDriver 78.)

> Download the [Chrome WebDriver](https://sites.google.com/a/chromium.org/chromedriver/downloads)
{: .fs-5 .fw-500 }

> Other WebDrivers are available [on the selenium pyPI page](https://pypi.org/project/selenium/)
{: .fs-3 .fw-300 }


### Place it in the OS `PATH`

Once you've downloaded the WebDriver, it should be placed in a directory in the operating system `PATH`. If you're unfamiliar with environment variables, guidance is available from a variety of online sources (_i.e._ "Ask the Google"). Alternatively, an absolute path to the WebDriver file can be passed [at archive instantiation](/broadcastify-archtk/user-guide/creating-an-archive.html#instantiating-the-toolkit).


## Getting Through the Paywall

Although the toolkit can browse and build the list of archive entries without a Broadcastify account, access to find and download archive audio files is behind a paywall. For $15, you can get 180 days of premium access. Get more information and sign up at [https://m.broadcastify.com/premium/](https://m.broadcastify.com/premium/).
