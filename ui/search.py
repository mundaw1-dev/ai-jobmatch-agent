
# ui/search.py

"""Multi-query Adzuna search UI with persistent caching."""

import streamlit as st

from persistence.repositories import load_jobs, save_jobs
from persistence.search_cache import (
    DEFAULT_TTL_HOURS,
    get_cached_jobs,
    get_search_cache_stats,
    make_search_cache_key,
    save_cached_jobs,
)
from providers.adzuna import AdzunaClient


DEFAULT_QUERIES = """AI Engineer
Healthcare AI Engineer
Healthcare Data Engineer
Senior AI Platform Engineer
Forward Deployed Engineer
Snowflake Cortex AI Engineer"""


def render_search():
    st.subheader("Find jobs")

    client = AdzunaClient()

    if not client.configured:
        st.info(
            "Adzuna API credentials are optional. Add ADZUNA_APP_ID and "
            "ADZUNA_APP_KEY to your .env file to enable live searches."
        )

    with st.form("job_search_form"):
        queries_text = st.text_area(
            "Search queries (one per line)",
            value=DEFAULT_QUERIES,
            height=180,
            help=(
                "Use specific role titles and skill combinations. "
                "Duplicate queries are removed automatically."
            ),
            disabled=not client.configured,
        )

        location = st.text_input(
            "Location",
            placeholder="e.g. Remote, United Kingdom, London",
            disabled=not client.configured,
        )

        col1, col2 = st.columns(2)

        with col1:
            pages = st.selectbox(
                "Pages per query",
                options=[1, 2, 3],
                index=0,
                help="More pages increase coverage and API usage.",
                disabled=not client.configured,
            )

        with col2:
            results_per_page = st.selectbox(
                "Results per page",
                options=[10, 20, 30, 50],
                index=1,
                disabled=not client.configured,
            )

        force_refresh = st.checkbox(
            "Force refresh — bypass the 24-hour cache",
            value=False,
            help=(
                "Fetch results from Adzuna even if matching cached "
                "results exist."
            ),
            disabled=not client.configured,
        )

        submitted = st.form_submit_button(
            "Search Adzuna",
            disabled=not client.configured,
        )

    if submitted:
        queries = [
            line.strip()
            for line in queries_text.splitlines()
            if line.strip()
        ]

        unique_query_count = len(
            {" ".join(query.split()).casefold() for query in queries}
        )

        if not queries:
            st.error("Enter at least one search query.")

        elif unique_query_count > client.MAX_QUERIES:
            st.error(
                f"Enter no more than {client.MAX_QUERIES} unique queries."
            )

        else:
            try:
                cache_key = make_search_cache_key(
                    queries=queries,
                    location=location,
                    pages=pages,
                    results_per_page=results_per_page,
                )

                cached_jobs = None

                if not force_refresh:
                    cached_jobs = get_cached_jobs(cache_key)

                if cached_jobs is not None:
                    jobs = cached_jobs
                    errors = []
                    cache_hit = True

                else:
                    cache_hit = False

                    with st.spinner("Searching Adzuna..."):
                        jobs, errors = client.search_many(
                            queries=queries,
                            location=location,
                            pages=pages,
                            results_per_page=results_per_page,
                        )

                    # Cache only fully successful searches. Partial results
                    # accompanied by errors should be retried next time.
                    if not errors:
                        save_cached_jobs(
                            cache_key,
                            jobs,
                            ttl_hours=DEFAULT_TTL_HOURS,
                        )

                if jobs:
                    save_jobs(jobs)

                st.session_state["search_jobs"] = [
                    job.model_dump(mode="json") for job in jobs
                ]

                if cache_hit:
                    st.info(
                        "Loaded cached search results. "
                        f"They are retained for up to "
                        f"{DEFAULT_TTL_HOURS} hours."
                    )
                else:
                    st.caption(
                        "Results fetched from Adzuna. "
                        + (
                            "The successful search has been cached."
                            if not errors
                            else "The results were not cached because "
                                 "some searches reported errors."
                        )
                    )

                if jobs:
                    st.success(
                        f"Retrieved {len(jobs)} unique jobs from "
                        f"{unique_query_count} unique search queries."
                    )
                elif errors:
                    st.warning("No jobs were retrieved successfully.")
                else:
                    st.info("No jobs matched these searches.")

                if errors:
                    with st.expander(
                        f"Search warnings ({len(errors)})",
                        expanded=True,
                    ):
                        for error in errors:
                            st.warning(error)

                st.caption(
                    f"Maximum requested results: "
                    f"{unique_query_count * pages * results_per_page}. "
                    "The actual number may be lower because of duplicates "
                    "or fewer available listings."
                )

            except (ValueError, RuntimeError) as exc:
                st.error(f"Search could not be started: {exc}")

    st.divider()

    st.caption(
        "Retrieved jobs are stored in SQLite. Successful searches are "
        f"cached for {DEFAULT_TTL_HOURS} hours."
    )

    st.write(f"Stored jobs: {len(load_jobs())}")

    try:
        stats = get_search_cache_stats()
        st.caption(
            f"Search cache: {stats['valid_entries']} valid entries "
            f"out of {stats['total_entries']} stored entries."
        )
    except Exception:
        # Cache diagnostics should not prevent the search page from rendering.
        st.caption("Search cache statistics are currently unavailable.")

