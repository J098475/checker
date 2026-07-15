# Job Listing Scraper & Gmail Notifier

A lightweight, serverless job scraper that runs automatically on a cron schedule using GitHub Actions. It tracks new job postings, updates a state file (`seen_jobs.json`) to prevent duplicate notifications, and sends beautifully styled HTML email alerts via Gmail.

---

## 🛠️ Features

- **Automated Scheduling**: Runs once daily (or on your custom cron schedule) via GitHub Actions.
- **Config-Driven**: Easily add or modify job sources in `config.json` with custom CSS selectors.
- **Duplicate Prevention**: Keeps track of already-seen job listings in `seen_jobs.json` by committing state updates back to your repository.
- **Responsive HTML Emails**: Delivers clean, premium-looking job alert emails using Gmail SMTP.
- **Dry-Run Mode**: Safely tests your scraping selectors locally without requiring email credentials.

---

## 📋 Setup Instructions

### 1. Generate a Gmail App Password
To allow the script to send emails via Gmail SMTP, you must generate a secure **App Password**:
1. Go to your [Google Account Settings](https://myaccount.google.com/).
2. Select **Security** on the left menu.
3. Under *How you sign in to Google*, ensure **2-Step Verification** is enabled.
4. Click on **2-Step Verification**, scroll to the bottom, and select **App passwords**.
5. Enter a name (e.g., `GitHub Job Scraper`) and click **Create**.
6. Copy the **16-character password** generated (you will not be able to see it again).

---

### 2. Configure GitHub Secrets
In your GitHub repository where you host this script, set up the secret variables:
1. Go to your repository on GitHub.
2. Navigate to **Settings** -> **Secrets and variables** -> **Actions**.
3. Click **New repository secret** and add the following three secrets:
   - `GMAIL_SENDER`: The Gmail address used to send the emails (e.g., `your-email@gmail.com`).
   - `GMAIL_PASSWORD`: The 16-character App Password you generated in Step 1 (without spaces).
   - `GMAIL_RECEIVER`: The email address where you want to receive the job alerts (can be the same as `GMAIL_SENDER`).

---

### 3. Adjusting Settings (Optional)
- **Schedule**: The workflow is set to run once daily at 12:00 PM UTC. You can change this by modifying the `cron` expression in [.github/workflows/scrape.yml](file://./.github/workflows/scrape.yml):
  ```yaml
  on:
    schedule:
      - cron: '0 12 * * *' # e.g. change to your preferred time
  ```
- **Job Sources**: Add new URLs and CSS selectors inside [config.json](file://./config.json).

---

## 💻 Local Testing & Development

You can run the script locally to test your scrapers. If the environment variables are not set, it automatically executes in **Dry-Run Mode** (printing the output to the console instead of sending an email).

1. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the scraper:
   ```bash
   python scraper.py
   ```
