---
layout: default
title: Creating an Archive
parent: User Guide
nav_order: 2
---

# Creating an Archive

## Importing the package

All the needed Classes for the toolkit are contained in `broadcastify-archtk.archive`:
```python
import broadcastify_archtk.archive as btk
```

## Instantiating the toolkit

The toolkit's capabilities are exposed via the `broadcastify-archtk.archive.BroadcastifyArchive` Class.

```python
BroadcastifyArchive(feed_id=None,
                    username=None, password=None, login_cfg_path=None,
                    show_browser_ui=False)
```

| Parameter | Data Type | Requirement | Description |
|:----------|:----------|:------------|:------------|
| `feed_id` | str | Required | The unique feed identifier for the Broadcastify feed represented by the object, taken from www.broadcastify.com/listen/feed/[feed_id].|
| `username` | str | Optional | The username for a valid Broadcastify account. In order to download, the account must be a [premium account](https://m.broadcastify.com/premium/). Optional at instantiation, but must be set before downloading audio files. |
| `password` | str | Optional | The password for the account referenced by `username`. Subject to the same requirement timings as `username`.|
| `login_cfg_path` | str | Optional | Absolute path to [a config file](#password-configuration-files) containing the username and password information. Allows the user to maintain the privacy of their account information by by keeping it outside the code using the toolkit. |
| `show_browser_ui` | str | Optional | If True, scraping done during initialization and build will be done with the Selenium webdriver "headless" option set to False, resulting in a visible browser window being open in the UI during scraping. Otherwise, scraping will be done "invisibly".  Note that no browser will be shown during download, since requests.Session() is used rather than Selenium.|

Usage:
```python
my_archive = btk.BroadcastifyArchive(feed_id='4288')
```

## Password Configuration Files

If you do not wish to expose your Broadcastify login information in your code, you can instead store it in a configuration file. The file should have a `.ini` or `.cfg` extension. You may pass the absolute path to this file in the `login_cfg_path` parameter when instantiating a `BroadcastifyArchive` object. The file must use the following template:

```
[authentication_data]
username:
password:
```

**Tips:**
- Leave a space between the colon and your login parameter
- Do not enclose the login information in quotes
- If you need to include notes in the file, use a `#` to indicate a comment
- For example:
  ```
  [authentication_data]
  username: johndoe88
  password: @nonymou$1
  ```
- If you're using GitHub for your project, and to avoid public exposure of your login information, ensure the password file is either in your `.gitignore` file or in a directory that's not part of the repository
