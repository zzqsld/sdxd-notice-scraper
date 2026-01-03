import argparse
import sys
import time
import urllib.request
import urllib.error
import re
import json
from urllib.parse import urlparse, parse_qs, urlencode
from html.parser import HTMLParser

def parse_json_response(html: str) -> list[dict]:
    """
    尝试从 HTML 中提取 var sdata... = [...] 格式的 JSON 数据
    """
    notices = []
    # 匹配 var sdata... = [...];
    # 注意：JSON 可能跨多行，使用 DOTALL
    pattern = re.compile(r'var\s+sdata\w+\s*=\s*(\[.*?\]);', re.DOTALL)
    match = pattern.search(html)
    
    if match:
        json_str = match.group(1)
        try:
            data = json.loads(json_str)
            for item in data:
                link = item.get("url", "")
                if link.startswith("//"):
                    link = "https:" + link
                elif link.startswith("/"):
                    # 假设是相对路径，需要 base_url，但这里没有 context
                    # 暂时保留原样，或者假设是 https://www.sdxd.edu.cn
                    pass
                    
                notice = {
                    "title": item.get("title", ""),
                    "date": item.get("sjall", "").split(" ")[0], # 只取日期部分
                    "link": link,
                    "body": item.get("Abstract", "")
                }
                notices.append(notice)
        except json.JSONDecodeError as e:
            print(f"[warn] JSON 解析失败: {e}")
            
    return notices

class NoticeParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.notices = []
        self.current_notice = {}
        self.in_content_box = False
        self.in_title = False
        self.in_body = False
        self.in_date_day = False
        self.in_date_year = False
        self.temp_data = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        classes = attrs_dict.get("class", "").split()

        if "content-box" in classes:
            # print(f"DEBUG: Found content-box in tag {tag}")
            self.in_content_box = True
            self.current_notice = {"title": "", "body": "", "date": "", "link": attrs_dict.get("href", "")}
            # print(f"DEBUG: Start content-box: {self.current_notice['link']}")
        
        if self.in_content_box:
            if "titletext" in classes:
                self.in_title = True
                self.temp_data = ""
            elif "bodytext" in classes:
                self.in_body = True
                self.temp_data = ""
            elif tag == "span":
                 self.in_date_day = True
                 self.temp_data = ""
            elif tag == "em":
                 self.in_date_year = True
                 self.temp_data = ""

    def handle_endtag(self, tag):
        # print(f"DEBUG: End tag {tag}, in_content_box={self.in_content_box}")
        if self.in_content_box:
            if tag == "a": 
                # print("DEBUG: Closing content-box")
                day = self.current_notice.pop("day", "")
                year_month = self.current_notice.pop("year_month", "")
                if day and year_month:
                    self.current_notice["date"] = f"{year_month}-{day}"
                
                self.notices.append(self.current_notice)
                self.current_notice = {}
                self.in_content_box = False
            
            elif self.in_title and tag == "article":
                self.current_notice["title"] = self.temp_data.strip()
                self.in_title = False
            elif self.in_body and tag == "article":
                self.current_notice["body"] = self.temp_data.strip()
                self.in_body = False
            elif self.in_date_day and tag == "span":
                self.current_notice["day"] = self.temp_data.strip()
                self.in_date_day = False
            elif self.in_date_year and tag == "em":
                self.current_notice["year_month"] = self.temp_data.strip()
                self.in_date_year = False

    def handle_data(self, data):
        if self.in_title or self.in_body or self.in_date_day or self.in_date_year:
            self.temp_data += data

import http.cookiejar

# 全局 Opener，用于保持 Cookie
cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

def fetch(url: str, timeout: float, user_agent: str, data: dict = None, referer: str = None, extra_headers: dict = None) -> str:
    headers = {"User-Agent": user_agent}
    if referer:
        headers["Referer"] = referer
    if extra_headers:
        headers.update(extra_headers)
        
    req = urllib.request.Request(url, headers=headers)
    if data:
        encoded_data = urlencode(data).encode('utf-8')
        req.data = encoded_data
        req.method = 'POST'
        # 移除 AJAX 头，以获取完整页面（包含 ViewState）
        # req.add_header("X-Requested-With", "XMLHttpRequest")
    
    with opener.open(req, timeout=timeout) as response:
        return response.read().decode('utf-8', errors='ignore')

