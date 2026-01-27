"""
Excel File ID Retrieval Script
Helps find the OneDrive file ID for an Excel file.

Usage:
    python scripts/get_excel_file_id.py

Prerequisites:
    - MICROSOFT_CLIENT_ID
    - MICROSOFT_CLIENT_SECRET
    - MICROSOFT_REFRESH_TOKEN (from setup_microsoft_auth.py)
"""

import os
import sys

try:
    import requests
except ImportError:
    print("Error: requests package not installed. Run: pip install requests")
    sys.exit(1)

try:
    import msal
except ImportError:
    print("Error: msal package not installed. Run: pip install msal")
    sys.exit(1)

# Configuration
CLIENT_ID = os.getenv('MICROSOFT_CLIENT_ID', '')
CLIENT_SECRET = os.getenv('MICROSOFT_CLIENT_SECRET', '')
TENANT_ID = os.getenv('MICROSOFT_TENANT_ID', 'consumers')
REFRESH_TOKEN = os.getenv('MICROSOFT_REFRESH_TOKEN', '')
SCOPES = ['Files.ReadWrite', 'User.Read']


def get_access_token():
    """Get access token using refresh token."""
    authority = f"https://login.microsoftonline.com/{TENANT_ID}"
    app = msal.ConfidentialClientApplication(
        client_id=CLIENT_ID,
        client_credential=CLIENT_SECRET,
        authority=authority,
    )

    result = app.acquire_token_by_refresh_token(
        refresh_token=REFRESH_TOKEN,
        scopes=SCOPES
    )

    if 'access_token' in result:
        return result['access_token']
    else:
        error = result.get('error_description', result.get('error', 'Unknown error'))
        print(f"ERROR: Failed to get token: {error}")
        return None


def list_excel_files(token):
    """List Excel files in OneDrive."""
    headers = {'Authorization': f'Bearer {token}'}

    # Search for Excel files
    url = "https://graph.microsoft.com/v1.0/me/drive/root/search(q='.xlsx')"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"ERROR: Failed to search files: {response.text}")
        return []

    data = response.json()
    return data.get('value', [])


def search_file_by_name(token, filename):
    """Search for a specific file by name."""
    headers = {'Authorization': f'Bearer {token}'}

    # Search for the file
    url = f"https://graph.microsoft.com/v1.0/me/drive/root/search(q='{filename}')"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"ERROR: Failed to search: {response.text}")
        return []

    data = response.json()
    return data.get('value', [])


def main():
    print("=" * 60)
    print("Excel File ID Finder for Breaktime Tracker")
    print("=" * 60)
    print()

    # Check configuration
    if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
        print("ERROR: Missing environment variables")
        print()
        print("Required variables:")
        print("  - MICROSOFT_CLIENT_ID")
        print("  - MICROSOFT_CLIENT_SECRET")
        print("  - MICROSOFT_REFRESH_TOKEN")
        print()
        print("Run setup_microsoft_auth.py first to get the refresh token.")
        return

    # Get access token
    print("Getting access token...")
    token = get_access_token()
    if not token:
        return

    print("Token obtained successfully!")
    print()

    # Ask user what to do
    print("Options:")
    print("1. List all Excel files in OneDrive")
    print("2. Search for a specific file by name")
    print()

    choice = input("Enter choice (1 or 2): ").strip()

    if choice == '1':
        print()
        print("Searching for Excel files...")
        files = list_excel_files(token)

        if not files:
            print("No Excel files found in OneDrive.")
            return

        print()
        print(f"Found {len(files)} Excel file(s):")
        print("-" * 60)

        for i, file in enumerate(files, 1):
            name = file.get('name', 'Unknown')
            file_id = file.get('id', 'Unknown')
            modified = file.get('lastModifiedDateTime', 'Unknown')
            web_url = file.get('webUrl', '')

            print(f"\n{i}. {name}")
            print(f"   File ID: {file_id}")
            print(f"   Modified: {modified}")
            if web_url:
                print(f"   URL: {web_url}")

        print()
        print("-" * 60)
        print()
        print("Copy the File ID for your .env file:")
        print("  EXCEL_FILE_ID=<file-id-here>")

    elif choice == '2':
        filename = input("Enter filename to search (e.g., 'Breaktime' or 'BreakLog'): ").strip()

        if not filename:
            print("No filename provided.")
            return

        print()
        print(f"Searching for '{filename}'...")
        files = search_file_by_name(token, filename)

        if not files:
            print(f"No files found matching '{filename}'.")
            return

        print()
        print(f"Found {len(files)} matching file(s):")
        print("-" * 60)

        for i, file in enumerate(files, 1):
            name = file.get('name', 'Unknown')
            file_id = file.get('id', 'Unknown')
            modified = file.get('lastModifiedDateTime', 'Unknown')

            print(f"\n{i}. {name}")
            print(f"   File ID: {file_id}")
            print(f"   Modified: {modified}")

        print()
        print("-" * 60)
        print()
        print("Copy the File ID for your .env file:")
        print("  EXCEL_FILE_ID=<file-id-here>")

    else:
        print("Invalid choice.")


if __name__ == '__main__':
    main()
