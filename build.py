import json

# Load site data
with open('site-data.json') as f:
    site_data = json.load(f)

# Open index.html and replace the defaultData object
with open('index.html', 'r') as file:
    data = file.read()
    new_data = data.replace('defaultData', json.dumps(site_data))

# Write the changes back to index.html
with open('index.html', 'w') as file:
    file.write(new_data)
