# -*- coding: utf-8 -*-
"""
Arachudar Blogger OAuth Token Generator
Generates permanent refresh token and saves to blogger_token.json
"""

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/blogger']

def main():
    print("=======================================================")
    print("   அறச்சுடர் (Arachudar) Blogger OAuth Setup Wizard")
    print("=======================================================")
    
    # Check if client_secrets.json exists
    if os.path.exists("client_secrets.json"):
        print("\nFound 'client_secrets.json'! Starting authorization flow...")
        flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
    else:
        # Allow user to paste Client ID and Secret directly if they didn't download json
        print("\n'client_secrets.json' was not found.")
        print("You can paste your Client ID and Client Secret below,")
        print("or place 'client_secrets.json' in this folder and re-run.\n")
        
        client_id = input("Enter your Client ID: ").strip()
        client_secret = input("Enter your Client Secret: ").strip()
        
        if not client_id or not client_secret:
            print("\nError: Client ID and Secret are required.")
            return

        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"]
            }
        }
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)

    print("\nOpening your web browser for one-click Google authorization...")
    print("Please log in with 'arachudarnews@gmail.com' and grant permissions.\n")
    
    try:
        creds = flow.run_local_server(port=0)
    except Exception as e:
        print(f"Authorization error: {e}")
        return

    # Save credentials with permanent refresh token
    token_data = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': list(creds.scopes)
    }

    with open('blogger_token.json', 'w', encoding='utf-8') as f:
        json.dump(token_data, f, indent=2)

    print("\nSUCCESS: Permanent refresh token saved to 'blogger_token.json'!")

    # Fetch available blogs and print Blog ID
    try:
        service = build('blogger', 'v3', credentials=creds)
        user_blogs = service.users().blogs().listByUser(userId='self').execute()
        
        print("\n=======================================================")
        print("   Your Connected Blogger Sites:")
        print("=======================================================")
        items = user_blogs.get('items', [])
        if not items:
            print("No blogs found under this account.")
        for b in items:
            print(f"Blog Name: {b.get('name')}")
            print(f"Blog ID:   {b.get('id')}")
            print(f"Blog URL:  {b.get('url')}")
            print("-------------------------------------------------------")
            
            # Save the first blog ID into config for easy reference
            config = {"blog_id": b.get('id'), "blog_name": b.get('name'), "blog_url": b.get('url')}
            with open('blogger_config.json', 'w', encoding='utf-8') as cf:
                json.dump(config, cf, indent=2)
            print("Saved primary Blog ID to 'blogger_config.json'!")
            
    except Exception as e:
        print(f"Could not list blogs: {e}")

if __name__ == '__main__':
    main()
