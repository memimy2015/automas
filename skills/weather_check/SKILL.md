---
name: weather-check
description: Supports weather lookup
---

# weather-check

## Instructions
Query the weather by entering a region and a date, The value of the "region" field shall be selected from [北方,中部,南方]. The date format as yyyyMMdd.
1. Determine which region of China a city belongs to based on its name
2. Call the script to query the weather corresponding to the region and date.If the date information is not specified, it will default to today's date.

## Examples
What's the weather like today?
What's the weather like tomorrow?

# Script
Run the get-weather script:
```bash
python /Users/bytedance/automas/skills/weather_check/scripts/weather_check.py {region} {date}
```