def extract_form_data(html: str, target_component_id: str = None) -> dict:
    """
    从 HTML 中提取 form 数据。
    优先提取包含目标 ID 的 form，其次提取包含 __VIEWSTATE 的 form，最后回退到第一个 form。
    """
    class FormParser(HTMLParser):
        def __init__(self, target_id=None):
            super().__init__()
            self.target_id = target_id
            self.in_form = False
            self.current_form_data = {}
            
            self.target_form_data = None
            self.viewstate_form_data = None
            self.first_form_data = None
            
            self.current_has_target = False
            self.current_has_viewstate = False

        def handle_starttag(self, tag, attrs):
            attrs_dict = dict(attrs)
            
            if tag == "form":
                self.in_form = True
                self.current_form_data = {}
                self.current_has_target = False
                self.current_has_viewstate = False
                
            if tag == "input" and self.in_form:
                name = attrs_dict.get("name")
                value = attrs_dict.get("value", "")
                if name:
                    self.current_form_data[name] = value
                    
                    # 检查是否是目标组件
                    if self.target_id:
                        if name == "newsComponentId" and value == self.target_id:
                            self.current_has_target = True
                        elif name == self.target_id:
                            self.current_has_target = True
                            
                    # 检查是否有 __VIEWSTATE
                    if name == "__VIEWSTATE":
                        self.current_has_viewstate = True

        def handle_endtag(self, tag):
            if tag == "form":
                self.in_form = False
                
                # 保存第一个 form
                if not self.first_form_data:
                    self.first_form_data = self.current_form_data.copy()
                
                # 保存包含 __VIEWSTATE 的 form
                if self.current_has_viewstate and not self.viewstate_form_data:
                    self.viewstate_form_data = self.current_form_data.copy()
                    
                # 保存目标 form
                if self.current_has_target:
                    self.target_form_data = self.current_form_data.copy()

    parser = FormParser(target_component_id)
    parser.feed(html)
    
    if parser.target_form_data:
        return parser.target_form_data
    elif parser.viewstate_form_data:
        # 如果没找到明确匹配的 form，但找到了包含 ViewState 的 form，这通常是主 form
        return parser.viewstate_form_data
    elif parser.first_form_data:
        # 最后的回退
        return parser.first_form_data
    return {}

def parse_url_info(url_str: str) -> tuple[str, str, str] | None:
    """
    解析 URL，返回 (base_url, webpage_id, component_id)
    component_id 可能为 None
    """
    parsed = urlparse(url_str)
    
    # 尝试从 fragment 提取 component_id
    fragment = parsed.fragment
    comp_id = None
    if fragment and '=' in fragment:
        try:
            comp_id, _ = fragment.split('=', 1)
        except ValueError:
            pass

    path = parsed.path
    webpage_id = None
    
    if '/page/' in path:
        # 格式: .../page/WEBPAGE_ID.html
        part = path.split('/page/')[-1]
        if part.endswith('.html') or part.endswith('.htm'):
            webpage_id = part.rsplit('.', 1)[0]
    elif path.endswith('/page.htm') or path.endswith('/page.html'):
        # 格式: .../WEBPAGE_ID/page.htm
        parts = path.split('/')
        if len(parts) >= 2:
            webpage_id = parts[-2]
            
    if not webpage_id:
        return None
        
    base_url = f"{parsed.scheme}://{parsed.netloc}/"
    return base_url, webpage_id, comp_id

