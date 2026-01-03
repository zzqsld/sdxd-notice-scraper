from html.parser import HTMLParser
import os

class FormParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_form = False
        self.form_data = {}

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        if tag == "form":
            self.in_form = True
            
        if tag == "input" and self.in_form:
            name = attrs_dict.get("name")
            value = attrs_dict.get("value", "")
            if name:
                self.form_data[name] = value

    def handle_endtag(self, tag):
        if tag == "form":
            self.in_form = False

def analyze_file(filepath):
    print(f"Analyzing {filepath}...")
    if not os.path.exists(filepath):
        print("File not found.")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    parser = FormParser()
    parser.feed(content)
    
    keys = list(parser.form_data.keys())
    print(f"Found {len(keys)} hidden inputs.")
    for k in keys:
        val = parser.form_data[k]
        if len(val) > 50:
            print(f"  {k}: {val[:20]}...{val[-20:]} (Length: {len(val)})")
        else:
            print(f"  {k}: {val}")
    return parser.form_data

data1 = analyze_file(r"d:\pachong\1学校新闻-山东现代学院.html")
data9 = analyze_file(r"d:\pachong\9学校新闻-山东现代学院.html")

print("\nComparing Page 1 vs Page 9:")
common_keys = set(data1.keys()) & set(data9.keys())
for k in common_keys:
    if data1[k] != data9[k]:
        print(f"  [DIFFERENT] {k}")
    else:
        print(f"  [SAME]      {k}")

only_in_1 = set(data1.keys()) - set(data9.keys())
only_in_9 = set(data9.keys()) - set(data1.keys())

if only_in_1:
    print(f"Only in Page 1: {only_in_1}")
if only_in_9:
    print(f"Only in Page 9: {only_in_9}")
