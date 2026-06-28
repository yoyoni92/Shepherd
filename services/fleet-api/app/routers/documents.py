from uuid import UUID

from fastapi import APIRouter

from app import repo
from app.auth import Action, assert_permitted
from app.deps import Caller, Db
from app.schemas import DocumentExtractedRequest, DocumentExtractedResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "/extracted",
    response_model=DocumentExtractedResponse,
    summary="Apply extracted document data (n8n/admin only)",
    description=(
        "Called by n8n after Bedrock extraction. Matches the plate to a fleet vehicle and updates "
        "the relevant fields (insurance, license, or creates a ticket report). "
        "If the plate is not found, emits a review event instead of a silent failure."
    ),
)
def extracted_document(
    body: DocumentExtractedRequest, session: Db, caller: Caller
) -> DocumentExtractedResponse:
    assert_permitted(caller.role, Action.WRITE_REPORTS)
    company_id = UUID(caller.company_id) if caller.company_id else None
    status_str, event_id, report_id = repo.process_extracted_doc(
        session, body.model_dump(), company_id=company_id
    )
    return DocumentExtractedResponse(status=status_str, event_id=event_id, report_id=report_id)
