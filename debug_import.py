
try:
    print("Importing scrape_notices...")
    import scrape_notices
    print("Importing article_processor...")
    import article_processor
    print("Importing gui_main...")
    import gui_main
    print("All imported successfully.")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
