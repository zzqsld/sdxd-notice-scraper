import os
import json
import time
import scrape_notices
import article_processor
from datetime import datetime

# Configuration
HISTORY_FILE = "history.json"
OUTPUT_DIR = "output"
PRESETS = {
    "官网学校新闻": "https://www.sdxd.edu.cn/page/20190417140037rmry93pvdhwspazvhn.html",
    "官网通知公告": "https://www.sdxd.edu.cn/page/20190417141109v1ewezmjl1uf1hqy9h.html",
    "官网校园动态": "https://www.sdxd.edu.cn/page/20190404194753wvyx0njs7m2gopyk6g.html",
    "官网学术信息": "https://www.sdxd.edu.cn/page/20250519093719belcb0u1xf6h94mj9y.html"
}

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Convert lists back to sets
                return {k: set(v) for k, v in data.items()}
        except Exception as e:
            print(f"Error loading history: {e}")
    return {}

def save_history(history):
    # Convert sets to lists for JSON
    data = {k: list(v) for k, v in history.items()}
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def run():
    print(f"Starting scrape job at {datetime.now()}")
    ensure_dir(OUTPUT_DIR)
    
    history = load_history()
    has_updates = False
    
    for name, url in PRESETS.items():
        print(f"Processing: {name} ({url})")
        
        # Try to find history for this URL (handling potential fragments in keys)
        url_history = history.get(url)
        if url_history is None:
            # Fallback: look for key starting with this URL
            for k, v in history.items():
                if k.startswith(url):
                    url_history = v
                    print(f"  Using history from key: {k}")
                    break
        
        if url_history is None:
            url_history = set()
            print("  No history found, starting fresh.")
        else:
            print(f"  Loaded {len(url_history)} history items.")
        
        # Temporary file for this scrape (required by crawl_notices)
        temp_txt = os.path.join(OUTPUT_DIR, f"temp_{name}.txt")
        
        try:
            # Scrape
            # We use update_only logic by passing history
            new_items = scrape_notices.crawl_notices(
                source=url,
                output_file=temp_txt,
                is_file=False,
                timeout=30.0,
                history=url_history
            )
            
            if new_items:
                print(f"Found {len(new_items)} new items for {name}")
                has_updates = True
                
                # Update history
                if url not in history:
                    history[url] = set()
                for item in new_items:
                    history[url].add(item['link'])
                
                # Generate Word doc
                date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                doc_name = f"{name}_{date_str}.docx"
                doc_path = os.path.join(OUTPUT_DIR, doc_name)
                
                print(f"Generating Word document: {doc_path}")
                
                article_processor.generate_word_doc(
                    items=new_items,
                    output_path=doc_path,
                    max_size_mb=100,
                    progress_callback=lambda c, t, title: print(f"  [{c}/{t}] {title}"),
                    download_images=True
                )
                
            else:
                print(f"No new items for {name}")
                
        except Exception as e:
            print(f"Error processing {name}: {e}")
        finally:
            # Clean up temp file
            if os.path.exists(temp_txt):
                try:
                    os.remove(temp_txt)
                except:
                    pass
                
    if has_updates:
        print("Saving history...")
        save_history(history)
    else:
        print("No updates found in any category.")

if __name__ == "__main__":
    run()
