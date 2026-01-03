import requests
from bs4 import BeautifulSoup

url = "https://www.sdxd.edu.cn/detail/20250929140712ydwrbb0ezpftq796xu.html"
try:
    r = requests.get(url, timeout=10)
    r.encoding = r.apparent_encoding
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # Find the title to locate the content area
    # title = soup.find(string="我校召开中医药文化实践周活动研讨会")
    # Search for h1, h2, h3 containing the text
    import re
    target = re.compile("中医药文化实践周活动研讨会")
    found = soup.body.find(string=target)
    
    if found:
        print(f"Found text in body: {found}")
        parent = found.parent
        # Traverse up to find 'article-2'
        while parent and 'article-2' not in parent.get('class', []):
            parent = parent.parent
        
        if parent:
            print(f"Found container: {parent.name} class={parent.get('class')}")
            # Check if it has the body text
            text_len = len(parent.get_text())
            print(f"Container text length: {text_len}")
            
            if "您现在的位置" in parent.get_text():
                print("Breadcrumbs FOUND in container")
            else:
                print("Breadcrumbs NOT found in container")
        else:
            print("Could not find article-2 container")
        
except Exception as e:
    print(e)
