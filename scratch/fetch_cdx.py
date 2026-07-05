import httpx
import json

cdx_url = "http://web.archive.org/cdx/search/cdx?url=blinkit.com/pr/*&output=json&limit=5"
resp = httpx.get(cdx_url)
print(resp.json())
