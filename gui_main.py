import sys
print(f"Python executable: {sys.executable}")
print("Initializing imports...", flush=True)

try:
    import tkinter as tk
    print("Imported tkinter", flush=True)
    from tkinter import ttk, filedialog, messagebox
    print("Imported tkinter submodules", flush=True)
    import json
    import os
    import threading
    import time
    from datetime import datetime
    print("Imported stdlibs", flush=True)
    
    import scrape_notices
    print("Imported scrape_notices", flush=True)
    
    import article_processor
    print("Imported article_processor", flush=True)
    
    print("Imports successful.", flush=True)
except ImportError as e:
    print(f"Import failed: {e}")
    input("Press Enter to exit...")
    sys.exit(1)
except Exception as e:
    print(f"An error occurred during imports: {e}")
    input("Press Enter to exit...")
    sys.exit(1)

print("Starting gui_main.py...")

CONFIG_FILE = "config.json"
HISTORY_FILE = "history.json"

PRESETS = {
    "官网学校新闻": "https://www.sdxd.edu.cn/page/20190417140037rmry93pvdhwspazvhn.html",
    "官网通知公告": "https://www.sdxd.edu.cn/page/20190417141109v1ewezmjl1uf1hqy9h.html",
    "官网校园动态": "https://www.sdxd.edu.cn/page/20190404194753wvyx0njs7m2gopyk6g.html",
    "官网学术信息": "https://www.sdxd.edu.cn/page/20250519093719belcb0u1xf6h94mj9y.html"
}

