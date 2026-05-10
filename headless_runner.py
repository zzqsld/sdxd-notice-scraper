import os
import json
import time
import scrape_notices
import article_processor
from datetime import datetime

# Configuration
HISTORY_FILE = "history.json"
OUTPUT_DIR = "output"
SCRAPE_MODE = os.environ.get("SCRAPE_MODE", "incremental").strip().lower()
FULL_CRAWL = SCRAPE_MODE == "full"
DOWNLOAD_IMAGES = os.environ.get("DOWNLOAD_IMAGES", "true").strip().lower() in {"1", "true", "yes", "y", "on"}
PRESETS = {
    "官网学校新闻": "https://www.sdxd.edu.cn/page/20190417140037rmry93pvdhwspazvhn.html",
    "官网通知公告": "https://www.sdxd.edu.cn/page/20190417141109v1ewezmjl1uf1hqy9h.html",
    "官网校园动态": "https://www.sdxd.edu.cn/page/20190404194753wvyx0njs7m2gopyk6g.html",
    "官网学术信息": "https://www.sdxd.edu.cn/page/20250519093719belcb0u1xf6h94mj9y.html"
}

TITLE_TYPES = {
    "官网学校新闻": "校园新闻",
    "官网校园动态": "校园动态",
    "官网通知公告": "通知公告",
    "官网学术信息": "学术信息",
}

TITLE_PREFIXES = {
    "官网学校新闻": "新闻",
    "官网校园动态": "校园动态",
    "官网通知公告": "通知公告",
    "官网学术信息": "学术信息",
}

def format_article_title(category_name: str, title: str, published_at: str) -> str:
    prefix = TITLE_PREFIXES.get(category_name, "新闻")
    news_type = TITLE_TYPES.get(category_name, "新闻")
    safe_title = title.strip()
    safe_time = published_at.strip() if published_at else "未知"
    return f"【{prefix}】{safe_title} | 时间：{safe_time} | 类型：{news_type}"

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
    
    if FULL_CRAWL:
        print("Running in full crawl mode.")
        history = {}
    else:
        print("Running in incremental mode.")
        history = load_history()
    has_updates = False
    
    for name, url in PRESETS.items():
        print(f"Processing: {name} ({url})")
        
        if FULL_CRAWL:
            url_history = set()
            print("  Full crawl: history disabled for this run.")
        else:
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

                for item in new_items:
                    item['title'] = format_article_title(name, item.get('title', ''), item.get('date', ''))
                
                # Update history
                if url not in history:
                    history[url] = set()
                for item in new_items:
                    history[url].add(item['link'])
                
                # Generate Word doc
                date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                mode_suffix = "full" if FULL_CRAWL else "incremental"
                image_suffix = "img" if DOWNLOAD_IMAGES else "noimg"
                doc_name = f"{name}_{mode_suffix}_{image_suffix}_{date_str}.docx"
                doc_path = os.path.join(OUTPUT_DIR, doc_name)
                
                print(f"Generating Word document: {doc_path}")
                
                article_processor.generate_word_doc(
                    items=new_items,
                    output_path=doc_path,
                    max_size_mb=100,
                    progress_callback=lambda c, t, title: print(f"  [{c}/{t}] {title}"),
                    download_images=DOWNLOAD_IMAGES
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
