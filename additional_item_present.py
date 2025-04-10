from flask import Flask, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import re
import pandas as pd

app = Flask(__name__)

# Setup Google Sheets credentials
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(os.environ["GOOGLE_CREDS_JSON"])  # Render environment variable
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)
sheet = client.open("menu").worksheet("additional item menu")
data = sheet.get_all_records()

# Create and clean DataFrame
menu = pd.DataFrame(data)
menu['Name_clean'] = menu['Name'].str.strip().str.lower().apply(lambda x: x[:-1] if x.endswith('s') and not x.endswith('ss') else x)
menu['Category_clean'] = menu['Category'].str.strip().str.lower()

# Utility to singularize words
def singularize(word):
    word = word.strip().lower()
    return word[:-1] if word.endswith('s') and not word.endswith('ss') else word

@app.route('/check_item', methods=['POST'])
def check_item():
    input_data = request.get_json()
    raw_order = input_data.get("order", "").lower()

    # Parse order: e.g., "2 coca colas and 1 red velvet lava cake"
    item_matches = re.findall(r'(\d*)\s*([a-zA-Z ]+?)(?=\s*(?:and|,|$))', raw_order)
    item_names = [singularize(name.strip()) for _, name in item_matches if name.strip()]

    unavailable_responses = []
    all_available = True

    for item in item_names:
        if item in menu['Name_clean'].values:
            continue  # Item available
        all_available = False

        # Try to infer category from name
        guessed_category = ""
        for cat in menu['Category_clean'].unique():
            if cat in item:
                guessed_category = cat
                break

        # Keyword-based fallback
        if not guessed_category:
            if any(word in item for word in ['cola','frooti', 'pepsi', 'juice', 'drink', 'soda', 'water', 'fizz', 'up']):
                guessed_category = 'beverages'
            elif any(word in item for word in ['cake', 'brownie', 'mousse', 'dessert', 'lava', 'ice cream', 'icecream']):
                guessed_category = 'desserts'

        # Suggest items from same category
        if guessed_category:
            suggestions = menu[menu['Category_clean'] == guessed_category]['Name'].unique()
        else:
            suggestions = menu['Name'].unique()

        suggestion_str = ", ".join(sorted(suggestions))
        unavailable_responses.append(
            f"Sorry! The item '{item}' is not available. But instead, we have: {suggestion_str}."
        )

    if all_available:
        return "All items are available!"
    else:
        return "\n".join(unavailable_responses)

@app.route('/')
def home():
    return "✅ Menu Suggestion API is live."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
