from bs4 import BeautifulSoup
import re

def extract_urls(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    urls = []

    # Find all links in the HTML
    for link in soup.find_all('a', href=True):
        href = link['href']
        if 'q?=' in href:
            urls.append(href)
    
    return urls

def save_urls_to_file(urls, output_file):
    with open(output_file, 'w') as file:
        for url in urls:
            file.write(url + '\n')

# Path to the input HTML file
input_html_file = 'input/MyActivity.html'

# Path to the output text file
output_text_file = 'output_urls_2.txt'

# Read the HTML content from the file
with open(input_html_file, 'r', encoding='utf-8') as file:
    html_content = file.read()

# Extract URLs and save to file
urls = extract_urls(html_content)
save_urls_to_file(urls, output_text_file)

print(f'Extracted URLs saved to {output_text_file}')
