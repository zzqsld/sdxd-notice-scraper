import urllib.request
from html.parser import HTMLParser

url = "https://www.sdxd.edu.cn/page/20190417140037rmry93pvdhwspazvhn.html"

def fetch(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as response:
        return response.read().decode('utf-8', errors='ignore')

html = fetch(url)

print(f"HTML length: {len(html)}")

# Save to file for manual inspection if needed (though I can't see it directly, I can grep it)
with open("debug_list_page.html", "w", encoding="utf-8") as f:
    f.write(html)

# Let's try to find some known text from the website to locate the container
# I'll search for a common class or just print the structure around 'li' tags
class DebugParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.in_target = False
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        classes = attrs_dict.get("class", "")
        ids = attrs_dict.get("id", "")
        
        # Print potential containers
        if "news" in classes or "list" in classes or "content" in classes or "box" in classes:
            print(f"Found potential container: <{tag} class='{classes}' id='{ids}'>")

parser = DebugParser()
parser.feed(html)