def crawl_notices(source: str, output_file: str, is_file: bool = False, timeout: float = 30.0, start_page: int = 2, method: str = "POST", history: set = None) -> list[dict]:
    """
    抓取通知。
    :param history: 已知链接集合 (set)。如果提供，遇到其中的链接将视为旧内容。
    :return: 抓取到的所有通知列表 (list of dict)
    """
    print(f"开始处理: {source}")
    
    all_notices = []
    new_items_count = 0
    seen_links = set()
    
    # 如果传入了历史记录，将其加入 seen_links 以便去重，但我们需要区分"本次新抓取"和"历史已存在"
    # 策略：seen_links 用于本次抓取过程中的去重。
    # history 用于判断是否遇到旧内容。
    
    # 解析 URL 信息
    url_info = parse_url_info(source) if not is_file else None
    base_url, webpage_id, component_id = url_info if url_info else (None, None, None)
    
    form_data = None
    
    # 抓取第一页
    target_url = ""
    try:
        if is_file:
            with open(source, "r", encoding="utf-8") as f:
                html = f.read()
        else:
            # 初始请求使用原始 URL，以确保获取正确的页面内容和 Form 数据
            parsed_source = urlparse(source)
            # 去除 fragment
            initial_url = f"{parsed_source.scheme}://{parsed_source.netloc}{parsed_source.path}"
            print(f"请求初始页面: {initial_url}")
            
            html = fetch(initial_url, timeout, "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # DEBUG: Save Page 1 HTML - Removed for cleanup
            # with open("d:\\pachong\\debug_page1.html", "w", encoding="utf-8") as f:
            #    f.write(html)
            
            # 尝试自动检测页面中的真实 Component ID
            # 1. 查找类似 ?webpageId=...&COMPONENT_ID=... 的链接
            # 注意：HTML 中可能是 &amp;，且 ID 长度可能为 32 或 33
            real_comp_id_match = re.search(r'webpageId=[^&]+&(?:amp;)?([a-zA-Z0-9]{32,})=\d+', html)
            if real_comp_id_match:
                found_comp_id = real_comp_id_match.group(1)
                if found_comp_id != component_id:
                    print(f"[info] 检测到页面实际分页组件 ID 为: {found_comp_id} (原: {component_id})")
                    component_id = found_comp_id
            
            # 2. 如果还没找到，尝试查找 hidden input
            if not component_id:
                 input_match = re.search(r'<input[^>]*name="newsComponentId"[^>]*value="([a-zA-Z0-9]{32})"', html)
                 if input_match:
                     component_id = input_match.group(1)
                     print(f"[info] 从隐藏域检测到组件 ID: {component_id}")

            # 如果是分页模式，尝试提取 form 数据
            if component_id:
                print(f"尝试提取分页 Form 数据 (Component ID: {component_id})...")
                form_data = extract_form_data(html, target_component_id=component_id)
                
                if form_data:
                    print("成功提取目标 Form 数据，将使用 POST 请求翻页。")
                    # 打印关键参数以供调试
                    print(f"  pagesize: {form_data.get('pagesize')}")
                    print(f"  newstype: {form_data.get('newstype')}")
                    
                    # 构造 POST 请求的目标 URL (通常是 /?webpageId=...)
                    if webpage_id:
                        target_url = f"{base_url}?webpageId={webpage_id}"
                    else:
                        target_url = initial_url
                    print(f"翻页 POST URL: {target_url}")
                    
                else:
                    print("[warn] 未找到包含目标 Component ID 的 Form 数据！将尝试使用默认/空数据。")
                    # 尝试回退到第一个 Form? 或者报错?
                    # 暂时尝试手动构造，但很可能失败
                    form_data = {
                        'newsComponentId': component_id,
                    }
                    target_url = initial_url


    except Exception as e:
        print(f"[error] 获取第一页失败: {e}", file=sys.stderr)
        return []

    # 解析第一页
    parser = NoticeParser()
    parser.feed(html)
    
    notices = parser.notices
    if not notices:
        print("[info] HTML 解析未找到内容，尝试提取 JSON 数据...")
        notices = parse_json_response(html)
        if notices:
            print(f"[info] 使用 JSON 数据解析成功 (发现 {len(notices)} 条)")

    # 检查第一页内容
    page1_new_items = 0
    for notice in notices:
        link = notice.get("link", "")
        if link not in seen_links:
            seen_links.add(link)
            # 检查是否在历史记录中
            if history and link in history:
                continue # 跳过历史记录
            
            all_notices.append(notice)
            page1_new_items += 1
            
    print(f"第 1 页发现 {len(notices)} 条通知，其中新内容 {page1_new_items} 条")
    
    # 如果第一页全是旧内容，且提供了 history，则可能不需要继续翻页
    if history and page1_new_items == 0 and len(notices) > 0:
        print("第 1 页全部为历史内容，停止抓取。")
        # 写入空文件或不写入？根据需求，这里直接返回
        return all_notices

    # 翻页循环
    try:
        if not is_file and form_data and target_url:
            # 如果第一页没有发现内容（可能是因为内容是动态加载的），则从第 1 页开始抓取
            if len(parser.notices) == 0:
                print("初始页面未发现内容，尝试从第 1 页开始 POST 抓取...")
                current_page = 1
            else:
                current_page = start_page
                
            max_page = 70
            consecutive_duplicates = 0
            
            while current_page <= max_page:
                time.sleep(1.0) # 增加延时到 1s，避免服务器拒绝
                
                # 更新页码参数
                if method.upper() == "GET":
                    # GET 方式：直接构造 URL
                    # 格式: /?webpageId=...&componentId=page
                    query_params = {
                        "webpageId": webpage_id,
                        component_id: str(current_page)
                    }
                    next_url = f"{base_url}?{urlencode(query_params)}"
                    print(f"[{current_page}/{max_page}] 正在抓取第 {current_page} 页 (GET {next_url})...")
                    try:
                        html = fetch(next_url, timeout, "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", referer=target_url)
                    except Exception as e:
                        print(f"[warn] 获取第 {current_page} 页失败: {e}")
                        break
                else:
                    # POST 方式
                    # 注意：参数名就是 component_id
                    current_form_data = form_data.copy()
                    current_form_data[component_id] = str(current_page)
                    
                    print(f"[{current_page}/{max_page}] 正在抓取第 {current_page} 页 (POST to {target_url})...")
                    # print(f"DEBUG: POST Data keys: {list(current_form_data.keys())}")
                    
                    # Use initial_url as Referer if available, otherwise target_url
                    req_referer = initial_url if 'initial_url' in locals() else target_url
                    
                    try:
                        html = fetch(target_url, timeout, "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", data=current_form_data, referer=req_referer, extra_headers={"X-Requested-With": "XMLHttpRequest"})
                        
                        # DEBUG: Save first POST response - Removed for cleanup
                        # if current_page == 1 or current_page == start_page:
                        #      with open(f"d:\\pachong\\debug_post_page{current_page}.html", "w", encoding="utf-8") as f:
                        #         f.write(html)

                    except Exception as e:
                        print(f"[warn] 获取第 {current_page} 页失败: {e}")
                        break

                # 优先尝试解析 JSON 数据
                json_notices = parse_json_response(html)
                current_notices = []
                
                if json_notices:
                    # print(f"DEBUG: Found {len(json_notices)} notices via JSON")
                    current_notices = json_notices
                else:
                    # 回退到 HTML 解析
                    parser = NoticeParser()
                    parser.feed(html)
                    current_notices = parser.notices
                
                new_count = 0
                page_has_history_item = False
                
                for notice in current_notices:
                    link = notice.get("link", "")
                    if link not in seen_links:
                        seen_links.add(link)
                        
                        if history and link in history:
                            page_has_history_item = True
                            continue # 跳过历史记录
                            
                        all_notices.append(notice)
                        new_count += 1
                
                print(f"  -> 本页发现 {len(current_notices)} 条通知，新增 {new_count} 条")
                
                # 如果本页发现了历史记录中的条目，且没有新条目（或者策略是只要遇到旧的就停止），则停止
                # 假设是按时间倒序，一旦遇到旧的，后面都是旧的
                if history and page_has_history_item and new_count == 0:
                     print("遇到历史记录，停止抓取。")
                     break
                
                if len(current_notices) == 0:
                    print("当前页未发现任何通知，停止翻页")
                    break
                
                # 尝试从当前页面更新 form_data (用于获取新的 __VIEWSTATE 等)
                # 注意：这里也需要指定 target_component_id，否则可能提取到错误的 form
                new_form_data = extract_form_data(html, target_component_id=component_id)
                if new_form_data:
                    # print(f"DEBUG: Updated form data from response. Keys: {list(new_form_data.keys())}")
                    # 只更新隐藏字段，保留核心参数
                    for k, v in new_form_data.items():
                        if k not in ['webpageId', 'newsComponentId', component_id]:
                            form_data[k] = v
                else:
                    print(f"[warn] 响应中未找到目标 Form ({component_id})，无法更新 ViewState，翻页可能失败。")
                
                # 如果连续两页内容完全一样（新增为0），可能是分页参数无效
                # 用户反馈：有的标题前面几个字相同但是不同内容，不要轻易停止
                # 改为：如果连续 3 页都没有新增内容，再停止
                if new_count == 0:
                    consecutive_duplicates += 1
                    print(f"[warn] 本页未发现新内容 (连续 {consecutive_duplicates} 次)")
                    if consecutive_duplicates >= 5:
                        print("连续 5 页未发现新内容，停止翻页。")
                        break
                else:
                    consecutive_duplicates = 0

                current_page += 1

    except KeyboardInterrupt:
        print("\n[info] 用户中断，正在保存已抓取的数据...")
    except Exception as e:
        print(f"\n[error] 发生错误: {e}，正在保存已抓取的数据...")
    finally:
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                for notice in all_notices:
                    # 格式化输出
                    link = notice['link']
                    if link.startswith('//'):
                        link = link[2:]

                    f.write(f"标题: {notice['title']}\n")
                    f.write(f"{notice['date']}\n")
                    f.write(f"链接: {link}\n")
                    # f.write(f"内容摘要:\n{notice['body']}\n") 
                    f.write("-" * 50 + "\n")

            print(f"全部完成。共采集通知 {len(all_notices)} 条，已写入 {output_file}")
            
    return all_notices



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="山东现代学院通知公告爬虫")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="通知公告页面URL")
    group.add_argument("--file", help="本地HTML文件路径")
    
    parser.add_argument("--output", required=True, help="输出文件路径")
    parser.add_argument("--start-page", type=int, default=2, help="起始页码 (默认为 2)")
    parser.add_argument("--method", default="POST", help="请求方法 (POST 或 GET)")
    parser.add_argument("--timeout", type=float, default=30.0, help="请求超时时间 (秒)")
    args = parser.parse_args()
    
    if args.file:
        crawl_notices(args.file, args.output, is_file=True, start_page=args.start_page, method=args.method, timeout=args.timeout)
    else:
        crawl_notices(args.url, args.output, is_file=False, start_page=args.start_page, method=args.method, timeout=args.timeout)
