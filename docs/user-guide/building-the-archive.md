---
layout: default
title: Building the Archive
parent: User Guide
nav_order: 3
---

# Building the Archive

The `.build()` method retrieves archive entry data for the archive and populates it as a dictionary to the `BroadcastifyArchive.entries` attribute.

```python
build(start=None, end=None, days_back=None,
      chronological=False, rebuild=False)
```

| Parameter | Data Type | Requirement | Description |
|:----------|:----------|:------------|:------------|
| `start` | date | See [valid date parameter combinations](#valid-date-parameter-combinations) | The earliest date for which to populate the archive. Must be a valid date on the archive's calendar. |
| `end` | date | See [valid date parameter combinations](#valid-date-parameter-combinations) | The latest date for which to populate the archive. Must be a valid date on the archive's calendar. |
| `days_back` | int | See [valid date parameter combinations](#valid-date-parameter-combinations) | The number of days before the current day to retrieve information for. |
| `chronological` | bool | Optional | By default, start with the latest date and work backward in time. If True, reverse that. |
| `rebuild` | bool | Optional<super>*</super> | Specifies that existing data in the `entries` attribute should be overwritten with data newly fetched from Broadcastify. If the `entries` attribute is not empty, this parameter must be set to `True` or an error will be raised. |

##### Valid Date Parameter Combinations
| `start` | `end` | `days_back` | Behavior |
|---------|-------|-------------|----------|
| **Supplied** | Omitted | Omitted | Build entry list from `start` through the last date in the archive calendar, inclusive |
| Omitted | **Supplied** | Omitted | Build entry list from first date in the archive calendar through `end`, inclusive |
| **Supplied** | **Supplied** | Omitted | Build entry list from `start` through `end`, inclusive |
| Omitted | Omitted | **Supplied** | Build entry list from today's date going `days_back` into the past. (Zero days back includes only the current day.) |

All other combinations produce an error.
{: .fs-2 .lh-0 }
