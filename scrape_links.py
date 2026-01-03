import argparse
import time
import sys
import urllib.request
import urllib.error
from urllib.parse import urljoin
from html.parser import HTMLParser

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.recording = False
        self.current_links = []
        self.in_a_tag = False
        self.current_href = None
        self.current_text = ""

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.in_a_tag = True
            attrs_dict = dict(attrs)
            self.current_href = attrs_dict.get("href")
            self.current_text = ""

    def handle_endtag(self, tag):
        if tag == "a" and self.in_a_tag:
            if self.current_href:
                self.current_links.append({"href": self.current_href, "text": self.current_text.strip()})
            self.in_a_tag = False
            self.current_href = None
            self.current_text = ""

    def handle_data(self, data):
        if self.in_a_tag:
            self.current_text += data

def fetch(url: str, timeout: float, user_agent: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode('utf-8', errors='ignore')

def parse_links_simple(html: str, base_url: str) -> list[tuple[str, str]]:
    parser = LinkParser()
    parser.feed(html)
    
    results = []
    for link in parser.current_links:
        href = link.get("href")
        if not href:
            continue
        # 处理相对路径
        full = urljoin(base_url, href)
        title = link.get("text", "") or full
        results.append((title, full))
    return results

def crawl(
    start_url: str,
    output_file: str,
    limit: int | None = None,
    timeout: float = 15.0,
    user_agent: str = "Mozilla/5.0 (compatible; CopilotCrawler/1.0)"
):
    seen = set()
    collected: list[tuple[str, str]] = []

    print(f"开始抓取: {start_url}")

    try:
        html = fetch(start_url, timeout, user_agent)
    except Exception as e:
        print(f"[error] 获取页面失败 {start_url}: {e}", file=sys.stderr)
        return

    links = parse_links_simple(html, start_url)
    
    # 简单过滤：只保留 http/https 开头的链接
    valid_links = []
    for title, href in links:
        if href.startswith("http"):
            valid_links.append((title, href))

    print(f"页面发现 {len(valid_links)} 个有效链接")

    for title, href in valid_links:
        if href in seen:
            continue
        seen.add(href)
        collected.append((title, href))
        if limit is not None and len(collected) >= limit:
            break

    with open(output_file, "w", encoding="utf-8") as f:
        for title, href in collected:
            f.write(f"{title} {href}\n")

    print(f"共采集链接 {len(collected)} 条，已写入 {output_file}")
    for i, (title, href) in enumerate(collected[:10], 1):
        print(f"示例[{i}]: {title} -> {href}")

def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="通用文章链接爬取脚本 (标准库版)")
    p.add_argument("--url", required=True, help="起始页面URL")
    p.add_argument("--output", required=True, help="输出文件路径")
    p.add_argument("--limit", type=int, default=None, help="最多采集的链接条数")
    p.add_argument("--timeout", type=float, default=15.0, help="请求超时秒数")
    p.add_argument("--user-agent", default="Mozilla/5.0 (compatible; CopilotCrawler/1.0)", help="自定义User-Agent")
    return p

def main():
    args = build_argparser().parse_args()
    crawl(
        start_url=args.url,
        output_file=args.output,
        limit=args.limit,
        timeout=args.timeout,
        user_agent=args.user_agent,
    )

if __name__ == "__main__":
    main()
