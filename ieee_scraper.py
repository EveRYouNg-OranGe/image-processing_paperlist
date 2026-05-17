import requests
import json
import time
import os
import urllib3

# Disable insecure request warnings for proxy usage
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def scrape_ieee_journal():
    print("=== IEEE Xplore Scraper (TMM & TIP) ===")
    
    # Selection of Journal
    print("Select Journal:")
    print("1. TMM (Transactions on Multimedia) - punumber: 6046")
    print("2. TIP (Transactions on Image Processing) - punumber: 83")
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == '1':
        punumber = "6046"
        journal_name = "TMM"
    elif choice == '2':
        punumber = "83"
        journal_name = "TIP"
    else:
        print("Invalid choice.")
        return

    isnumber = input(f"Enter the isnumber (Issue ID) for {journal_name}: ").strip()
    if not isnumber:
        print("isnumber is required.")
        return

    output_filename = f"IEEE_{journal_name}_{isnumber}.json"
    
    # Proxy configuration
    proxies = {
        "http": "http://127.0.0.1:7890",
        "https": "http://127.0.0.1:7890"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://ieeexplore.ieee.org",
        "Referer": f"https://ieeexplore.ieee.org/xpl/tocresult.jsp?isnumber={isnumber}&punumber={punumber}"
    }

    # Internal REST API endpoint
    search_url = "https://ieeexplore.ieee.org/rest/search"
    
    papers = []
    page_number = 1
    
    print(f"Starting to scrape {journal_name} issue {isnumber}...")

    try:
        while True:
            print(f"Fetching page {page_number}...")
            
            payload = {
                "isnumber": isnumber,
                "punumber": punumber,
                "sortType": "vol-only-seq",
                "rowsPerPage": "100",
                "pageNumber": str(page_number)
            }

            response = requests.post(search_url, json=payload, headers=headers, proxies=proxies, timeout=20, verify=False)
            response.raise_for_status()
            data = response.json()
            
            records = data.get("records", [])
            if not records:
                print("No more records found.")
                break
            
            print(f"Found {len(records)} records on page {page_number}.")
            
            for record in records:
                title = record.get("articleTitle", "Unknown Title")
                authors_data = record.get("authors", [])
                authors = [a.get("preferredName") for a in authors_data]
                
                # Check if abstract is in the record. 
                # Sometimes it's 'abstract', sometimes it's missing and needs a separate call.
                abstract = record.get("abstract", "")
                
                # If abstract is missing or too short (often a snippet), we might need to fetch it
                article_number = record.get("articleNumber")
                
                if not abstract and article_number:
                    # Optional: Fetch detailed abstract if TOC record doesn't have it
                    # But TOC records usually have it in IEEE Xplore JSON responses
                    pass
                
                papers.append({
                    "title": title,
                    "authors": authors,
                    "abstract": abstract,
                    "url": f"https://ieeexplore.ieee.org/document/{article_number}/",
                    "doi": record.get("doi"),
                    "articleNumber": article_number
                })

            # Check if there are more pages
            total_records = data.get("totalRecords", 0)
            if len(papers) >= total_records:
                break
            
            page_number += 1
            time.sleep(2) # Be respectful

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if papers:
            with open(output_filename, 'w', encoding='utf-8') as f:
                json.dump(papers, f, ensure_ascii=False, indent=4)
            print(f"Successfully saved {len(papers)} papers to {output_filename}")
        else:
            print("No papers were scraped.")

if __name__ == "__main__":
    scrape_ieee_journal()
