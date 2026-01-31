
import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# --- Configuration ---
BASE_URL = "https://developers.google.com/google-ads/api/"
# We will start with a few key sections to keep the download size manageable
# In a real-world scenario, this list could be expanded or discovered dynamically
START_URLS = [
    "https://developers.google.com/google-ads/api/docs/get-started/introduction",
    "https://developers.google.com/google-ads/api/docs/concepts/overview",
    "https://developers.google.com/google-ads/api/docs/reporting/overview",
]
OUTPUT_DIR = 'google_ads_docs_viewer'

# --- Helper Functions ---

def sanitize_filename(url):
    """
    Cleans a URL to create a safe and descriptive local filename.
    Example: 'https://.../docs/concepts/api-structure' -> 'docs_concepts_api-structure.html'
    """
    # Remove the base URL part to get a relative path
    path = url.replace(BASE_URL, '')
    # Replace slashes and other unsafe characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', path)
    # Ensure it ends with .html
    if not sanitized.endswith('.html'):
        sanitized += '.html'
    return sanitized

def get_page_title(html_content):
    """
    Parses HTML content to extract the text from the <title> tag.
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        title_tag = soup.find('title')
        if title_tag and title_tag.string:
            # Clean up the title string
            return title_tag.string.strip().replace(' | Google Ads API', '').replace(' | Google for Developers', '')
    except Exception as e:
        print(f"  - Warning: Could not parse title. Error: {e}")
    return "Untitled Document"

def generate_index_html(file_info_list):
    """
    Generates the final index.html file from a list of file info dictionaries.
    """
    list_items = ""
    # Sort the list alphabetically by title for better navigation
    for info in sorted(file_info_list, key=lambda x: x['title']):
        list_items += f'        <li><a href="{info["relative_path"]}">{info["title"]}</a></li>\n'

    html_template = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Google Ads API Dokümantasyon Görüntüleyici</title>
    <style>
        body {{ font-family: sans-serif; margin: 2em; }}
        input {{ width: 100%; padding: 10px; margin-bottom: 20px; font-size: 16px; }}
        ul {{ list-style-type: none; padding: 0; }}
        li {{ margin-bottom: 10px; }}
        a {{ text-decoration: none; color: #007BFF; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>Google Ads API Dokümantasyon Görüntüleyici</h1>
    <input type="text" id="searchInput" onkeyup="searchFunction()" placeholder="Dokümanlarda ara...">
    <ul id="docList">
{list_items}    </ul>
    <script>
    function searchFunction() {{
        var input, filter, ul, li, a, i, txtValue;
        input = document.getElementById('searchInput');
        filter = input.value.toUpperCase();
        ul = document.getElementById("docList");
        li = ul.getElementsByTagName('li');
        for (i = 0; i < li.length; i++) {{
            a = li[i].getElementsByTagName("a")[0];
            txtValue = a.textContent || a.innerText;
            if (txtValue.toUpperCase().indexOf(filter) > -1) {{
                li[i].style.display = "";
            }} else {{
                li[i].style.display = "none";
            }}
        }}
    }}
    </script>
</body>
</html>"""

    index_path = os.path.join(OUTPUT_DIR, 'index.html')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html_template)
    print(f"\nSuccessfully generated index.html with {len(file_info_list)} links.")


# --- Main Logic ---

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    print(f"Starting documentation download from {len(START_URLS)} sections...")

    downloaded_files_info = []
    processed_urls = set()

    # Create a session for connection pooling
    session = requests.Session()

    for url in START_URLS:
        if url in processed_urls:
            continue

        try:
            print(f"- Fetching section: {url}")
            response = session.get(url)
            response.raise_for_status() # Raises an exception for bad status codes

            soup = BeautifulSoup(response.content, 'html.parser')
            processed_urls.add(url)

            # Process and save the main section page
            main_filename = sanitize_filename(url)
            main_filepath = os.path.join(OUTPUT_DIR, main_filename)
            with open(main_filepath, 'wb') as f:
                f.write(response.content)

            page_title = get_page_title(response.content)
            downloaded_files_info.append({
                "title": page_title,
                "relative_path": main_filename
            })

            # Find and download all linked pages within the same directory
            links = soup.find_all('a', href=True)
            for link in links:
                absolute_url = urljoin(url, link['href'])
                # Only process links that are within the same subdirectory
                if absolute_url.startswith(os.path.dirname(url)) and absolute_url not in processed_urls:
                    try:
                        print(f"  - Fetching linked page: {absolute_url}")
                        sub_response = session.get(absolute_url)
                        sub_response.raise_for_status()

                        filename = sanitize_filename(absolute_url)
                        filepath = os.path.join(OUTPUT_DIR, filename)

                        with open(filepath, 'wb') as f:
                            f.write(sub_response.content)

                        title = get_page_title(sub_response.content)
                        downloaded_files_info.append({
                            "title": title,
                            "relative_path": filename
                        })
                        processed_urls.add(absolute_url)

                    except requests.RequestException as e:
                        print(f"  - Warning: Failed to download {absolute_url}. Error: {e}")

        except requests.RequestException as e:
            print(f"- Error: Failed to download section {url}. Error: {e}")

    if downloaded_files_info:
        generate_index_html(downloaded_files_info)
    else:
        print("\nNo files were downloaded. index.html not generated.")


if __name__ == "__main__":
    main()
