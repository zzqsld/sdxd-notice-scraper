# SDXD Notice Scraper

山东现代学院通知公告自动抓取与 Word 生成工具。

## 功能特点

*   **自动抓取**: 自动爬取学校官网的通知公告、新闻等内容。
*   **格式转换**: 将网页内容自动转换为 Word 文档 (.docx)，保留图片和基本格式。
*   **增量更新**: 支持记录历史抓取记录，只抓取新发布的文章。
*   **GUI 界面**: 提供图形化界面 (`gui_main.py`)，方便本地操作和任务管理。
*   **自动化运行**: 集成 GitHub Actions，每天定时自动运行爬虫并生成文档。

## 快速开始

### 本地运行

1.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **运行 GUI**:
    ```bash
    python gui_main.py
    ```
    在界面中配置抓取链接和输出目录，点击“立即运行”或设置定时任务。

### GitHub Actions 自动化

本项目配置了 GitHub Actions 工作流 (`.github/workflows/scrape.yml`)，可以实现：

1.  每天定时 (UTC 9:00) 自动运行爬虫。
2.  检查是否有新文章。
3.  如果有新文章，自动生成 Word 文档并提交到仓库的 `output/` 目录。
4.  更新 `history.json` 以记录已抓取的文章。

**启用方法**:
1.  Fork 或 Clone 本仓库。
2.  在 GitHub 仓库的 "Actions" 标签页中启用 Workflow。
3.  (可选) 手动触发 Workflow 进行测试。

## 文件说明

*   `gui_main.py`: 主程序 GUI 入口。
*   `scrape_notices.py`: 爬虫核心逻辑。
*   `article_processor.py`: 文章处理与 Word 生成逻辑。
*   `headless_runner.py`: 用于 GitHub Actions 的无头模式运行脚本。
*   `requirements.txt`: 项目依赖列表。

## 许可证

本项目采用 [GPL-3.0 许可证](LICENSE)。
