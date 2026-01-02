import json

def filter_nested_data(data, key, value_startswith):
    """
    Recursively filters data for dictionaries where `key` starts with `value_startswith`.
    """
    filtered = []

    if isinstance(data, dict):
        if key in data and data[key].startswith(value_startswith):
            filtered.append(data)
        for sub_key, sub_value in data.items():
            filtered.extend(filter_nested_data(sub_value, key, value_startswith))

    elif isinstance(data, list):
        for item in data:
            filtered.extend(filter_nested_data(item, key, value_startswith))

    return filtered

# Load the JSON file
input_file = "input/searches.json"  # Replace with your JSON file name
output_file = "filtered_search_activity.json"  # Name for the filtered output file

with open(input_file, "r", encoding="utf-8") as file:
    data = json.load(file)

# Filter entries
filtered_data = filter_nested_data(data, "titleUrl", "https://www.google.com/search?q=")

# Save the filtered data to a new file
with open(output_file, "w", encoding="utf-8") as file:
    json.dump(filtered_data, file, ensure_ascii=False, indent=4)

print(f"Filtered data saved to {output_file}")
