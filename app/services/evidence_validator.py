from __future__ import annotations

from app.schemas import (
    EvidenceStatus,
    EstimateKind,
    GuideDraft,
    Source,
    TestingRecord,
)
from app.services.source_utils import normalize_url


def _known_ids(sources: list[Source]) -> set[str]:
    return {source.id for source in sources}


def _drop_unknown_ids(ids: list[str], valid_ids: set[str]) -> tuple[list[str], bool]:
    kept = [item for item in ids if item in valid_ids]
    return kept, len(kept) != len(ids)


def validate_and_repair_draft(draft: GuideDraft, collected_sources: list[Source]) -> GuideDraft:
    """Attach retrieved sources, drop invented citations, and keep testing honest."""
    valid_ids = _known_ids(collected_sources)
    collected_urls = {normalize_url(source.url) for source in collected_sources}
    uncertain_notes: list[str] = list(draft.unknowns)

    steps = []
    for step in draft.steps:
        kept_ids, removed = _drop_unknown_ids(step.source_ids, valid_ids)
        evidence = step.evidence_status
        if removed or (not kept_ids and evidence == EvidenceStatus.sourced):
            evidence = EvidenceStatus.unknown
            uncertain_notes.append(
                f"Step {step.order} ('{step.title}') had citations that could not be matched to retrieved sources."
            )
        steps.append(step.model_copy(update={"source_ids": kept_ids, "evidence_status": evidence}))

    prerequisites = []
    for item in draft.prerequisites:
        kept_ids, removed = _drop_unknown_ids(item.source_ids, valid_ids)
        evidence = item.evidence_status
        if removed or (not kept_ids and evidence == EvidenceStatus.sourced):
            evidence = EvidenceStatus.unknown
        prerequisites.append(item.model_copy(update={"source_ids": kept_ids, "evidence_status": evidence}))

    blockers = []
    for item in draft.blockers:
        kept_ids, _removed = _drop_unknown_ids(item.source_ids, valid_ids)
        evidence = item.evidence_status
        if not kept_ids and evidence == EvidenceStatus.sourced:
            evidence = EvidenceStatus.unknown
        blockers.append(item.model_copy(update={"source_ids": kept_ids, "evidence_status": evidence}))

    testing = draft.testing_record or TestingRecord()
    if testing.tested and not testing.attempts:
        testing = testing.model_copy(
            update={
                "tested": False,
                "notes": "Testing was claimed without a recorded attempt, so the claim was removed.",
            }
        )
        uncertain_notes.append("The guide was not end-to-end tested against the provider.")

    time_estimate = draft.time_estimate
    if time_estimate.kind == EstimateKind.documented and not any(
        source.source_type.value == "official" for source in collected_sources
    ):
        time_estimate = time_estimate.model_copy(update={"kind": EstimateKind.estimate})

    unique_unknowns: list[str] = []
    for note in uncertain_notes:
        if note and note not in unique_unknowns:
            unique_unknowns.append(note)

    # Model-supplied source URLs are discarded unless they match retrieved results.
    trusted_sources = [
        source
        for source in draft.sources
        if source.id in valid_ids and normalize_url(source.url) in collected_urls
    ]
    if not trusted_sources:
        trusted_sources = collected_sources

    return draft.model_copy(
        update={
            "steps": steps,
            "prerequisites": prerequisites,
            "blockers": blockers,
            "testing_record": testing,
            "time_estimate": time_estimate,
            "unknowns": unique_unknowns[:20],
            "sources": trusted_sources,
        }
    )
