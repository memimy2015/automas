---
name: web-search
description: Used to perform internet-wide information retrieval. It demonstrates how to call the specified web_search script to obtain public information on the Internet according to user query needs. In addition, further searches can be conducted based on contextual content to ensure that the finally obtained information meets the user's query needs and is suitable for various scenarios requiring internet-wide information support.
---


# Internet-Wide Search

## Instructions
It supports retrieving information from the entire Internet. If the retrieved information is insufficient, multiple calls can be made to perform repeated searches using different keyword information. Additionally, further searches can be conducted based on the contextual content.

## Script
Run the web_search script:
```bash
python {PROJECT_DIR}/skills/web_search/scripts/internet_wide_search.py {query}
```
