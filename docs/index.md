---
layout: default
title: Home
nav_order: 1
---

# The Broadcastify Archive Toolkit for python  
{: .fs-9 }

Automate downloading audio archives from Broadcastify, the world's largest source of Public Safety, Airline, Rail, and Marine live audio streams.
{: .fs-6 .fw-300 }

[Get Started Now](#get-started){: .btn .btn-purple .mr-4 }[Visit Broadcastify](http://www.broadcastify.com){: .btn .btn-blue }

_This toolkit is not officially affiliated with Broadcastify or Radio Reference._
{: .fs-1 .lh-0 }

----

## Get Started

- **Install the [`broadcastify-archtk`](https://pypi.org/project/broadcastify-archtk/) package.** It's hosted on pyPI.org, so you can use `pip`.
```bash
pip install broadcastify-archtk
```
<br>
- **Get a Selenium webdriver**. [Selenium](https://pypi.org/project/selenium/) is a browser automator the toolkit uses to interact with Broadcastify's archive navigation page. You'll need to download the webdriver for your chosen browser.
    - All testing for the toolkit is done with the [Chrome webdriver](https://sites.google.com/a/chromium.org/chromedriver/downloads), so it's strongly recommended. (Other webdrivers are available [on the selenium pyPI page](https://pypi.org/project/selenium/))
    - Ensure the driver is in a folder in your operating system 's `PATH` (here's [a great resource for Mac users](https://www.architectryan.com/2012/10/02/add-to-the-path-on-mac-os-x-mountain-lion/#.Uydjga1dXDg) on that front)

<br>

- **Get a Broadcastify premium account.** Although the toolkit can browse and build the list of archive entries without one, access to find and download archive audio files is behind a paywall. For $15, you can get 180 days of premium access.
    - More information at [https://m.broadcastify.com/premium/](https://m.broadcastify.com/premium/)
    - Make note of your username and password so the toolkit can use them to log in

<br>


- **Take a test spin.** Give the [`broadcastify-archtk` demo](https://github.com/ljhopkins2/broadcastify-archtk/blob/master/broadcastify-archtk_demo.ipynb) a try in a Jupyter notebook.
