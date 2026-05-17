import cloudscraper
import urllib3
from bs4 import BeautifulSoup
import json
import time
import os
import re

# Disable insecure request warnings for proxy usage
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_ijcv_by_volume():
    # Base URL for Springer
    base_url = "https://link.springer.com"
    
    # Get volume from user
    volume = input("Enter the Volume number (e.g., 134): ").strip()
    if not volume:
        print("Volume number is required.")
        return
    
    output_filename = f'IJCV_Volume_{volume}.json'
    
    # Base URL for specific volume
    base_url_volume = f"https://link.springer.com/journal/11263/articles?filter-by-volume={volume}&sortBy=newestFirst"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    proxies = {
        "http": "http://127.0.0.1:7890",
        "https": "http://127.0.0.1:7890"
    }

    # Load existing data for resume functionality
    papers = []
    start_page = 1
    if os.path.exists(output_filename):
        try:
            with open(output_filename, 'r', encoding='utf-8') as f:
                papers = json.load(f)
            print(f"Loaded {len(papers)} existing papers from {output_filename}.")
            
            resume_input = input(f"Existing file found. Enter start page number (default 1): ").strip()
            if resume_input:
                start_page = int(resume_input)
        except Exception as e:
            print(f"Error loading existing file: {e}. Starting from scratch.")

    # Use cloudscraper to bypass potential protection
    scraper = cloudscraper.create_scraper()
    page = start_page

    print(f"Starting to scrape IJCV Volume {volume} (Starting from page {page})...")

    try:
        while True:
            print(f"\n--- Fetching Volume {volume}, page {page} ---")
            url = f"{base_url_volume}&page={page}"
            
            max_retries = 3
            response = None
            for attempt in range(max_retries):
                try:
                    response = scraper.get(url, headers=headers, proxies=proxies, timeout=20)
                    response.raise_for_status()
                    break
                except Exception as e:
                    print(f"Attempt {attempt + 1} failed for page {page}: {e}")
                    if attempt == max_retries - 1:
                        print("Max retries reached.")
                        raise Exception("Failed to fetch page after max retries.")
                    time.sleep(3)
            
            if not response or response.status_code != 200:
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all article items
            items = soup.select('li[data-test="article-item"]')
            if not items:
                items = soup.find_all('article') or soup.select('.c-list-group__item')

            current_page_links = []
            for item in items:
                link_tag = item.find('a', href=True)
                if not link_tag: continue
                
                href = link_tag['href']
                if '/article/10.1007/s11263-' in href:
                    full_url = href if href.startswith('http') else base_url + href
                    if full_url not in current_page_links:
                        current_page_links.append(full_url)

            if not current_page_links:
                print(f"No articles detected on page {page}.")
                break

            print(f"Found {len(current_page_links)} potential article links on page {page}.")

            new_articles_on_page = 0
            for link in current_page_links:
                # Deduplication
                if any(p['url'] == link for p in papers):
                    print(f"  Skipping existing article: {link}")
                    continue

                print(f"  Fetching details for {link}...")
                for attempt in range(max_retries):
                    try:
                        res = scraper.get(link, headers=headers, proxies=proxies, timeout=20)
                        res.raise_for_status()
                        article_soup = BeautifulSoup(res.text, 'html.parser')
                        
                        # Title
                        title_tag = article_soup.find('h1', class_='c-article-title')
                        title = title_tag.text.strip() if title_tag else "Unknown Title"
                        
                        # Authors
                        author_tags = article_soup.find_all('li', class_='c-author-list__item')
                        authors = []
                        for author in author_tags:
                            name_tag = author.find('a', {'data-test': 'author-name'})
                            if name_tag:
                                authors.append(name_tag.text.strip())
                        if not authors:
                            alt_authors = article_soup.find_all('a', class_='c-article-author-affiliation__authors-link')
                            authors = [a.text.strip() for a in alt_authors]
                        
                        # Abstract
                        abstract_tag = article_soup.find('div', id='Abs1-content')
                        if not abstract_tag:
                            abstract_tag = article_soup.find('section', class_='Abstract')
                        abstract = abstract_tag.text.strip() if abstract_tag else "No Abstract Available"
                        
                        # Metadata (Year/Volume/Issue)
                        year = None
                        meta_date = article_soup.find('meta', attrs={'name': 'citation_publication_date'})
                        if meta_date and meta_date.get('content'):
                            year_match = re.search(r'20\d{2}', meta_date['content'])
                            if year_match:
                                year = int(year_match.group())
                        
                        papers.append({
                            "title": title,
                            "authors": authors,
                            "abstract": abstract,
                            "url": link,
                            "year": year,
                            "volume": volume
                        })
                        new_articles_on_page += 1
                        time.sleep(1)
                        break
                        
                    except Exception as e:
                        print(f"    Attempt {attempt + 1} failed for {link}: {e}")
                        time.sleep(2)

            # Save progress
            if new_articles_on_page > 0:
                with open(output_filename, 'w', encoding='utf-8') as f:
                    json.dump(papers, f, ensure_ascii=False, indent=4)
                print(f"Saved {len(papers)} papers so far.")

            # Check for next page
            next_page_link = soup.select_one('a[rel="next"]') or soup.find('a', string=re.compile(r'Next', re.I))
            if not next_page_link:
                print("No next page button. Finished volume.")
                break
            
            page += 1
            if page > 100: # Max pages per volume usually isn't that high
                break

    except KeyboardInterrupt:
        print("\nScraping interrupted by user. Progress saved.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(papers, f, ensure_ascii=False, indent=4)
        print(f"\nFinal: Successfully scraped {len(papers)} papers from Volume {volume}.")

if __name__ == "__main__":
    fetch_ijcv_by_volume()
