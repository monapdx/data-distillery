import json

# Replace 'Search.json' with the actual path to your file
file_path = "C:\\Users\\Ash\\Downloads\\Exported-Data\\takeout-20250105T072242Z-001\\Takeout\\My Activity\\Search\\MyActivity.json"

try:
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # Adjust this logic to match the structure of your JSON file
    search_count = sum(1 for item in data if 'search' in item.get('title', '').lower())
    print(f"Total Searches: {search_count}")

except UnicodeDecodeError as e:
    print(f"UnicodeDecodeError: {e}")
except json.JSONDecodeError as e:
    print(f"JSONDecodeError: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
