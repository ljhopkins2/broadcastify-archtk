---
layout: default
title: Downloading Audio Files
parent: User Guide
nav_order: 4
---

# Downloading Audio Files

The `.download()` method retrieves URIs and downloads mp3 files for the Broadcastify archive. `BroadcastifyArchive.entries` attribute.

```python
download(start=None, end=None, all_entries=False,
         output_path=None)
```

| Parameter | Data Type | Requirement | Description |
|:----------|:----------|:------------|:------------|
| `start` | datetime | See [valid date parameter combinations](#valid-date-parameter-combinations) | The earliest date & time for which to download files. Must be a valid date on the archive's calendar. |
| `end` | datetime | See [valid date parameter combinations](#valid-date-parameter-combinations) | The latest date & time for which to download files. Must be a valid date on the archive's calendar. |
| `all_entries` | bool | See [valid date parameter combinations](#valid-date-parameter-combinations) | Download all available archive files |
| `output_path` | str | Required | The absolute path to which archive entry mp3 files will be written. |

##### Valid Date Parameter Combinations

| `start` | `end` | `all_entries` | Behavior |
|:-------:|:-----:|:-----------:|----------|
| Any | Any | **Supplied** | Retrieve all files; ignore other arguments |
| **Supplied** | Omitted | Omitted | Retrieve from the earliest archive file through the file covering `end` |
| Omitted | **Supplied** | Omitted | Retrieve from the archive file containing `start` through the last archive file |
| **Supplied** | **Supplied** | Omitted | Retrieve from the file containing `start` through the file covering `end` |
| Omitted | Omitted | Omitted | Raise an error |

## Download Throttling

As of this writing, Broadcastify does not have a `robots.txt` file or any stated policy on automated access to their archives. In the spirit of good citizenship, the toolkit requests files _serially_ and waits until at least 5 seconds have elapsed since the last valid mp3 file request (_i.e._ the mp3 file in the prior request existed on the server and did not already exist in `output_path`) before making a subsequent request. So, downloads are retrieved at a rate of about **12 files per minute**.
