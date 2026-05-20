from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_workforce_payroll_downloads_do_not_send_org_id_query() -> None:
    text = _read("frontend/src/app/app/workforce/payroll/page.tsx")
    assert "workforcePayrollExport(periodId)}?org_id=" not in text
    assert "workforcePayrollPayslipPdf(entryId)}?org_id=" not in text


def test_workforce_hooks_canonical_routes_do_not_build_org_id_queries() -> None:
    text = _read("frontend/src/features/workforce/hooks.ts")
    # Canonicalized modules should not rely on mutable org_id query params.
    forbidden_fragments = [
        "workforceAnnouncements}?org_id=",
        "workforceAnnouncementById(announcementId!)}?org_id=",
        "workforceAnnouncementTemplates}?org_id=",
        "workforceAnnouncementAutomationKeys}?org_id=",
        "workforceAnnouncementAttachmentUpload}?org_id=",
        "workforceAnnouncementDeliveries(announcementId!)}?org_id=",
        "workforceHrPolicies}?org_id=",
        "workforceHrPolicyAcks(policyId)}?org_id=",
        "workforceHrDocuments}?org_id=",
        "workforceHrDocumentUpload}?org_id=",
        "workforceHrChecklist}?org_id=",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in text, f"Found forbidden org_id fragment: {fragment}"


def test_workforce_hooks_do_not_send_org_id_in_mutation_payloads() -> None:
    text = _read("frontend/src/features/workforce/hooks.ts")
    assert '"org_id"' not in text
