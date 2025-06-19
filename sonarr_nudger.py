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
        "Content-Type": "application/json",
    }

    # Construct the API endpoint with the item ID directly in the path
    api_endpoint = f"{SONARR_URL}/api/v3/queue/grab/{item_id}"

    # Send the POST request
    print(f"\tAttempting direct API POST call to: {api_endpoint}")
    try:
        response = requests.post(api_endpoint, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        print(f"\tSuccessfully sent grab command for item ID {item_id}.")
        return True
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
        print("\tPlease check your Sonarr URL and API key in settings.py.")
        return

    print("\tMonitoring the queue for matches...")
    first_run = False

    while True:
        try:
            if not first_run:
                first_run = True
            else:
                time.sleep(WAIT_TIME)  # Wait for 1 minute

            queue = sonarr.get_queue()

            # Check if the queue is empty
            if not queue.get("records", []):
                continue

            for item in queue.get("records", []):
                # Skip items that are not delayed
                if not item.get("status") in ["delay"]:
                    continue

                title = item.get("title")

                # Skip if no title is available
                if not title:
                    continue

                for regex_pattern in REGEX_PATTERNS:
                    if regex_pattern.languages:
                        # Get the languages from the queued item
                        languages = item.get("languages", [])

                        # Skip if no languages are specified
                        if not languages:
                            continue

                        language_names = [
                            lang.get("name", "").lower() for lang in languages
                        ]

                        regex_languages_lower = [
                            lang.lower() for lang in regex_pattern.languages
                        ]

                        # If there isn't a language present in both, then skip, otherwise continue
                        language_match = any(
                            lang.lower() in language_names
                            for lang in regex_languages_lower
                        )

                        if not language_match:
                            continue

                    if regex_pattern.pattern in title or re.search(
                        regex_pattern.pattern, title, re.IGNORECASE
                    ):
                        print(
                            f"\tMatch found for '{title}' with pattern '{regex_pattern.pattern}'."
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


if __name__ == "__main__":
    main()
