"""Write the API's OpenAPI spec to a file (default: openapi.json in the repo root).

The frontend generates its typed API client from this file with NSwag, so re-run this and commit
the result whenever a route, request model or response model changes:

    python scripts/export_openapi.py [output_path]

Then in TuneUp-App-Frontend run `npm run api:update`.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Importing the app connects to the database; use a throwaway in-memory one so this works anywhere.
# (load_dotenv() won't override a variable that's already set.)
os.environ["database_url"] = "sqlite://"
sys.path.insert(0, ROOT)

from main import app  # noqa: E402

output = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "openapi.json")
with open(output, "w") as f:
    json.dump(app.openapi(), f, indent=2)
    f.write("\n")
print(f"Wrote {output}")
