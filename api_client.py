# photobooth_ai/api_client.py
import requests
import config
import json

def get_ticket_info(qr_data_string):
    """
    Calls the ticket validation API endpoint with the QR data.
    
    Args:
        qr_data_string (str): The string data decoded from the QR code.
        
    Returns:
        dict: A dictionary with ticket holder information (e.g., 
              {"ticket_holder_name": "Nume Detinator", "purchaser_name": "Nume Cumparator"})
              if successful, None otherwise.
    """
    if not config.TICKET_API_ENDPOINT or config.TICKET_API_ENDPOINT == "YOUR_TICKET_API_ENDPOINT_HERE":
        print("Error: TICKET_API_ENDPOINT is not configured in config.py.")
        # For testing without a real API, return mock data
        print("Returning mock ticket data for testing.")
        if "valid_qr" in qr_data_string.lower(): # Simulate a valid QR
            return {"ticket_holder_name": "Test User", "purchaser_name": "Test Buyer"}
        else: # Simulate an invalid QR
            return None

    payload = {"qr_data": qr_data_string}
    headers = {"Content-Type": "application/json"} # Adjust if your API expects different headers

    try:
        # S-ar putea să vrei să folosești POST dacă trimiți datele în corpul cererii
        # sau GET dacă le trimiți ca parametri URL. Aici presupunem POST cu JSON.
        response = requests.post(config.TICKET_API_ENDPOINT, json=payload, headers=headers, timeout=10)
        response.raise_for_status()  # Ridică o excepție pentru coduri de eroare HTTP (4xx sau 5xx)
        
        ticket_data = response.json()
        
        # Verifică dacă răspunsul conține cheile așteptate
        if "ticket_holder_name" in ticket_data and "purchaser_name" in ticket_data:
            print(f"Ticket info received: {ticket_data}")
            return ticket_data
        else:
            print(f"Error: API response does not contain expected keys. Response: {ticket_data}")
            return None
            
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err} - Response: {response.text if 'response' in locals() else 'No response text'}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"An error occurred during API request: {req_err}")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON response from API. Response: {response.text if 'response' in locals() else 'No response text'}")
    
    return None

if __name__ == '__main__':
    # Test API client
    # Asigură-te că TICKET_API_ENDPOINT este setat în config.py pentru un test real
    # Sau rulează cu endpoint-ul mock (default dacă nu e setat)
    
    # Mock config for testing if not run from main project
    class MockConfig:
        TICKET_API_ENDPOINT = "YOUR_TICKET_API_ENDPOINT_HERE" # Va folosi mock-ul intern
        # TICKET_API_ENDPOINT = "https://jsonplaceholder.typicode.com/posts" # Un endpoint public de test (va eșua validarea cheilor)


    try:
        import config as app_config
    except ImportError:
        app_config = MockConfig()
        print("Using MockConfig for api_client test.")
        # Suprascrie config-ul global pentru a testa comportamentul mock al funcției
        import sys
        sys.modules['config'] = app_config


    print("\n--- Testing with simulated valid QR data (mock response) ---")
    valid_qr = "valid_qr_test_data_123"
    info = get_ticket_info(valid_qr)
    if info:
        print(f"Success! Ticket Info: {info}")
    else:
        print("Failed to get ticket info for valid_qr.")

    print("\n--- Testing with simulated invalid QR data (mock response) ---")
    invalid_qr = "invalid_qr_test_data_456"
    info_invalid = get_ticket_info(invalid_qr)
    if info_invalid:
        print(f"Success (unexpected for invalid)! Ticket Info: {info_invalid}") # Ar trebui să fie None
    else:
        print("Failed to get ticket info for invalid_qr (as expected for mock).")

    # Dacă vrei să testezi un endpoint real, decomentează și setează TICKET_API_ENDPOINT în config.py
    # print("\n--- Testing with a real (or placeholder) endpoint ---")
    # if app_config.TICKET_API_ENDPOINT and app_config.TICKET_API_ENDPOINT != "YOUR_TICKET_API_ENDPOINT_HERE":
    #     real_qr_data = "some_actual_qr_payload" # Modifică cu date reale dacă e necesar
    #     real_info = get_ticket_info(real_qr_data)
    #     if real_info:
    #         print(f"Real API Success! Ticket Info: {real_info}")
    #     else:
    #         print("Real API Failed to get ticket info (check endpoint, payload, and response structure).")
    # else:
    #     print("Skipping real endpoint test as TICKET_API_ENDPOINT is not configured for it.")
    
    print("\nAPI Client test finished.")
