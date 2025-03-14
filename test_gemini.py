import os
from dotenv import load_dotenv
import requests
import json

# Load environment variables
load_dotenv()

# Get and print the API key (first few characters only)
api_key = os.environ.get('GOOGLE_API_KEY')
print(f"API Key loaded: {api_key[:10]}...")

# API endpoint
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

# Request payload - exactly as shown in the official documentation
payload = {
    "contents": [{
        "parts":[{"text": "Explain how AI works"}]
    }]
}

try:
    # Make the API request
    print("\nTesting API connection...")
    print("URL:", url)
    print("Payload:", json.dumps(payload, indent=2))
    
    response = requests.post(
        url,
        headers={'Content-Type': 'application/json'},
        data=json.dumps(payload)
    )
    
    # Check response
    if response.status_code == 200:
        print("\nAPI Connection Successful!")
        result = response.json()
        print("Response:", result['candidates'][0]['content']['parts'][0]['text'])
    else:
        print("\nAPI Request Failed!")
        print("Status Code:", response.status_code)
        print("Error:", response.text)
        
except Exception as e:
    print("\nAPI Connection Failed!")
    print("Error:", str(e)) 