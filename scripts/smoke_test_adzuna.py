
# scripts/smoke_test_adzuna.py

"""Safely verify live Adzuna connectivity and search results."""

from providers.adzuna import AdzunaClient


def main() -> int:
    client = AdzunaClient()

    if not client.configured:
        print("NOT CONFIGURED: Add Adzuna credentials to your .env file.")
        return 1

    print("Testing Adzuna search...")
    jobs, errors = client.search_many(
        queries=["Python Developer"],
        location="",
        pages=1,
        results_per_page=5,
    )

    if jobs:
        print(f"\nSUCCESS: Retrieved {len(jobs)} job(s).")
        for number, job in enumerate(jobs, start=1):
            print(f"\n{number}. {job.title}")
            print(f"   Company: {job.company}")
            print(f"   Location: {job.location}")
            print(f"   Salary period: {job.salary_period}")
    else:
        print("\nNo jobs were retrieved.")

    for error in errors:
        print(f"WARNING: {error}")

    if jobs:
        print("\nLIVE SEARCH TEST PASSED")
        return 0

    print("\nLIVE SEARCH NOT VERIFIED")
    print("Check the warnings, credentials and API access.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
