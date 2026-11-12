"""Extension Request Sorter - CIT AI-Native Engineering, Semester 1, Assessment 5.

The LLM extracts facts only. Python validates the facts and applies the policy.
The program never approves or rejects an extension; faculty make the final decision.
"""
import csv
import json
import os
import re
from collections import Counter
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

BASE_DIR = Path(__file__).resolve().parent
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
MAX_DAYS_WITHIN_POLICY = 3
MIN_DAYS = 1
MAX_DAYS = 30
WITHIN_POLICY_REASONS = {"medical", "family", "technical"}
ALLOWED_REASONS = {"medical", "family", "technical", "event", "workload", "other"}
REQUIRED_FIELDS = {"course", "days", "reason", "summary"}

NUMBER_WORDS = {
    1:"one", 2:"two", 3:"three", 4:"four", 5:"five", 6:"six", 7:"seven",
    8:"eight", 9:"nine", 10:"ten", 11:"eleven", 12:"twelve", 13:"thirteen",
    14:"fourteen", 15:"fifteen", 16:"sixteen", 17:"seventeen", 18:"eighteen",
    19:"nineteen", 20:"twenty", 21:"twenty-one", 22:"twenty-two",
    23:"twenty-three", 24:"twenty-four", 25:"twenty-five",
    26:"twenty-six", 27:"twenty-seven", 28:"twenty-eight",
    29:"twenty-nine", 30:"thirty"
}

def load_requests(filename="requests.csv"):
    path = BASE_DIR / filename
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        if not {"id", "date", "request"}.issubset(row):
            raise ValueError("requests.csv must contain id, date, request columns.")
    return rows

def load_courses(filename="courses.csv"):
    path = BASE_DIR / filename
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return {r["code"].strip(): r["name"].strip() for r in rows}

def number_was_written(request_text, days):
    if isinstance(days, bool) or not isinstance(days, int):
        return False
    digit = re.search(rf"(?<!\w){days}(?!\w)", request_text) is not None
    word = NUMBER_WORDS.get(days, "")
    word_found = bool(word) and re.search(rf"\b{re.escape(word)}\b", request_text, re.I) is not None
    return digit or word_found

def is_valid(data):
    if not isinstance(data, dict) or set(data) != REQUIRED_FIELDS:
        return False
    if data["course"] is not None and not isinstance(data["course"], str):
        return False
    days = data["days"]
    if days is not None and (isinstance(days, bool) or not isinstance(days, int)
                             or not MIN_DAYS <= days <= MAX_DAYS):
        return False
    if data["reason"] not in ALLOWED_REASONS:
        return False
    if not isinstance(data["summary"], str) or len(data["summary"].split()) > 15:
        return False
    return True

def validate_extracted_facts(data, request_text, courses):
    """Python fact-checks course and days against the student's original text."""
    clean = dict(data)
    course = clean["course"]
    if course not in courses or not re.search(rf"\b{re.escape(course or '')}\b", request_text):
        clean["course"] = None
    days = clean["days"]
    if days is not None and not number_was_written(request_text, days):
        clean["days"] = None
    return clean

def make_safe_summary(course, days, reason):
    """Create a short summary from validated fields, not private free text."""
    if course is None and days is None:
        return "Extension request; course and number of days missing"
    if course is None:
        return f"Requests {days} days; course code missing"
    if days is None:
        return f"Extension request for {course}; number of days missing"
    return f"Requests {days} days for {course}; {reason} reason"

def load_system_prompt(filename="system_prompt.txt"):
    return (BASE_DIR / filename).read_text(encoding="utf-8")

def call_llm(request_text):
    """Use the OpenAI API for extraction only; never apply policy in the LLM."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing. Add it to .env.")
    if OpenAI is None:
        raise RuntimeError("Install dependencies with: pip install -r requirements.txt")
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": load_system_prompt()},
            {"role": "user", "content": request_text}
        ],
        response_format={"type": "json_object"},
        temperature=0
    )
    return json.loads(response.choices[0].message.content)

def extract_information(request_text, courses, extractor=None):
    """Retry once after an error, then safely send the request for more information."""
    extractor = extractor or call_llm
    for attempt in range(2):
        try:
            data = extractor(request_text)
            if not is_valid(data):
                raise ValueError("LLM returned an invalid JSON structure or field.")
            data = validate_extracted_facts(data, request_text, courses)
            data["summary"] = make_safe_summary(data["course"], data["days"], data["reason"])
            return data
        except Exception as exc:
            print(f"Extraction attempt {attempt + 1} failed: {exc}")
    return {
        "course": None, "days": None, "reason": "other",
        "summary": "Could not safely extract request; faculty review required"
    }

def recommend(course, days, reason):
    """Apply the fixed department policy in Python only."""
    if course is None or days is None:
        return "needs_more_info"
    if days <= MAX_DAYS_WITHIN_POLICY and reason in WITHIN_POLICY_REASONS:
        return "within_policy"
    return "needs_faculty_review"

def find_duplicate_ids(requests):
    """Return IDs of repeated request texts (case/spacing insensitive)."""
    seen = {}
    duplicates = set()
    for row in requests:
        normalized = " ".join(row["request"].casefold().split())
        if normalized in seen:
            duplicates.add(row["id"])
            duplicates.add(seen[normalized])
        else:
            seen[normalized] = row["id"]
    return duplicates

def write_reports(results):
    with (BASE_DIR / "results.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["id", "course", "days", "reason", "recommendation", "summary", "duplicate_flag"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k) for k in fields})

    with (BASE_DIR / "review_queue.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["id", "date", "request", "recommendation", "duplicate_flag"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in results:
            if r["recommendation"] != "within_policy" or r["duplicate_flag"] == "yes":
                writer.writerow({k: r.get(k) for k in fields})

    recommendations = Counter(r["recommendation"] for r in results)
    reasons = Counter(r["reason"] for r in results)
    courses = Counter(r["course"] or "missing" for r in results)
    with (BASE_DIR / "summary.txt").open("w", encoding="utf-8") as f:
        f.write("EXTENSION REQUEST SORTER - SUMMARY\n")
        f.write(f"Total requests: {len(results)}\n\n")
        for heading, counts in [("Recommendations", recommendations), ("Reasons", reasons), ("Courses", courses)]:
            f.write(heading + ":\n")
            for key, value in sorted(counts.items()):
                f.write(f"  {key}: {value}\n")
            f.write("\n")
        f.write("Reminder: recommendations are administrative categories only. Faculty make every final decision.\n")

def main():
    requests = load_requests()
    courses = load_courses()
    duplicate_ids = find_duplicate_ids(requests)
    results = []
    for row in requests:
        print(f"Processing {row['id']}...")
        extracted = extract_information(row["request"], courses)
        recommendation = recommend(extracted["course"], extracted["days"], extracted["reason"])
        duplicate = row["id"] in duplicate_ids
        if duplicate:
            recommendation = "needs_faculty_review"
        results.append({
            "id": row["id"], "date": row["date"], "request": row["request"],
            **extracted, "recommendation": recommendation,
            "duplicate_flag": "yes" if duplicate else "no"
        })
        print(f"  -> {recommendation}")
    write_reports(results)
    print("\nFinished. Created results.csv, review_queue.csv and summary.txt.")
    print("The tool does not approve or reject extensions. Faculty decide.")

if __name__ == "__main__":
    main()
