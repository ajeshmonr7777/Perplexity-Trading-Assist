# Client Setup Instructions for Perplexity Trading System

This guide will help you set up and run the **Perplexity Trading System** on a macOS system.

## Prerequisites

Before starting, ensure you have **Python 3.9 or higher** installed on your Mac.

1.  Open **Terminal** (Command + Space, type `Terminal`, press Enter).
2.  Check if Python is installed by typing:
    ```bash
    python3 --version
    ```
    If you see a version number (e.g., `Python 3.11.x`), you are good to go.
    If not, download and install it from [python.org](https://www.python.org/downloads/macos/).

## Automated Setup (Recommended)

We have included a setup script to automate the installation process.

1.  Open **Terminal**.
2.  Navigate to the project folder (`cd path/to/folder`).
3.  Fix folder permissions (required after extracting from zip):
    ```bash
    chmod -R u+rwX .
    ```
4.  Run the setup script:
    ```bash
    bash setup_mac.sh
    ```
4.  Follow the on-screen prompts (e.g., enter your API Key).

Once complete, you can start the application using:
```bash
bash start.sh
```

---

## Manual Installation (Alternative)

If you prefer to set up manually or the script fails, follow these steps:

### 1. Create a Virtual Environment
```bash
python3 -m venv venv
```

### 2. Activate the Virtual Environment
```bash
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
1.  Copy `.env.example` to `.env`.
2.  Add your API Key to `.env`.

### 5. Run the Application
```bash
bash start.sh
```

### Alternative Start Command
If the script doesn't work, ensure your virtual environment is activated (`source venv/bin/activate`) and run:
```bash
uvicorn main:app --reload --port 8001
```

## Accessing the Dashboard

Once the application is running, you will see output indicating the server has started (e.g., `Uvicorn running on http://127.0.0.1:8001`).

Open your web browser (Chrome, Safari, etc.) and go to:
[http://localhost:8001](http://localhost:8001)

## Troubleshooting

-   **"Command not found: python3"**: Ensure Python is installed. Try `python` instead of `python3`.
-   **"Module not found" error**: Ensure you activated the virtual environment (`source venv/bin/activate`) before running the app.
-   **Permission denied for start.sh**: Use `bash start.sh` instead of `./start.sh`.
