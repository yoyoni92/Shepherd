from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app import repo
from app.auth import Action, assert_company, assert_permitted
from app.deps import Caller, Db
from app.schemas import CustomerCreate, CustomerRead, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["customers"])


def _company(caller) -> UUID | None:
    return UUID(caller.company_id) if caller.company_id else None


def _to_read(c) -> CustomerRead:
    return CustomerRead(
        customer_id=c.customer_id,
        full_name=c.full_name,
        phone_number=c.phone_number,
        email=c.email,
        status=c.status.value,
    )


@router.get(
    "",
    response_model=list[CustomerRead],
    summary="List customers (admin only)",
)
def list_customers(session: Db, caller: Caller) -> list[CustomerRead]:
    assert_permitted(caller.role, Action.MANAGE_CUSTOMERS)
    return [_to_read(c) for c in repo.list_customers(session, company_id=_company(caller))]


@router.post(
    "",
    response_model=CustomerRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create customer (admin only)",
)
def create_customer(body: CustomerCreate, session: Db, caller: Caller) -> CustomerRead:
    assert_permitted(caller.role, Action.MANAGE_CUSTOMERS)
    data = body.model_dump()
    data["company_id"] = caller.company_id
    return _to_read(repo.create_customer(session, data))


@router.patch(
    "/{customer_id}",
    response_model=CustomerRead,
    summary="Update customer (admin only)",
    description="Partial update — only provided fields are written.",
)
def update_customer(customer_id: UUID, body: CustomerUpdate, session: Db, caller: Caller) -> CustomerRead:
    assert_permitted(caller.role, Action.MANAGE_CUSTOMERS)
    existing = repo.get_customer(session, customer_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    assert_company(existing, caller)
    customer = repo.update_customer(session, customer_id, body.model_dump(exclude_unset=True))
    return _to_read(customer)


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete customer (admin only)",
    description="Unlinks the customer from any vehicles, then removes the customer.",
)
def delete_customer(customer_id: UUID, session: Db, caller: Caller) -> None:
    assert_permitted(caller.role, Action.MANAGE_CUSTOMERS)
    existing = repo.get_customer(session, customer_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    assert_company(existing, caller)
    repo.delete_customer(session, customer_id)
