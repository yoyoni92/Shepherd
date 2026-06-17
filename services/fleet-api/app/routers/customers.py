from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app import repo
from app.auth import Action, assert_permitted
from app.deps import Caller, Db
from app.schemas import CustomerCreate, CustomerRead

router = APIRouter(prefix="/customers", tags=["customers"])


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
    return [_to_read(c) for c in repo.list_customers(session)]


@router.post(
    "",
    response_model=CustomerRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create customer (admin only)",
)
def create_customer(body: CustomerCreate, session: Db, caller: Caller) -> CustomerRead:
    assert_permitted(caller.role, Action.MANAGE_CUSTOMERS)
    return _to_read(repo.create_customer(session, body.model_dump()))


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete customer (admin only)",
)
def delete_customer(customer_id: UUID, session: Db, caller: Caller) -> None:
    assert_permitted(caller.role, Action.MANAGE_CUSTOMERS)
    if not repo.delete_customer(session, customer_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
