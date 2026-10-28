#!/usr/bin/env python3
import requests
import time
import re

from settings import *


BASE = f"{SONARR_URL}/api/v5"
H = {"X-Api-Key": SONARR_API_KEY}


def get_system_status():
    """
    Retrieves Sonarr system status via the v5 API.
    Returns the status dict on success, raises on failure.

    GET /api/v5/system/status
    """
    r = requests.get(f"{BASE}/system/status", headers=H, timeout=30)
    r.raise_for_status()
    return r.json()


def get_queue():
    """
    Retrieves all queued items from Sonarr via the v5 paged /queue endpoint.
    Returns a list of queue record dicts (each with a numeric 'id' field
    required by the grab endpoint).

    GET /api/v5/queue
    """
    r = requests.get(
        f"{BASE}/queue",
        headers=H,
        timeout=30,
        params={"pageSize": 1000, "includeUnknownSeriesItems": "true"},
    )
    r.raise_for_status()
    return r.json().get("records", [])


def force_grab_queued_item(item_id: int):
    """
    Makes a direct API POST call to Sonarr's v5 endpoint
    to force a grab for a queued item.

    POST /api/v5/queue/grab/{id}
    """
    headers = {
        "X-Api-Key": SONARR_API_KEY,
        "Content-Type": "application/json",
    }

    api_endpoint = f"{BASE}/queue/grab/{item_id}"

    print(f"\tAttempting direct API POST call to: {api_endpoint}")
    response = None
    try:
        response = requests.post(api_endpoint, headers=headers)
        response.raise_for_status()
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
    for setting_name, setting_value in {
        "SONARR_URL": SONARR_URL,
        "SONARR_API_KEY": SONARR_API_KEY,
        "REGEX_PATTERNS": REGEX_PATTERNS,
    }.items():
        if not setting_value:
            status = "empty" if setting_name == "REGEX_PATTERNS" else "not set"
            print(f"Error: {setting_name} is {status} in settings.py.")
            return

    print("--- Sonarr Queue Checker Initialized ---")
    print(f"\tConnecting to Sonarr at: {SONARR_URL}")

    try:
        # Test the connection by retrieving system status
        system_status = get_system_status()
        version = system_status.get("version", "unknown")
        print(f"\tSuccessfully connected to Sonarr (version: {version}).")
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
                time.sleep(WAIT_TIME)

            records = get_queue()

            # Check if the queue is empty
            if not records:
                continue

            for item in records:
                # In Sonarr v5 the relevant delay flag lives in
                # trackedDownloadState; fall back to checking status as well
                # for forward-compatibility.
                is_delayed = (
                    item.get("trackedDownloadState") == "delay"
                    or item.get("status") == "delay"
                )
                if not is_delayed:
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
            time.sleep(WAIT_TIME)

            # Try to reconnect to Sonarr
            while True:
                try:
                    get_system_status()
                    print("\tSuccessfully reconnected to Sonarr.")
                    break
                except Exception as reconnect_error:
                    print(f"\tReconnection attempt failed: {reconnect_error}")
                    time.sleep(WAIT_TIME)


if __name__ == "__main__":
    main()
