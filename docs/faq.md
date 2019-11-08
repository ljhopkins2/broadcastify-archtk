---
layout: default
title: FAQ
nav_order: 4
---

# Frequently Asked Questions

## What do I do if I: found a bug? am getting an error? have a suggestion?

Please search through [the existing issue list](https://github.com/ljhopkins2/broadcastify-archtk/issues) to look for resolutions (or vote up an existing unresolved issue), and submit a new issue if necessary.

# What does the `WebDriverException` mean?

```python
WebDriverException: Message: 'chromedriver' executable needs to be in PATH.
```

This error message means that the WebDriver for your browser is not in your operating system's `PATH` environment variable, so Selenium can't find a driver to use for scraping. The easiest solution is to specify the path to the WebDriver in the `webdriver_path` argument when [instantiating](/user-guide/creating-an-archive.html) a `BroadcastifyArchive` object. A cleaner solution is to [move the driver](/user-guide/installation.html#place-it-in-the-os-path) into a directory in the `PATH`.
