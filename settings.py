# Replace with your Sonarr URL
SONARR_URL = ""  # ex: http://localhost:8989

# Replace with your Sonarr API key
SONARR_API_KEY = ""

# Set to True if Sonarr is running on version 5
on_version_five = False


# Regex class with the pattern and the array of langauges the pattern applies to
class RegexPattern:
    def __init__(self, pattern, languages=[]):
        self.pattern = pattern
        self.languages = languages


# --- Regex Patterns ---
# Add your regex patterns to this list.
# The script will attempt to start the download for any queued item
# with a title that matches any of these patterns.
#
# EX:  RegexPattern(r"Keyword or Regex")
# EX2: RegexPattern(r"Keyword or Regex", ["English", "Japanese"])
REGEX_PATTERNS = []

# Time to wait between checks in seconds
WAIT_TIME = 20
