import re

def extract_urls(file_path, output_path):
    # Define the regex pattern to find URLs containing 'search?q='
    pattern = re.compile(r'https?://[^\s"]*search\?q=[^\s"]*')
    
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        
    # Find all matching URLs
    urls = re.findall(pattern, content)
    
    # Write the URLs to the output file
    with open(output_path, 'w', encoding='utf-8') as output_file:
        for url in urls:
            output_file.write(url + '\n')

# Replace 'path_to_html_file' with the actual path to your HTML file
input_file = 'input/MyActivity.html'
# Replace 'output_file.txt' with the desired path for the output file
output_file = 'output/text-links.txt'

extract_urls(input_file, output_file)