class App:
    def __init__(self, root):
        print("App.__init__ started")
        self.root = root
        self.root.title("自动爬虫工具")
        self.root.geometry("600x800") # 增加高度以容纳新界面
        
        self.config = self.load_config()
        self.history = self.load_history()
        self.running_tasks = False
        
        self.create_widgets()
        self.start_scheduler()
        print("App.__init__ finished")

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {"output_dir": os.getcwd(), "tasks": []}

    def save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    # Convert lists back to sets
                    data = json.load(f)
                    return {k: set(v) for k, v in data.items()}
            except:
                pass
        return {}

    def save_history(self):
        # Convert sets to lists for JSON
        data = {k: list(v) for k, v in self.history.items()}
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def create_widgets(self):
        # --- Configuration Frame ---
        config_frame = ttk.LabelFrame(self.root, text="配置", padding=10)
        config_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(config_frame, text="爬取地址:").grid(row=0, column=0, sticky="w")
        self.url_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.url_var, width=50).grid(row=0, column=1, padx=5)
        
        # 预设下拉框 (辅助填入)
        self.preset_combo = ttk.Combobox(config_frame, values=list(PRESETS.keys()), state="readonly", width=15)
        self.preset_combo.grid(row=0, column=2, padx=5)
        self.preset_combo.set("选择预设填入")
        self.preset_combo.bind("<<ComboboxSelected>>", self.on_preset_combo_select)
        
        ttk.Label(config_frame, text="输出目录:").grid(row=1, column=0, sticky="w")
        self.out_dir_var = tk.StringVar(value=self.config.get("output_dir", ""))
        ttk.Entry(config_frame, textvariable=self.out_dir_var, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(config_frame, text="浏览", command=self.browse_dir).grid(row=1, column=2)

        # --- Task Settings Frame ---
        task_frame = ttk.LabelFrame(self.root, text="任务设置", padding=10)
        task_frame.pack(fill="x", padx=10, pady=5)
        
        self.update_only_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(task_frame, text="仅输出更新模式", variable=self.update_only_var).grid(row=0, column=0, sticky="w")
        
        ttk.Label(task_frame, text="定时时间 (HH:MM):").grid(row=0, column=1, padx=10)
        self.time_var = tk.StringVar(value="09:00")
        ttk.Entry(task_frame, textvariable=self.time_var, width=10).grid(row=0, column=2)
        
        ttk.Button(task_frame, text="添加/更新任务", command=self.add_task).grid(row=0, column=3, padx=10)
        ttk.Button(task_frame, text="立即运行", command=self.run_now).grid(row=0, column=4)

        # --- Task List ---
        list_frame = ttk.LabelFrame(self.root, text="任务列表", padding=10)
        list_frame.pack(fill="x", padx=10, pady=5) # 移除 expand=True，固定高度
        
        self.task_list = tk.Listbox(list_frame, height=4) # 减小高度
        self.task_list.pack(fill="both", expand=True)
        self.refresh_task_list()
        
        # --- Word Generation Frame ---
        word_frame = ttk.LabelFrame(self.root, text="Word文档生成 (txt -> docx)", padding=10)
        word_frame.pack(fill="x", padx=10, pady=5)
        
        # Queue Management
        q_frame = tk.Frame(word_frame)
        q_frame.grid(row=0, column=0, columnspan=5, sticky="ew", padx=5, pady=5)
        
        tk.Label(q_frame, text="任务队列:").pack(side="left")
        self.queue_list = tk.Listbox(q_frame, height=4, width=50)
        self.queue_list.pack(side="left", padx=5, fill="x", expand=True)
        
        btn_frame = tk.Frame(q_frame)
        btn_frame.pack(side="left")
        ttk.Button(btn_frame, text="导入TXT文件", command=self.add_files_to_queue).pack(fill="x", pady=1)
        ttk.Button(btn_frame, text="移除选中", command=self.remove_from_queue).pack(fill="x", pady=1)
        ttk.Button(btn_frame, text="清空队列", command=self.clear_queue).pack(fill="x", pady=1)

        # Options
        opt_frame = tk.Frame(word_frame)
        opt_frame.grid(row=1, column=0, columnspan=5, sticky="ew", padx=5)
        
        self.download_images_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, text="下载图片", variable=self.download_images_var).pack(side="left", padx=5)
        
        self.auto_resume_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, text="自动断点续传", variable=self.auto_resume_var).pack(side="left", padx=5)

        ttk.Label(opt_frame, text="分卷大小(MB):").pack(side="left", padx=5)
        self.max_size_var = tk.StringVar(value="100")
        ttk.Entry(opt_frame, textvariable=self.max_size_var, width=5).pack(side="left")

        # Auto Shutdown/Sleep
        ttk.Label(opt_frame, text="完成后:").pack(side="left", padx=5)
        self.after_done_var = tk.StringVar(value="无操作")
        self.after_done_combo = ttk.Combobox(opt_frame, textvariable=self.after_done_var, values=["无操作", "自动关机", "自动休眠"], state="readonly", width=8)
        self.after_done_combo.pack(side="left")

        # Controls
        ctrl_frame = tk.Frame(word_frame)
        ctrl_frame.grid(row=2, column=0, columnspan=5, pady=5)
        
        self.start_btn = ttk.Button(ctrl_frame, text="开始生成 Word", command=self.start_queue_processing)
        self.start_btn.pack(side="left", padx=5)
        
        self.pause_btn = ttk.Button(ctrl_frame, text="暂停", command=self.toggle_pause, state="disabled")
        self.pause_btn.pack(side="left", padx=5)
        
        self.stop_btn = ttk.Button(ctrl_frame, text="停止", command=self.stop_gen, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        # --- Logs ---
        log_frame = ttk.LabelFrame(self.root, text="日志", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_text = tk.Text(log_frame, height=8, state="disabled")
        self.log_text.pack(fill="both", expand=True)

    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_msg = f"[{timestamp}] {message}\n"
        self.log_text.config(state="normal")
        self.log_text.insert("end", full_msg)
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def on_preset_combo_select(self, event):
        name = self.preset_combo.get()
        if name in PRESETS:
            self.url_var.set(PRESETS[name])

    def browse_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.out_dir_var.set(d)
            self.config["output_dir"] = d
            self.save_config()

    def add_task(self):
        url = self.url_var.get().strip()
        time_str = self.time_var.get().strip()
        
        if not url:
            messagebox.showerror("错误", "请输入URL")
            return
            
        # Check if task exists, update it
        task_found = False
        for task in self.config["tasks"]:
            if task["url"] == url:
                task["time"] = time_str
                task["update_only"] = self.update_only_var.get()
                task_found = True
                break
        
        if not task_found:
            self.config["tasks"].append({
                "url": url,
                "time": time_str,
                "update_only": self.update_only_var.get(),
                "last_run": ""
            })
            
        self.save_config()
        self.refresh_task_list()
        self.log(f"任务已添加/更新: {url} at {time_str}")

    def refresh_task_list(self):
        self.task_list.delete(0, "end")
        for task in self.config["tasks"]:
            mode = "增量" if task["update_only"] else "全量"
            self.task_list.insert("end", f"[{task['time']}] {task['url']} ({mode})")

    def run_now(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("错误", "请输入URL")
            return
        
        self.log(f"正在启动抓取任务: {url}")
        threading.Thread(target=self.execute_scrape, args=(url, self.update_only_var.get())).start()

    def execute_scrape(self, url, update_only):
        import scrape_notices
        self.log(f"开始抓取: {url}")
        output_dir = self.out_dir_var.get()
        if not output_dir:
            output_dir = os.getcwd()
            
        # Determine history
        history_set = set()
        if update_only:
            history_set = self.history.get(url, set())
            
        # Generate filename
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"notices_{date_str}.txt"
        filepath = os.path.join(output_dir, filename)
        
        try:
            # Call the scraper
            # Note: We pass None as output_file initially if we want to handle writing ourselves, 
            # but scrape_notices writes to file. Let's let it write to a temp file or just use the filepath.
            # But wait, if update_only is True, scrape_notices logic we added handles filtering.
            # If no new items, it returns empty list.
            
            new_items = scrape_notices.crawl_notices(
                source=url,
                output_file=filepath, # This will contain only new items due to our modification
                is_file=False,
                timeout=30.0,
                history=history_set if update_only else None
            )
            
            if update_only:
                if not new_items:
                    self.log(f"没有新内容: {url}")
                    # Delete the empty file created by scraper if any
                    if os.path.exists(filepath) and os.path.getsize(filepath) == 0:
                        os.remove(filepath)
                    else:
                        # If scraper wrote headers or something, maybe keep it? 
                        # Our scraper writes "Title..." etc. If list is empty, it writes nothing?
                        # Let's check scrape_notices.py: it writes loop over all_notices. If empty, file is empty.
                        if os.path.exists(filepath):
                            os.remove(filepath)
                            
                    # Log special message
                    log_file = os.path.join(output_dir, "scrape_log.txt")
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {url} - 没有新内容\n")
                else:
                    self.log(f"发现 {len(new_items)} 条新内容，已保存至 {filename}")
                    # Update history
                    if url not in self.history:
                        self.history[url] = set()
                    for item in new_items:
                        self.history[url].add(item['link'])
                    self.save_history()
            else:
                self.log(f"全量抓取完成，共 {len(new_items)} 条，保存至 {filename}")
                # Update history with everything?
                if url not in self.history:
                    self.history[url] = set()
                for item in new_items:
                    self.history[url].add(item['link'])
                self.save_history()

        except Exception as e:
            self.log(f"抓取失败: {e}")
        finally:
            self.clean_environment(output_dir)

    def clean_environment(self, output_dir):
        # 清理当前目录下的 debug html 文件
        cwd = os.getcwd()
        for file in os.listdir(cwd):
            if file.startswith("debug_") and file.endswith(".html"):
                try:
                    os.remove(os.path.join(cwd, file))
                except:
                    pass
        
        # 也可以清理输出目录下的非 txt 文件 (如果用户希望严格清理)
        # 但为了安全起见，我们只清理明确的临时文件模式
        # 如果之前有残留的 debug 文件在 output_dir (如果 output_dir == cwd)
        if output_dir != cwd and os.path.exists(output_dir):
             for file in os.listdir(output_dir):
                if file.startswith("debug_") and file.endswith(".html"):
                    try:
                        os.remove(os.path.join(output_dir, file))
                    except:
                        pass

    def start_scheduler(self):
        self.running_tasks = True
        threading.Thread(target=self.scheduler_loop, daemon=True).start()

    def scheduler_loop(self):
        while self.running_tasks:
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            
            # Check tasks
            # To avoid running multiple times in the same minute, we need a flag or check seconds
            # Simple way: check if seconds == 0, sleep 1. Or store last run date.
            
            for task in self.config["tasks"]:
                if task["time"] == current_time:
                    last_run = task.get("last_run", "")
                    today = now.strftime("%Y-%m-%d")
                    
                    if last_run != today:
                        self.log(f"执行定时任务: {task['url']}")
                        # Run in a separate thread to not block scheduler
                        threading.Thread(target=self.execute_scrape, args=(task["url"], task["update_only"])).start()
                        
                        task["last_run"] = today
                        self.save_config()
            
            time.sleep(30) # Check every 30 seconds

    def add_files_to_queue(self):
        files = filedialog.askopenfilenames(filetypes=[("Text Files", "*.txt")])
        for f in files:
            # Check if already in queue
            if f not in self.queue_list.get(0, "end"):
                self.queue_list.insert("end", f)

    def remove_from_queue(self):
        selection = self.queue_list.curselection()
        if selection:
            # Remove in reverse order to maintain indices
            for index in reversed(selection):
                self.queue_list.delete(index)

    def clear_queue(self):
        self.queue_list.delete(0, "end")

    def start_queue_processing(self):
        queue_files = self.queue_list.get(0, "end")
        if not queue_files:
            messagebox.showerror("错误", "队列为空，请先添加文件")
            return
            
        try:
            max_size = float(self.max_size_var.get())
        except ValueError:
            messagebox.showerror("错误", "请输入有效的大小数值")
            return

        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        
        self.start_btn.config(state="disabled")
        self.pause_btn.config(state="normal", text="暂停")
        self.stop_btn.config(state="normal")

        threading.Thread(target=self.run_queue_thread, args=(queue_files, max_size)).start()

    def run_queue_thread(self, queue_files, max_size):
        download_images = self.download_images_var.get()
        auto_resume = self.auto_resume_var.get()
        after_done = self.after_done_var.get()
        
        for i, txt_path in enumerate(queue_files):
            if self.stop_event.is_set():
                break
                
            if not os.path.exists(txt_path):
                self.log(f"文件不存在，跳过: {txt_path}")
                continue
                
            self.log(f"=== 开始处理队列文件 ({i+1}/{len(queue_files)}): {os.path.basename(txt_path)} ===")
            
            # Determine output path (auto-generated)
            dir_name = os.path.dirname(txt_path)
            base_name = os.path.splitext(os.path.basename(txt_path))[0]
            output_path = os.path.join(dir_name, f"{base_name}.docx")
            
            # Determine start index
            start_index = 1
            state_file = "word_gen_state.json"
            if auto_resume and os.path.exists(state_file):
                try:
                    with open(state_file, "r", encoding="utf-8") as f:
                        state = json.load(f)
                    saved_index = state.get(txt_path, 0)
                    if saved_index > 1:
                        start_index = saved_index
                        self.log(f"自动恢复进度: 从第 {start_index} 篇开始")
                except Exception as e:
                    print(f"读取进度失败: {e}")

            try:
                import article_processor
                items = article_processor.parse_txt_file(txt_path)
                self.log(f"解析到 {len(items)} 篇文章")
                
                if start_index > len(items):
                    self.log(f"已完成 (进度记录 {start_index} > 总数 {len(items)})，跳过。如需重新生成请取消'自动断点续传'。")
                    continue

                def progress(current, total, title):
                    # 更新 UI
                    if current % 1 == 0 or current == total or title.startswith("已保存") or title == "任务已终止":
                         self.log(f"[{i+1}/{len(queue_files)}] {current}/{total} - {title}")
                    
                    # 保存进度
                    if not title.startswith("正在") and not title.startswith("已保存") and title != "任务已终止":
                        try:
                            state_file = "word_gen_state.json"
                            state = {}
                            if os.path.exists(state_file):
                                with open(state_file, "r", encoding="utf-8") as f:
                                    state = json.load(f)
                            
                            # 保存下一篇的索引
                            state[txt_path] = current + 1
                            
                            with open(state_file, "w", encoding="utf-8") as f:
                                json.dump(state, f, ensure_ascii=False, indent=2)
                        except Exception as e:
                            print(f"保存进度失败: {e}")

                article_processor.generate_word_doc(items, output_path, max_size, progress, self.stop_event, self.pause_event, start_index, download_images)
                
                if self.stop_event.is_set():
                    self.log(f"队列处理已终止于: {os.path.basename(txt_path)}")
                    break
                else:
                    self.log(f"文件处理完成: {output_path}")
                    
            except Exception as e:
                self.log(f"处理文件失败 {txt_path}: {e}")
                
        self.log("=== 队列处理结束 ===")
        
        if not self.stop_event.is_set():
            if after_done == "自动关机":
                self.log("任务完成，60秒后自动关机...")
                os.system("shutdown /s /t 60")
            elif after_done == "自动休眠":
                self.log("任务完成，正在进入休眠...")
                os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

        self.root.after(0, self.reset_buttons)

    def toggle_pause(self):
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.pause_btn.config(text="暂停")
            self.log("任务继续...")
        else:
            self.pause_event.set()
            self.pause_btn.config(text="继续")
            self.log("任务已暂停")

    def stop_gen(self):
        if messagebox.askyesno("确认", "确定要停止任务吗？\n(程序将完成当前文章后停止)"):
            self.stop_event.set()
            self.log("正在停止任务 (将在当前文章完成后停止)...")

    # def run_word_gen(self, txt_path, output_path, max_size, start_index):
    #    ... (Removed, replaced by run_queue_thread)

    def reset_buttons(self):
        self.start_btn.config(state="normal")
        self.pause_btn.config(state="disabled", text="暂停")
        self.stop_btn.config(state="disabled")

if __name__ == "__main__":
    print("Entering main block...")
    try:
        print("Creating Tk instance...")
        root = tk.Tk()
        print("Tk created.")
        app = App(root)
        print("App created. Starting mainloop.")
        root.mainloop()
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
