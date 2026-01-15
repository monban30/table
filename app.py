# app.py
from flask import Flask, render_template, request
import requests
import re
import json
import random

app = Flask(__name__)

# Common browser user agents to help bypass simple bot filters
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0"
]


def extract_specs(content):
    """Extract specifications using multiple regex patterns"""
    result = {
        'product_id': 'Not found',
        'power_w': 'Not found',
        'power_va': 'Not found',
        'ups_type': 'Not found',
        'wave_type': 'Not found',
        'output_connection': 'Not found',
        'colour': 'Not found',
        'height': 'Not found',
        'width': 'Not found',
        'depth': 'Not found'
    }
    debug = []

    # Extract product ID first
    product_id_pattern = r'"productId"\s*:\s*"([^"]+)"'
    product_id_match = re.search(product_id_pattern, content)
    if product_id_match:
        result['product_id'] = product_id_match.group(1)
        debug.append(f"Found Product ID: {result['product_id']}")

    # Try to find if content contains specifications object
    debug.append(f"Content length: {len(content)} characters")

    try:
        spec_match = re.search(r'specifications:\s*(\{[^}]*characteristicTables[^}]*\[[^\]]*\].*?\})\s*(?:,|\}|$)', content, re.DOTALL)
        if not spec_match:
            spec_match = re.search(r'specifications:\s*(\{.*?\})\s*(?:[,\}]|$)', content, re.DOTALL)

        if spec_match:
            json_str = spec_match.group(1)
            debug.append("Found specifications object")

            json_str_fixed = re.sub(r'(\w+):', r'"\1":', json_str)

            try:
                data = json.loads(json_str_fixed)
                debug.append("Successfully parsed JSON")

                for table in data.get('characteristicTables', []):
                    for row in table.get('rows', []):
                        char_name = row.get('characteristicName', '')
                        values = row.get('characteristicValues', [])
                        if not values:
                            continue
                        value = values[0].get('labelText', 'Not found')

                        for key, keywords in {
                            'power_w': ['Maximum configurable power in W'],
                            'power_va': ['Maximum configurable power in VA'],
                            'ups_type': ['UPS type'],
                            'wave_type': ['Wave type'],
                            'output_connection': ['Output connection type'],
                            'colour': ['Colour'],
                            'height': ['Height'],
                            'width': ['Width'],
                            'depth': ['Depth']
                        }.items():
                            if any(k in char_name for k in keywords):
                                result[key] = value
                                debug.append(f"Found {key}: {value}")
            except json.JSONDecodeError as e:
                debug.append(f"JSON parse error: {str(e)}")
    except Exception as e:
        debug.append(f"Spec extraction error: {str(e)}")

    return result, "\n".join(debug)


@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    errors = []
    urls = []

    if request.method == 'POST':
        # Collect up to 6 URLs
        for i in range(1, 7):
            url = request.form.get(f'url{i}', '').strip()
            if url:
                urls.append(url)

        for idx, url in enumerate(urls, 1):
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Connection": "keep-alive"
            }
            try:
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 403:
                    errors.append(f"Error fetching URL {idx}: 403 Forbidden (site blocked Render IP or bot request)")
                    continue

                response.raise_for_status()
                specs, debug_info = extract_specs(response.text)
                specs['url'] = url
                specs['product_num'] = specs['product_id'] if specs['product_id'] != 'Not found' else f"Product {idx}"
                results.append(specs)

            except requests.exceptions.RequestException as e:
                errors.append(f"Error fetching URL {idx}: {str(e)}")
            except Exception as e:
                errors.append(f"Error processing URL {idx}: {str(e)}")

    return render_template('index.html', results=results, errors=errors, urls=urls)


if __name__ == '__main__':
    # Render expects the app to listen on 0.0.0.0 with the provided PORT
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
