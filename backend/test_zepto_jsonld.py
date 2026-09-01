import json
from bs4 import BeautifulSoup

with open("zepto_product_source.html", "r") as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
scripts = soup.find_all('script', type='application/ld+json')
print(f"Found {len(scripts)} ld+json scripts")
for s in scripts:
    try:
        data = json.loads(s.string)
        if data.get('@type') == 'Product':
            print("Product Image:", data.get('image'))
    except Exception as e:
        print(e)
