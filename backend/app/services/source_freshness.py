
from datetime import datetime, timezone


# Initial freshness rules.
# These are configurable project policies, not universal standards.

DOMAIN_POLICIES = {
    "scientific": {
        "max_age_days": 730,
        "verification_interval_days": 365,
    },
    "scientific_research": {
        "max_age_days": 730,
        "verification_interval_days": 365,
    },
    "agriculture": {
        "max_age_days": 180,
        "verification_interval_days": 90,
    },
    "government_policy": {
        "max_age_days": 90,
        "verification_interval_days": 30,
    },
    "education": {
        "max_age_days": 365,
        "verification_interval_days": 180,
    },
    "law": {
        "max_age_days": None,
        "verification_interval_days": 90,
    },
}


def normalize_domain(domain):
    if not domain:
        return None

    domain = domain.strip().lower()

    if domain == "scientific_research":
        return "scientific"

    return domain


def make_aware(value):
    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def assess_source_freshness(source, domain, now=None):
    """
    Assess whether a saved source needs freshness revalidation.

    This evaluates dates and previous verification metadata.
    It does not independently verify the truth or accuracy of a source.
    """

    now = make_aware(now or datetime.now(timezone.utc))
    domain = normalize_domain(domain)

    policy = DOMAIN_POLICIES.get(domain)

    if policy is None:
        return {
            "status": "UNVERIFIED",
            "reason": "No freshness policy exists for this domain.",
            "age_days": None,
        }

    published_at = make_aware(
        getattr(source, "published_at", None)
    )

    last_verified_at = make_aware(
        getattr(source, "last_verified_at", None)
    )

    if last_verified_at and last_verified_at <= now:
        verification_age = (now - last_verified_at).days

        if verification_age <= policy["verification_interval_days"]:
            return {
                "status": "FRESH",
                "reason": (
                    "Source was verified within the domain's "
                    "verification interval."
                ),
                "age_days": (
                    max(0, (now - published_at).days)
                    if published_at else None
                ),
            }

    if published_at is None:
        return {
            "status": "UNVERIFIED",
            "reason": (
                "Publication date is unavailable and recent "
                "verification was not found."
            ),
            "age_days": None,
        }

    age_days = max(0, (now - published_at).days)

    if domain == "law":
        return {
            "status": "REVALIDATE",
            "reason": (
                "Legal validity, amendments, jurisdiction and "
                "precedent must be checked before reuse."
            ),
            "age_days": age_days,
        }

    max_age_days = policy["max_age_days"]

    if max_age_days is not None and age_days > max_age_days:
        return {
            "status": "STALE",
            "reason": (
                f"Source is older than the initial "
                f"{max_age_days}-day domain threshold."
            ),
            "age_days": age_days,
        }

    return {
        "status": "REVALIDATE",
        "reason": (
            "Source is within the age threshold, but no recent "
            "verification is recorded."
        ),
        "age_days": age_days,
    }


def update_source_freshness(source, domain, now=None):
    """
    Calculate and store freshness classification.

    Does not change last_verified_at.
    Only a real verification process should update that field.
    """

    result = assess_source_freshness(
        source=source,
        domain=domain,
        now=now,
    )

    source.freshness_status = result["status"].lower()

    return result


def assess_sources(sources, domain, now=None):
    """Assess a collection of sources."""

    results = []

    for source in sources:
        assessment = update_source_freshness(
            source=source,
            domain=domain,
            now=now,
        )

        results.append({
            "source_id": str(source.id),
            "title": getattr(source, "title", None),
            **assessment,
        })

    return results


def decide_research_memory_action(memories, freshness_results):
    """
    Decide whether previous research can be reused.

    REUSE is allowed only when all matched sources are fresh.
    """

    if not memories:
        return {
            "action": "RESEARCH",
            "reason": "No relevant previous research was found.",
        }

    if not freshness_results:
        return {
            "action": "RESEARCH",
            "reason": "Previous research has no saved source assessments.",
        }

    statuses = {
        item.get("status", "UNVERIFIED")
        for item in freshness_results
    }

    if "STALE" in statuses:
        return {
            "action": "RESEARCH",
            "reason": (
                "One or more sources are stale. "
                "New research is required."
            ),
        }

    if "UNVERIFIED" in statuses or "REVALIDATE" in statuses:
        return {
            "action": "REVALIDATE",
            "reason": (
                "Previous evidence needs additional verification."
            ),
        }

    if statuses == {"FRESH"}:
        return {
            "action": "REUSE",
            "reason": (
                "All assessed sources passed the initial "
                "freshness policy."
            ),
        }

    return {
        "action": "RESEARCH",
        "reason": "Source freshness could not be safely established.",
    }
