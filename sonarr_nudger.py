import requests
import time
import re
from pyarr import SonarrAPI

from settings import *


def force_grab_queued_item(item_id: int):
    """
    Makes a direct API POST call to Sonarr's /api/v3/queue/grab/{id} endpoint
    to force a grab for a queued item.
    """
    headers = {
        "X-Api-Key": SONARR_API_KEY,
        # Content-Type is not strictly needed if there's no JSON payload,
        # but it's good practice for POST requests.
        # However, since the ID is in the URL, we might not send an explicit JSON body.
        # Let's keep it just in case Sonarr prefers it.
        "Content-Type": "application/json",
    }

    # Construct the API endpoint with the item ID directly in the path
    api_endpoint = f"{SONARR_URL}/api/v3/queue/grab/{item_id}"

    print(f"\tAttempting direct API POST call to: {api_endpoint}")
    try:
        # For a POST request with the ID in the URL, the 'json' parameter might not be strictly needed,
        # but some APIs are forgiving. The critical part is the URL and method.
        response = requests.post(api_endpoint, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        print(f"\tSuccessfully sent grab command for item ID {item_id}.")
        return True  # Or just True if you don't need the response body
    except requests.exceptions.RequestException as e:
        print(f"\tError making direct API call to Sonarr for item ID {item_id}: {e}")
        if response is not None:
            print(f"\t\tResponse status code: {response.status_code}")
            print(f"\t\tResponse text: {response.text}")
        return False


def main():
    """
    Main function to connect to Sonarr, check the queue,
    and start downloads for items matching regex patterns.
    """

    # Check if the necessary settings are provided
    if not SONARR_URL:
        print("Error: SONARR_URL is not set in settings.py.")
        return
    if not SONARR_API_KEY:
        print("Error: SONARR_API_KEY is not set in settings.py.")
        return
    if not REGEX_PATTERNS:
        print("Error: REGEX_PATTERNS is empty in settings.py.")
        return

    print("--- Sonarr Queue Checker Initialized ---")
    print(f"\tConnecting to Sonarr at: {SONARR_URL}")

    try:
        sonarr = SonarrAPI(SONARR_URL, SONARR_API_KEY)
        # Test the connection by retrieving system status
        sonarr.get_system_status()
        print("\tSuccessfully connected to Sonarr.")
    except Exception as e:
        print(f"\tError connecting to Sonarr: {e}")
        print("\tPlease check your Sonarr URL and API key.")
        return

    print("\tMonitoring the queue for matches...")

    while True:
        try:
            queue = sonarr.get_queue()

            if queue.get("records", []):
                for item in queue.get("records", []):
                    # Check if the item has not started downloading
                    # The 'status' can vary, common statuses for queued but not downloading
                    # items include 'Queued', 'Pending'. You may need to adjust this
                    # based on your download client and Sonarr setup.
                    if item.get("status") in ["delay"]:
                        title = item.get("title")
                        if title:
                            for pattern in REGEX_PATTERNS:
                                if re.search(pattern, title, re.IGNORECASE):
                                    print(
                                        f"\tMatch found for '{title}' with pattern '{pattern}'."
                                    )
                                    # Use the direct API call
                                    grab_result = force_grab_queued_item(item["id"])
                                    if grab_result:
                                        print(f"\tDownload started for '{title}'.\n")
                                    else:
                                        print(
                                            f"\tFailed to start download for '{title}' via direct API call.\n"
                                        )
                                    break  # Move to the next item once a match is found and acted upon

        except Exception as e:
            print(f"\tAn error occurred while checking the queue: {e}")

        time.sleep(WAIT_TIME)  # Wait for 1 minute


if __name__ == "__main__":
    main()
