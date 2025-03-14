import os
from dotenv import load_dotenv
import google.generativeai as genai
import json

# Load environment variables
load_dotenv()

# Configure Google Gemini AI
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
print(f"API Key loaded: {GOOGLE_API_KEY[:10]}...")
genai.configure(api_key=GOOGLE_API_KEY)

# Initialize model
text_model = genai.GenerativeModel('gemini-2.0-flash')

def generate_content_calendar(client_name, industry, target_audience, goals):
    try:
        prompt = f"""Generate a 3-month content calendar for {client_name}, a {industry} business targeting {target_audience}.
        Goals: {goals}
        
        Format the response as a JSON array with the following structure:
        [
            {{
                "date": "YYYY-MM-DD",
                "platform": "platform_name",
                "content_type": "type_of_content",
                "topic": "main_topic",
                "description": "detailed_description"
            }}
        ]
        
        Include 2-3 posts per week across different platforms (Instagram, Facebook, LinkedIn, Twitter).
        Ensure content aligns with the business goals and target audience.
        """
        
        print(f"\nGenerating calendar for: {client_name}")
        print(f"Industry: {industry}")
        print(f"Target Audience: {target_audience}")
        print(f"Goals: {goals}")
        
        response = text_model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean up the response - remove the "```json" and "```" if present
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        print("\nRaw API Response (after cleanup):")
        print(response_text)
        
        # Try to parse the response as JSON
        try:
            calendar_data = json.loads(response_text)
            print("\nSuccessfully parsed calendar data!")
            print(f"Number of entries: {len(calendar_data)}")
            print("\nFirst 3 entries:")
            for entry in calendar_data[:3]:
                print(f"\nDate: {entry['date']}")
                print(f"Platform: {entry['platform']}")
                print(f"Content Type: {entry['content_type']}")
                print(f"Topic: {entry['topic']}")
            return calendar_data
        except json.JSONDecodeError as e:
            print(f"\nError parsing JSON response: {str(e)}")
            print("Response text is not valid JSON. Please check the API response format.")
            return None
            
    except Exception as e:
        print(f"\nError generating content calendar: {str(e)}")
        return None

if __name__ == "__main__":
    # Test case
    client_name = "Test Restaurant"
    industry = "Food & Beverage"
    target_audience = "Young professionals and families"
    goals = "Increase brand awareness and drive weekend foot traffic"
    
    generate_content_calendar(client_name, industry, target_audience, goals) 