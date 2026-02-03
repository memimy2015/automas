import requests
import json
import sys

URL = "https://open.feedcoopapi.com/search_api/web_search"

def search(query):
    try:
        # Define headers
        api_key = os.environ.get("SEARCH_API_KEY")
        headers = {"Authorization": f"Bearer {api_key}"}        
        if not api_key:
            return {"error": "FEEDCOOP_API_KEY environment variable not set"}
        
        # Send POST request
        body = {
            "Query": query,
            "SearchType": "web",
            "Count": 15,
            "Filter": {
                "NeedContent": False,
                "NeedUrl": False
            },
            "NeedSummary": False,
            "TimeRange":"OneYear"
        }
        
        # 请求包含body
        response = requests.post(URL, headers=headers, json=body, timeout=10)
        
        # Raise an exception for bad status codes
        response.raise_for_status()
        
        # Try to parse JSON response
        try:
            res_json = response.json()
            res_str = ""
            for item in res_json['Result']['WebResults']:
                item['Title'] = item['Title'].replace('\n', '').replace('\r', '')
                item['Content'] = item['Content'].replace('\n', '').replace('\r', '')
                res_str += f"标题：{item['Title']}\n内容：{item['Content']}\n\n"
            return res_str
        except json.JSONDecodeError:
            return {"text": response.text}
            
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Please provide a query as an argument.")
    else:
        query = sys.argv[1]
    result = search(query)
    print(result)
