import json

# Open your JSON file for reading
with open('C:\\Users\\Ash\\Downloads\\Exported-Data\\takeout-20250105T072242Z-001\\Takeout\\My Activity\\Search\\MyActivity.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# Filter out entries where 'titleUrl' starts with 'https://www.google.com/search?q='
filtered_data = [entry for entry in data if entry.get('titleUrl', '').startswith('https://www.google.com/search?q=')]

# Write the filtered data back to a new JSON file
with open('filtered_google_search_data.json', 'w', encoding='utf-8') as file:
    json.dump(filtered_data, file, ensure_ascii=False, indent=2)

print(f"Filtered data containing search queries saved to 'filtered_google_search_data.json'.")
