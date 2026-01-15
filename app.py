# app.py
from flask import Flask, render_template, request
import requests
import re
import json

app = Flask(__name__)

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
    
    # Method 1: Direct JSON parsing if possible
    try:
        # Look for specifications object - match until the end or next major structure
        spec_match = re.search(r'specifications:\s*(\{[^}]*characteristicTables[^}]*\[[^\]]*\].*?\})\s*(?:,|\}|$)', content, re.DOTALL)
        if not spec_match:
            # Try alternative pattern - get everything after specifications:
            spec_match = re.search(r'specifications:\s*(\{.*?\})\s*(?:[,\}]|$)', content, re.DOTALL)
        
        if spec_match:
            json_str = spec_match.group(1)
            debug.append("Found specifications object")
            
            # Fix JavaScript object notation to JSON
            json_str_fixed = re.sub(r'(\w+):', r'"\1":', json_str)
            
            # Parse as JSON
            try:
                data = json.loads(json_str_fixed)
                debug.append("Successfully parsed JSON")
                
                # Search through all tables and rows
                for table in data.get('characteristicTables', []):
                    for row in table.get('rows', []):
                        char_name = row.get('characteristicName', '')
                        if 'Maximum configurable power in W' in char_name:
                            values = row.get('characteristicValues', [])
                            if values:
                                result['power_w'] = values[0].get('labelText', 'Not found')
                                debug.append(f"Found W: {result['power_w']}")
                        
                        if 'Maximum configurable power in VA' in char_name:
                            values = row.get('characteristicValues', [])
                            if values:
                                result['power_va'] = values[0].get('labelText', 'Not found')
                                debug.append(f"Found VA: {result['power_va']}")
                        
                        if 'UPS type' in char_name:
                            values = row.get('characteristicValues', [])
                            if values:
                                result['ups_type'] = values[0].get('labelText', 'Not found')
                                debug.append(f"Found UPS type: {result['ups_type']}")
                        
                        if 'Wave type' in char_name:
                            values = row.get('characteristicValues', [])
                            if values:
                                result['wave_type'] = values[0].get('labelText', 'Not found')
                                debug.append(f"Found Wave type: {result['wave_type']}")
                        
                        if 'Output connection type' in char_name:
                            values = row.get('characteristicValues', [])
                            if values:
                                result['output_connection'] = values[0].get('labelText', 'Not found')
                                debug.append(f"Found Output connection: {result['output_connection']}")
                        
                        if 'Colour' in char_name:
                            values = row.get('characteristicValues', [])
                            if values:
                                result['colour'] = values[0].get('labelText', 'Not found')
                                debug.append(f"Found Colour: {result['colour']}")
                        
                        if 'Height' in char_name:
                            values = row.get('characteristicValues', [])
                            if values:
                                result['height'] = values[0].get('labelText', 'Not found')
                                debug.append(f"Found Height: {result['height']}")
                        
                        if 'Width' in char_name:
                            values = row.get('characteristicValues', [])
                            if values:
                                result['width'] = values[0].get('labelText', 'Not found')
                                debug.append(f"Found Width: {result['width']}")
                        
                        if 'Depth' in char_name:
                            values = row.get('characteristicValues', [])
                            if values:
                                result['depth'] = values[0].get('labelText', 'Not found')
                                debug.append(f"Found Depth: {result['depth']}")
            except json.JSONDecodeError as e:
                debug.append(f"JSON parse error: {str(e)}")
    except Exception as e:
        debug.append(f"Method 1 error: {str(e)}")
    
    # Method 2: Regex patterns for embedded data (most reliable for this format)
    specs_to_extract = {
        'power_w': ['Maximum configurable power in W'],
        'power_va': ['Maximum configurable power in VA'],
        'ups_type': ['UPS type'],
        'wave_type': ['Wave type'],
        'output_connection': ['Output connection type'],
        'colour': ['Colour', 'Color'],
        'height': ['Height'],
        'width': ['Width'],
        'depth': ['Depth']
    }
    
    for key, names in specs_to_extract.items():
        if result[key] == 'Not found':
            for name in names:
                patterns = [
                    rf'characteristicName["\s:]+{name}["\s,}}]+.*?labelText["\s:]+([^"]+)"',
                    rf'"{name}".*?labelText["\s:]+([^"]+)"',
                ]
                for pattern in patterns:
                    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
                    if match:
                        result[key] = match.group(1).strip().replace('\\u003Cbr />', ', ')
                        debug.append(f"Found {name} with regex: {result[key]}")
                        break
                if result[key] != 'Not found':
                    break
    
    # Show sample of content for debugging
    sample_chars = [m.group(1) for m in re.finditer(r'"characteristicName"\s*:\s*"([^"]+)"', content)]
    if sample_chars:
        debug.append(f"\nFound {len(sample_chars)} characteristic names:")
        debug.append(", ".join(sample_chars[:10]))
    
    return result, "\n".join(debug)

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    errors = []
    urls = []
    
    if request.method == 'POST':
        # Get all URLs from form
        for i in range(1, 7):
            url = request.form.get(f'url{i}', '').strip()
            if url:
                urls.append(url)
        
        # Fetch and extract specs for each URL
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        for idx, url in enumerate(urls, 1):
            try:
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                
                specs, debug_info = extract_specs(response.text)
                specs['url'] = url
                specs['product_num'] = specs['product_id'] if specs['product_id'] != 'Not found' else f"Product {idx}"
                results.append(specs)
                
            except requests.exceptions.RequestException as e:
                errors.append(f'Error fetching URL {idx}: {str(e)}')
            except Exception as e:
                errors.append(f'Error processing URL {idx}: {str(e)}')
    
    return render_template('index.html', results=results, errors=errors, urls=urls)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)