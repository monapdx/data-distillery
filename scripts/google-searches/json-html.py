import json

def json_to_html_recursive(data):
    """Recursively converts JSON data to HTML."""
    html_content = ""

    # If the data is a dictionary
    if isinstance(data, dict):
        html_content += "<table border='1'>"
        for key, value in data.items():
            html_content += f"<tr><th>{key}</th><td>{json_to_html_recursive(value)}</td></tr>"
        html_content += "</table>"
    
    # If the data is a list
    elif isinstance(data, list):
        html_content += "<ul>"
        for item in data:
            html_content += f"<li>{json_to_html_recursive(item)}</li>"
        html_content += "</ul>"
    
    # If the data is a basic data type (int, str, etc.)
    else:
        html_content += str(data)
    
    return html_content

def json_to_html(json_file, output_html):
    # Open the JSON file and load the data
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Create the base HTML structure
    html_content = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>JSON to HTML</title>
        <style>
            table {
                width: 100%;
                border-collapse: collapse;
            }
            table, th, td {
                border: 1px solid black;
            }
            th, td {
                padding: 8px;
                text-align: left;
            }
            th {
                background-color: #f2f2f2;
            }
            ul {
                list-style-type: none;
                padding: 0;
            }
            li {
                padding: 5px;
            }
        </style>
    </head>
    <body>
        <h1>JSON Data</h1>
    '''
    
    # Generate HTML from the JSON data using recursion
    html_content += json_to_html_recursive(data)
    
    html_content += '''
    </body>
    </html>
    '''
    
    # Write the generated HTML content to an output file
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"HTML file '{output_html}' created successfully.")

# Example usage
json_to_html('C:\\Users\\Ash\\Downloads\\Exported-Data\\chatGPT\\October-12', 'output.html')
