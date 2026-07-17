import os
import sys
import json
import smtplib
import urllib.parse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from bs4 import BeautifulSoup

# Configurable paths
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')
SEEN_JOBS_PATH = os.path.join(os.path.dirname(__file__), 'seen_jobs.json')

def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"Error: Configuration file not found at {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def load_seen_jobs():
    if os.path.exists(SEEN_JOBS_PATH):
        try:
            with open(SEEN_JOBS_PATH, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Warning: seen_jobs.json was corrupted. Re-initializing.")
            return {}
    return {}

def save_seen_jobs(seen_jobs):
    with open(SEEN_JOBS_PATH, 'w') as f:
        json.dump(seen_jobs, f, indent=2)

def scrape_html(source):
    name = source.get('name', 'Unknown Source')
    url = source.get('url')
    selectors = source.get('selectors', {})
    filters = source.get('filters', {})
    keywords = source.get('keywords', [])
    
    if not url:
        print(f"Warning: No URL specified for HTML source '{name}'. Skipping.")
        return []
    
    print(f"Scraping HTML source '{name}' from {url}...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching page for '{name}': {e}")
        return []
        
    soup = BeautifulSoup(response.text, 'html.parser')
    
    job_container_sel = selectors.get('job_container')
    title_sel = selectors.get('title')
    link_sel = selectors.get('link')
    location_sel = selectors.get('location')
    
    if not job_container_sel:
        print(f"Error: Missing job_container selector for '{name}'")
        return []
        
    containers = soup.select(job_container_sel)
    print(f"Found {len(containers)} total job listing container(s) on the page.")
    
    jobs = []
    for container in containers:
        # Apply HTML attribute filters if present (e.g. data-department, data-office)
        if filters:
            matched_filters = True
            for attr, val in filters.items():
                if container.get(attr) != val:
                    matched_filters = False
                    break
            if not matched_filters:
                continue

        # Extract title
        title_el = container.select_one(title_sel) if title_sel else None
        title = title_el.text.strip() if title_el else "Unknown Title"
        
        # Extract link
        if link_sel == 'a' and container.name == 'a':
            link_el = container
        else:
            link_el = container.select_one(link_sel) if link_sel else None
            
        href = link_el.get('href') if link_el else None
        link = urllib.parse.urljoin(url, href) if href else ""
        
        # Extract location
        location_el = container.select_one(location_sel) if location_sel else None
        location = location_el.text.strip() if location_el else "Unknown Location"
        
        # Apply keyword matching if keywords list is provided
        if keywords:
            search_text = f"{title} {location}".lower()
            if not any(k.lower() in search_text for k in keywords):
                continue

        if link:
            jobs.append({
                'title': title,
                'link': link,
                'location': location,
                'source': name
            })
            
    print(f"Matched {len(jobs)} job(s) after applying filters and keywords.")
    return jobs

def scrape_workday(source):
    name = source.get('name', 'Unknown Source')
    url = source.get('url')
    web_url = source.get('web_url')
    payload = source.get('payload', {})
    keywords = source.get('keywords', [])
    
    if not url or not web_url:
        print(f"Warning: Missing url or web_url for Workday source '{name}'. Skipping.")
        return []
        
    print(f"Scraping Workday source '{name}' from {url}...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error fetching API for Workday source '{name}': {e}")
        return []
        
    job_postings = data.get('jobPostings', [])
    print(f"Found {len(job_postings)} total job listing(s) in API response.")
    
    jobs = []
    base_web_url = web_url if web_url.endswith('/') else web_url + '/'
    
    for job_data in job_postings:
        title = job_data.get('title', 'Unknown Title')
        
        external_path = job_data.get('externalPath', '').lstrip('/')
        link = urllib.parse.urljoin(base_web_url, external_path) if external_path else ""
        
        # Location is usually in bulletFields
        bullet_fields = job_data.get('bulletFields', [])
        location = ", ".join(bullet_fields) if bullet_fields else "Unknown Location"
        
        # Apply keyword matching if keywords list is provided
        if keywords:
            search_text = f"{title} {location}".lower()
            if not any(k.lower() in search_text for k in keywords):
                continue
                
        if link:
            jobs.append({
                'title': title,
                'link': link,
                'location': location,
                'source': name
            })
            
    print(f"Matched {len(jobs)} job(s) after applying filters and keywords.")
    return jobs

def scrape_source(source):
    source_type = source.get('type', 'html')
    if source_type == 'workday':
        return scrape_workday(source)
    else:
        return scrape_html(source)

def format_email_body(new_jobs):
    job_cards_html = ""
    for job in new_jobs:
        job_cards_html += f"""
        <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
            <h3 style="margin-top: 0; margin-bottom: 8px; color: #0f172a; font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 18px; font-weight: 600;">
                {job['title']}
            </h3>
            <p style="margin: 0 0 12px 0; color: #64748b; font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 14px;">
                <strong>📍 Location:</strong> {job['location']} | <strong>🏢 Source:</strong> {job['source']}
            </p>
            <a href="{job['link']}" target="_blank" style="display: inline-block; background-color: #2563eb; color: #ffffff; text-decoration: none; padding: 8px 16px; border-radius: 6px; font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 14px; font-weight: 500;">
                View Job &rarr;
            </a>
        </div>
        """
        
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>New Job Postings Alert</title>
    </head>
    <body style="background-color: #f8fafc; margin: 0; padding: 20px; font-family: 'Helvetica Neue', Arial, sans-serif; -webkit-font-smoothing: antialiased;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
            <!-- Header Banner -->
            <div style="background: linear-gradient(135deg, #1e3a8a, #3b82f6); padding: 30px 20px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -0.025em;">
                    💼 Job Posting Alert
                </h1>
                <p style="color: #bfdbfe; margin: 8px 0 0 0; font-size: 14px;">
                    We found {len(new_jobs)} new listings matching your criteria!
                </p>
            </div>
            
            <!-- Content -->
            <div style="padding: 24px; background-color: #f8fafc;">
                {job_cards_html}
            </div>
            
            <!-- Footer -->
            <div style="padding: 20px; text-align: center; background-color: #f1f5f9; border-top: 1px solid #e2e8f0;">
                <p style="margin: 0; color: #94a3b8; font-size: 12px; line-height: 1.5;">
                    This email was sent automatically by your GitHub Actions Job Scraper.<br>
                    To configure sources, update the config.json file in your repository.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    return html

def send_email(new_jobs):
    sender = os.environ.get('GMAIL_SENDER')
    password = os.environ.get('GMAIL_PASSWORD')
    receiver = os.environ.get('GMAIL_RECEIVER')
    
    if not sender or not password or not receiver:
        print("\n--- DRY RUN ---")
        print("Missing GMAIL_SENDER, GMAIL_PASSWORD, or GMAIL_RECEIVER environment variables.")
        print(f"Would have sent email to: {receiver or 'Not Configured'}")
        print(f"Content contains {len(new_jobs)} new jobs:")
        for job in new_jobs:
            print(f"- {job['title']} in {job['location']} ({job['link']})")
        print("----------------\n")
        return False
        
    print(f"Sending email to {receiver}...")
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"🔔 {len(new_jobs)} New Job Posting(s) Found!"
    msg['From'] = sender
    msg['To'] = receiver
    
    # Plain text alternative
    text = f"We found {len(new_jobs)} new job postings:\n\n"
    for job in new_jobs:
        text += f"- {job['title']}\n  Location: {job['location']}\n  Source: {job['source']}\n  Link: {job['link']}\n\n"
        
    html = format_email_body(new_jobs)
    
    msg.attach(MIMEText(text, 'plain'))
    msg.attach(MIMEText(html, 'html'))
    
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
        print("Email sent successfully!")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def main():
    config = load_config()
    seen_jobs = load_seen_jobs()
    
    all_scraped_jobs = []
    for source in config.get('sources', []):
        jobs = scrape_source(source)
        all_scraped_jobs.extend(jobs)
        
    print(f"Scraped a total of {len(all_scraped_jobs)} job listing(s) matching initial criteria.")
    
    new_jobs = []
    for job in all_scraped_jobs:
        job_key = job['link']  # Use absolute URL as the unique key
        if job_key not in seen_jobs:
            new_jobs.append(job)
            
    if not new_jobs:
        print("No new job postings found since the last check.")
        return
        
    print(f"Found {len(new_jobs)} new job posting(s)!")
    
    # Attempt to send email
    email_sent = send_email(new_jobs)
    
    is_dry_run = not os.environ.get('GMAIL_SENDER') or not os.environ.get('GMAIL_PASSWORD')
    
    if email_sent or is_dry_run:
        # Mark jobs as seen
        for job in new_jobs:
            seen_jobs[job['link']] = {
                'title': job['title'],
                'location': job['location'],
                'source': job['source']
            }
        save_seen_jobs(seen_jobs)
        print("Updated seen_jobs.json database.")

if __name__ == '__main__':
    main()
