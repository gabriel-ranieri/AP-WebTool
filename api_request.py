import requests
import json # Optional: for pretty-printing the output

# 1. Define the components of your request

# The base URL (before the '?')
base_url = 'https://comunicaapi.pje.jus.br/api/v1/comunicacao'

# The query parameters (the key-value pairs after the '?')
# requests will automatically format this into a URL string for you
params = {
    'numeroOab': '143956',
    'dataDisponibilizacaoInicio': '2025-09-25',
    'dataDisponibilizacaoFim': '2025-09-25'
}

# The headers (from the -H flag)
headers = {
    'accept': 'application/json'
}

# 2. Make the request and handle the response
try:
    print(f"Sending GET request to: {base_url}")
    
    # The actual request is made here
    response = requests.get(base_url, params=params, headers=headers)
    
    # Check if the request was successful (HTTP status code 200)
    if response.status_code == 200:
        print("Request successful!")
        
        # Parse the JSON response into a Python dictionary
        data = response.json()
        
        # Pretty-print the JSON data
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
    else:
        # If something went wrong, print the status code and any error message
        print(f"Error: Received status code {response.status_code}")
        print(f"Response text: {response.text}")

except requests.exceptions.RequestException as e:
    # Handle potential network errors (e.g., no internet connection)
    print(f"An error occurred: {e}")