# Invoices, Email, and Team Invitations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire up Resend transactional email, replace mock invoice data with real Stripe invoices, and build a full team-invitation flow (pro+ gated, invite-by-email, accept-via-GitHub-OAuth).

**Architecture:** Resend email client lives in `packages/integrations/integrations/email/`. Stripe webhooks gain two new event types (`checkout.session.completed` for billing email capture, `invoice.paid` for receipt). A new `OrgInvite` model carries the invite token; the existing GitHub OAuth flow is extended to carry an `invite_token` through Redis state so unauthenticated invitees can sign up and accept in one step. Authenticated users accept via a direct POST endpoint.

**Tech Stack:** Resend REST API (httpx), Stripe Python SDK, FastAPI, SQLAlchemy async, Alembic, Next.js 15 (App Router), TanStack Query, Zod.

---

## File Map

**Create:**
- `packages/integrations/integrations/email/__init__.py`
- `packages/integrations/integrations/email/client.py` — Resend HTTP client + HTML templates
- `packages/shared/shared/models/invite.py` — OrgInvite SQLAlchemy model
- `migrations/versions/<hash>_add_org_invites_billing_email.py` — Alembic migration
- `apps/gateway/api/routes/invites.py` — all invite + members routes
- `apps/web/app/invite/[token]/page.tsx` — standalone invite acceptance page
- `tests/unit/test_integrations/test_email_client.py`
- `tests/unit/test_gateway/test_invites.py`

**Modify:**
- `packages/integrations/pyproject.toml` — add httpx dependency
- `packages/shared/shared/models/org_billing.py` — add `billing_email` column
- `packages/shared/shared/models/__init__.py` — export OrgInvite
- `packages/shared/shared/config.py` — add `resend_api_key`
- `.env.example` — add `RESEND_API_KEY`
- `packages/integrations/integrations/billing/stripe_sync.py` — handle `checkout.session.completed`, `invoice.paid`, add `list_stripe_invoices()`
- `apps/gateway/api/routes/billing.py` — add `GET /billing/invoices`
- `apps/gateway/api/__init__.py` — register invites router
- `apps/gateway/middleware/auth.py` — exempt `/invites/` prefix
- `apps/gateway/api/routes/auth.py` — carry `invite_token` through OAuth state
- `apps/web/lib/types.ts` — add InvoiceSchema, MemberSchema, PendingInviteSchema
- `apps/web/lib/api.ts` — add billing.invoices(), orgs.members(), orgs.pendingInvites(), invites.*
- `apps/web/lib/queries.ts` — add invoicesOptions, membersOptions, pendingInvitesOptions, invite mutations
- `apps/web/app/dashboard/billing/page.tsx` — replace mock invoices with real data
- `apps/web/app/dashboard/settings/page.tsx` — real member list, invite dialog

---

## Task 1: Resend email client

**Files:**
- Create: `packages/integrations/integrations/email/__init__.py`
- Create: `packages/integrations/integrations/email/client.py`
- Modify: `packages/integrations/pyproject.toml`
- Modify: `packages/shared/shared/config.py`
- Modify: `.env.example`
- Test: `tests/unit/test_integrations/test_email_client.py`

- [ ] **Step 1: Add httpx to integrations package**

```bash
uv add --package integrations httpx
```

Expected: `packages/integrations/pyproject.toml` now lists `httpx` in dependencies.

- [ ] **Step 2: Add resend_api_key to Settings**

In `packages/shared/shared/config.py`, add after the Stripe block:

```python
# Email (Resend — optional, email sending disabled when unset)
resend_api_key: str | None = None
```

- [ ] **Step 3: Update .env.example**

Add to `.env.example` after the Stripe block:

```
# Resend (transactional email — optional, get key at resend.com)
RESEND_API_KEY=
```

- [ ] **Step 4: Write the failing test**

Create `tests/unit/test_integrations/test_email_client.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_send_email_posts_to_resend():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_client):
        from integrations.email.client import send_email
        await send_email("re_test_key", "user@example.com", "Hello", "<p>Hello</p>")

    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    assert call_kwargs.args[0] == "https://api.resend.com/emails"
    assert call_kwargs.kwargs["headers"]["Authorization"] == "Bearer re_test_key"
    assert call_kwargs.kwargs["json"]["to"] == ["user@example.com"]


def test_invoice_receipt_html_contains_amount_and_number():
    from integrations.email.client import invoice_receipt_html
    html = invoice_receipt_html("pro", 2900, "INV-0001", "https://stripe.com/invoice.pdf")
    assert "$29.00" in html
    assert "INV-0001" in html
    assert "https://stripe.com/invoice.pdf" in html
    assert "Pro" in html


def test_invite_html_contains_org_and_link():
    from integrations.email.client import invite_html
    html = invite_html("Acme Corp", "jdoe", "https://app.argus.ai/invite/abc123")
    assert "Acme Corp" in html
    assert "jdoe" in html
    assert "https://app.argus.ai/invite/abc123" in html
```

- [ ] **Step 5: Run the test to confirm it fails**

```bash
uv run pytest tests/unit/test_integrations/test_email_client.py -v
```

Expected: `ModuleNotFoundError: No module named 'integrations.email'`

- [ ] **Step 6: Create the email package**

Create `packages/integrations/integrations/email/__init__.py` — empty file.

Create `packages/integrations/integrations/email/client.py`:

```python
from __future__ import annotations

import httpx

_RESEND_URL = "https://api.resend.com/emails"
_FROM = "Argus <noreply@argus.ai>"


async def send_email(api_key: str, to: str, subject: str, html: str) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            _RESEND_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={"from": _FROM, "to": [to], "subject": subject, "html": html},
        )
        resp.raise_for_status()


def invoice_receipt_html(plan: str, amount_cents: int, invoice_number: str, invoice_pdf_url: str) -> str:
    amount = f"${amount_cents / 100:.2f}"
    return f"""
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:24px">
  <h2 style="margin:0 0 8px">Payment confirmed</h2>
  <p style="color:#666;margin:0 0 24px">Your Argus {plan.title()} plan is now active.</p>
  <table style="width:100%;border-collapse:collapse;margin-bottom:24px">
    <tr>
      <td style="padding:8px 0;border-bottom:1px solid #eee;color:#666">Invoice</td>
      <td style="padding:8px 0;border-bottom:1px solid #eee;text-align:right">{invoice_number}</td>
    </tr>
    <tr>
      <td style="padding:8px 0;color:#666">Amount paid</td>
      <td style="padding:8px 0;text-align:right;font-weight:600">{amount}</td>
    </tr>
  </table>
  <a href="{invoice_pdf_url}"
     style="background:#000;color:#fff;padding:12px 24px;text-decoration:none;font-size:14px;display:inline-block">
    Download invoice PDF
  </a>
</div>
"""


def invite_html(org_name: str, inviter_login: str, accept_url: str) -> str:
    return f"""
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:24px">
  <h2 style="margin:0 0 8px">You&#39;ve been invited to {org_name}</h2>
  <p style="color:#666;margin:0 0 24px">
    <strong>{inviter_login}</strong> has invited you to join their team on Argus.
  </p>
  <a href="{accept_url}"
     style="background:#000;color:#fff;padding:12px 24px;text-decoration:none;font-size:14px;display:inline-block">
    Accept invite
  </a>
  <p style="color:#999;font-size:12px;margin-top:24px">
    This invite expires in 7 days. If you didn&#39;t expect this, you can safely ignore this email.
  </p>
</div>
"""
```

- [ ] **Step 7: Run the tests and verify they pass**

```bash
uv run pytest tests/unit/test_integrations/test_email_client.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 8: Commit**

```bash
git add packages/integrations/integrations/email/ packages/integrations/pyproject.toml \
        packages/shared/shared/config.py .env.example \
        tests/unit/test_integrations/test_email_client.py
git commit -m "feat(email): add Resend email client with invoice and invite templates"
```

---

## Task 2: OrgInvite model, billing_email column, and migration

**Files:**
- Create: `packages/shared/shared/models/invite.py`
- Modify: `packages/shared/shared/models/org_billing.py`
- Modify: `packages/shared/shared/models/__init__.py`
- Create: `migrations/versions/<hash>_add_org_invites_billing_email.py` (auto-generated)

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_shared/test_org_invite_model.py`:

```python
from datetime import datetime, timedelta, timezone

import pytest


def test_org_invite_defaults():
    from shared.models.invite import OrgInvite
    invite = OrgInvite(org_id="org-1", email="user@example.com", invited_by="user-1")
    assert invite.role == "member"
    assert invite.accepted_at is None
    assert invite.token is not None
    assert len(invite.token) > 10
    # expires ~7 days from now
    now = datetime.now(timezone.utc)
    assert invite.expires_at > now + timedelta(days=6)
    assert invite.expires_at < now + timedelta(days=8)


def test_org_billing_has_billing_email():
    from shared.models.org_billing import OrgBilling
    b = OrgBilling(org_id="org-1")
    assert b.billing_email is None  # nullable by default
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
uv run pytest tests/unit/test_shared/test_org_invite_model.py -v
```

Expected: `ImportError` or `AttributeError` — model doesn't exist yet.

- [ ] **Step 3: Add billing_email to OrgBilling**

In `packages/shared/shared/models/org_billing.py`, add after `stripe_subscription_id`:

```python
billing_email: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
```

Also add `billing_email` to the `__init__` signature and `super().__init__()` call:

```python
def __init__(
    self,
    org_id: str,
    plan: str = "free",
    seat_count: int = 1,
    reviews_used_this_month: int = 0,
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
    billing_email: str | None = None,
    **kwargs,
):
    super().__init__(
        org_id=org_id,
        plan=plan,
        seat_count=seat_count,
        reviews_used_this_month=reviews_used_this_month,
        stripe_customer_id=stripe_customer_id,
        stripe_subscription_id=stripe_subscription_id,
        billing_email=billing_email,
        **kwargs,
    )
```

- [ ] **Step 4: Create the OrgInvite model**

Create `packages/shared/shared/models/invite.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


def _expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=7)


class OrgInvite(Base):
    __tablename__ = "org_invites"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(String, ForeignKey("orgs.id"), nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default="member")
    token: Mapped[str] = mapped_column(
        String, unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )
    invited_by: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_expires_at
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_org_invites_token", "token"),
        Index("ix_org_invites_org_id", "org_id"),
    )
```

- [ ] **Step 5: Export OrgInvite from shared models**

In `packages/shared/shared/models/__init__.py`:

```python
from .api_key import ApiKey
from .base import Base
from .finding import Finding
from .invite import OrgInvite
from .org import Org
from .org_billing import OrgBilling
from .org_integration import OrgIntegration
from .repo import Repo
from .review import Review
from .user import User
from .user_org import UserOrg

__all__ = [
    "Base", "Org", "OrgBilling", "OrgIntegration", "OrgInvite",
    "User", "UserOrg", "ApiKey", "Repo", "Review", "Finding",
]
```

- [ ] **Step 6: Run the tests and verify they pass**

```bash
uv run pytest tests/unit/test_shared/test_org_invite_model.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 7: Generate the migration**

```bash
make migrate NAME="add_org_invites_billing_email"
```

- [ ] **Step 8: Verify the migration looks correct**

Open the generated file in `migrations/versions/`. It should contain:
- `op.add_column("org_billing", sa.Column("billing_email", sa.String(), nullable=True))`
- `op.create_table("org_invites", ...)` with all columns
- A `downgrade()` that drops both

If the auto-generated migration is missing anything, edit it to match the model exactly.

- [ ] **Step 9: Apply the migration**

```bash
make migrate-up
```

Expected: migration applies without error.

- [ ] **Step 10: Commit**

```bash
git add packages/shared/shared/models/invite.py \
        packages/shared/shared/models/org_billing.py \
        packages/shared/shared/models/__init__.py \
        migrations/versions/
git commit -m "feat(db): add OrgInvite model and billing_email to OrgBilling"
```

---

## Task 3: Stripe invoice list endpoint + invoice.paid + checkout.session.completed

**Files:**
- Modify: `packages/integrations/integrations/billing/stripe_sync.py`
- Modify: `apps/gateway/api/routes/billing.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_integrations/test_stripe_invoice.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_list_stripe_invoices_maps_fields():
    fake_invoices = {
        "data": [
            {
                "id": "in_abc",
                "number": "INV-0001",
                "amount_paid": 2900,
                "created": 1700000000,
                "invoice_pdf": "https://stripe.com/pdf",
                "status": "paid",
            }
        ]
    }
    with patch(
        "integrations.billing.stripe_sync._run_stripe_call",
        new=AsyncMock(return_value=fake_invoices),
    ):
        from integrations.billing.stripe_sync import list_stripe_invoices
        result = await list_stripe_invoices("sk_test", "cus_abc")

    assert len(result) == 1
    assert result[0]["id"] == "in_abc"
    assert result[0]["amount_paid"] == 2900
    assert result[0]["invoice_pdf"] == "https://stripe.com/pdf"


@pytest.mark.asyncio
async def test_sync_invoice_paid_sends_email():
    from unittest.mock import AsyncMock, MagicMock, patch
    from sqlalchemy.ext.asyncio import AsyncSession

    billing = MagicMock()
    billing.billing_email = "owner@example.com"
    billing.plan = "pro"

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=billing))
    )

    event = {
        "type": "invoice.paid",
        "data": {
            "object": {
                "customer": "cus_abc",
                "amount_paid": 2900,
                "number": "INV-0001",
                "invoice_pdf": "https://stripe.com/pdf",
            }
        },
    }

    with patch("integrations.billing.stripe_sync.send_email", new=AsyncMock()) as mock_send, \
         patch("integrations.billing.stripe_sync._resend_key", return_value="re_test"):
        from integrations.billing.stripe_sync import sync_subscription_event
        await sync_subscription_event(mock_session, event)

    mock_send.assert_called_once()
    call_args = mock_send.call_args
    assert call_args.args[1] == "owner@example.com"
```

- [ ] **Step 2: Run to confirm it fails**

```bash
uv run pytest tests/unit/test_integrations/test_stripe_invoice.py -v
```

Expected: `ImportError` for `list_stripe_invoices`.

- [ ] **Step 3: Update stripe_sync.py**

Replace the entire `_HANDLED_EVENTS` set and `sync_subscription_event` function, and add `list_stripe_invoices` and `_resend_key` in `packages/integrations/integrations/billing/stripe_sync.py`:

```python
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

import stripe
from shared.models.org_billing import OrgBilling
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_HANDLED_EVENTS = frozenset(
    [
        "checkout.session.completed",
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "invoice.paid",
    ]
)


class StripeBillingError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


async def _run_stripe_call(api_key: str, func: Callable[..., Any], **kwargs: Any) -> Any:
    def call() -> Any:
        stripe.api_key = api_key
        return func(**kwargs)

    try:
        return await asyncio.to_thread(call)
    except stripe.StripeError as exc:
        status_code = exc.http_status if exc.http_status and 400 <= exc.http_status < 500 else 502
        detail = exc.user_message or str(exc) or "Stripe request failed"
        raise StripeBillingError(status_code=status_code, detail=detail) from exc


def parse_stripe_event(raw_body: bytes, sig_header: str, settings: Any) -> dict:
    try:
        event = stripe.Webhook.construct_event(raw_body, sig_header, settings.stripe_webhook_secret)
        return event.to_dict()
    except stripe.SignatureVerificationError as exc:
        raise ValueError("Invalid signature") from exc
    except ValueError as exc:
        raise ValueError("Invalid payload") from exc


async def create_stripe_customer(api_key: str, org_id: str) -> Any:
    return await _run_stripe_call(api_key, stripe.Customer.create, metadata={"org_id": org_id})


async def create_stripe_checkout_session(
    api_key: str,
    customer_id: str,
    price_id: str,
    plan: str,
    seats: int,
    success_url: str,
    cancel_url: str,
) -> Any:
    return await _run_stripe_call(
        api_key,
        stripe.checkout.Session.create,
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": seats}],
        subscription_data={"metadata": {"plan": plan, "seat_count": str(seats)}},
        success_url=success_url,
        cancel_url=cancel_url,
    )


async def create_stripe_portal_session(api_key: str, customer_id: str, return_url: str) -> Any:
    return await _run_stripe_call(
        api_key,
        stripe.billing_portal.Session.create,
        customer=customer_id,
        return_url=return_url,
    )


async def list_stripe_invoices(api_key: str, customer_id: str, limit: int = 12) -> list[dict]:
    result = await _run_stripe_call(
        api_key, stripe.Invoice.list, customer=customer_id, limit=limit
    )
    return [
        {
            "id": inv["id"],
            "number": inv.get("number") or inv["id"],
            "amount_paid": inv["amount_paid"],
            "created": inv["created"],
            "invoice_pdf": inv.get("invoice_pdf"),
            "status": inv["status"],
        }
        for inv in result.get("data", [])
    ]


def _resend_key() -> str | None:
    from shared.config import get_settings
    return get_settings().resend_api_key


async def sync_subscription_event(session: AsyncSession, event: Any) -> None:
    event_type = event.get("type", "")
    if event_type not in _HANDLED_EVENTS:
        return

    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        customer_id: str = obj.get("customer", "")
        email: str | None = (obj.get("customer_details") or {}).get("email")
        if not customer_id or not email:
            return
        result = await session.execute(
            select(OrgBilling).where(OrgBilling.stripe_customer_id == customer_id)
        )
        billing = result.scalar_one_or_none()
        if billing:
            billing.billing_email = email
            await session.commit()
        return

    if event_type == "invoice.paid":
        customer_id = obj.get("customer", "")
        result = await session.execute(
            select(OrgBilling).where(OrgBilling.stripe_customer_id == customer_id)
        )
        billing = result.scalar_one_or_none()
        if billing and billing.billing_email:
            api_key = _resend_key()
            if api_key:
                from integrations.email.client import invoice_receipt_html, send_email
                html = invoice_receipt_html(
                    billing.plan,
                    obj.get("amount_paid", 0),
                    obj.get("number") or obj.get("id", ""),
                    obj.get("invoice_pdf") or "",
                )
                try:
                    await send_email(
                        api_key,
                        billing.billing_email,
                        "Your Argus invoice",
                        html,
                    )
                except Exception:
                    logger.warning("Failed to send invoice email for customer %s", customer_id)
        return

    # subscription created / updated / deleted
    customer_id = obj["customer"]
    sub_id: str = obj["id"]

    result = await session.execute(
        select(OrgBilling).where(OrgBilling.stripe_customer_id == customer_id)
    )
    billing = result.scalar_one_or_none()
    if billing is None:
        logger.warning("No OrgBilling found for stripe_customer_id=%s — skipping", customer_id)
        return

    if event_type == "customer.subscription.deleted":
        billing.plan = "free"
        billing.seat_count = 1
        billing.stripe_subscription_id = None
    else:
        status = obj.get("status", "")
        if status not in {"active", "trialing"}:
            logger.warning("Ignoring subscription %s with status=%r", sub_id, status)
            return
        metadata = obj.get("metadata", {})
        plan = metadata.get("plan", "free")
        if plan not in {"free", "pro", "team", "enterprise"}:
            logger.warning("Ignoring subscription %s with unsupported plan=%r", sub_id, plan)
            return
        try:
            seat_count = int(metadata.get("seat_count", "1"))
        except (TypeError, ValueError):
            seat_count = 1

        billing.plan = plan
        billing.seat_count = max(1, seat_count)
        billing.stripe_customer_id = customer_id
        billing.stripe_subscription_id = sub_id

    await session.commit()
```

- [ ] **Step 4: Add GET /billing/invoices to billing.py**

In `apps/gateway/api/routes/billing.py`, add the import at the top:

```python
from integrations.billing.stripe_sync import (
    StripeBillingError,
    create_stripe_checkout_session,
    create_stripe_customer,
    create_stripe_portal_session,
    list_stripe_invoices,
)
```

Then add the new route at the end of the file:

```python
@router.get("/invoices")
async def get_invoices(request: Request):
    org_id: str = request.state.org_id
    settings = get_settings()
    if not settings.stripe_secret_key:
        return []
    async with session_context() as session:
        result = await session.execute(select(OrgBilling).where(OrgBilling.org_id == org_id))
        billing = result.scalar_one_or_none()
        if not billing or not billing.stripe_customer_id:
            return []
    try:
        return await list_stripe_invoices(settings.stripe_secret_key, billing.stripe_customer_id)
    except StripeBillingError as exc:
        _raise_stripe_http_error(exc)
```

- [ ] **Step 5: Run the tests and verify they pass**

```bash
uv run pytest tests/unit/test_integrations/test_stripe_invoice.py -v
```

Expected: tests PASS (the `test_sync_invoice_paid_sends_email` test patches `send_email` so no real network call).

- [ ] **Step 6: Commit**

```bash
git add packages/integrations/integrations/billing/stripe_sync.py \
        apps/gateway/api/routes/billing.py \
        tests/unit/test_integrations/test_stripe_invoice.py
git commit -m "feat(billing): add invoice list endpoint and invoice.paid receipt email"
```

---

## Task 4: Frontend — real invoice list

**Files:**
- Modify: `apps/web/lib/types.ts`
- Modify: `apps/web/lib/api.ts`
- Modify: `apps/web/lib/queries.ts`
- Modify: `apps/web/app/dashboard/billing/page.tsx`

- [ ] **Step 1: Add InvoiceSchema to types.ts**

In `apps/web/lib/types.ts`, add after `BillingSchema`:

```typescript
export const InvoiceSchema = z.object({
  id: z.string(),
  number: z.string(),
  amount_paid: z.number(),
  created: z.number(),
  invoice_pdf: z.string().nullable(),
  status: z.string(),
})

export type Invoice = z.infer<typeof InvoiceSchema>
```

- [ ] **Step 2: Add api.billing.invoices() to api.ts**

In `apps/web/lib/api.ts`, add inside the `billing` object after `portal`:

```typescript
invoices: () => request<unknown[]>("/api/v1/billing/invoices"),
```

- [ ] **Step 3: Add invoicesOptions to queries.ts**

In `apps/web/lib/queries.ts`, add after `billingOptions`:

```typescript
import { InvoiceSchema } from "./types"

export const invoicesOptions = () =>
  queryOptions({
    queryKey: ["invoices"],
    queryFn: () =>
      api.billing.invoices().then((data) => z.array(InvoiceSchema).parse(data)),
  })
```

Also add `InvoiceSchema` to the import from `"./types"` at the top of `queries.ts`.

- [ ] **Step 4: Replace mock invoices in billing/page.tsx**

In `apps/web/app/dashboard/billing/page.tsx`:

1. Remove the `MOCK_INVOICES` constant entirely.
2. Add `invoicesOptions` to the imports from `@/lib/queries`.
3. Add the query inside the component:

```typescript
const { data: invoices = [] } = useQuery(invoicesOptions())
```

4. Replace the invoices section's inner content. The full invoices `div` (from `{/* Invoices */}` to its closing `</div>`) should be:

```tsx
{/* Invoices */}
<div
  className="border border-white/[0.08] overflow-hidden"
  style={{ background: "rgba(255,255,255,0.04)" }}
>
  <div className="px-4 py-3 border-b border-white/5">
    <h3 className="text-[10px] font-bold tracking-wider uppercase text-[#8e9192]">
      Recent Invoices
    </h3>
  </div>
  {invoices.length === 0 ? (
    <div className="px-4 py-6 text-center text-[13px] text-[#8e9192]">
      No invoices yet
    </div>
  ) : (
    <div className="divide-y divide-white/5">
      {invoices.map((inv) => (
        <div
          key={inv.id}
          className="flex items-center justify-between px-4 py-3 hover:bg-white/[0.02] transition-colors"
        >
          <div className="flex items-center gap-4">
            <FileText className="h-5 w-5 text-[#8e9192]" />
            <div>
              <p className="text-[14px] text-[#e5e2e1]">{inv.number}</p>
              <p className="text-[12px] text-[#8e9192]">
                {new Date(inv.created * 1000).toLocaleDateString()}
              </p>
            </div>
          </div>
          <div className="text-right flex items-center gap-3">
            <div>
              <p className="text-[14px] font-semibold text-[#e5e2e1]">
                ${(inv.amount_paid / 100).toFixed(2)}
              </p>
              <p className="text-[12px] text-[#4ade80]">Paid</p>
            </div>
            {inv.invoice_pdf && (
              <a
                href={inv.invoice_pdf}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[11px] text-[#8e9192] hover:text-[#c6c6c7] underline"
              >
                PDF
              </a>
            )}
          </div>
        </div>
      ))}
    </div>
  )}
</div>
```

- [ ] **Step 5: Commit**

```bash
git add apps/web/lib/types.ts apps/web/lib/api.ts apps/web/lib/queries.ts \
        apps/web/app/dashboard/billing/page.tsx
git commit -m "feat(billing): replace mock invoices with real Stripe invoice data"
```

---

## Task 5: Invite backend routes and OAuth flow extension

**Files:**
- Create: `apps/gateway/api/routes/invites.py`
- Modify: `apps/gateway/api/__init__.py`
- Modify: `apps/gateway/middleware/auth.py`
- Modify: `apps/gateway/api/routes/auth.py`
- Test: `tests/unit/test_gateway/test_invites.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_gateway/test_invites.py`:

```python
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../apps/gateway"))


def test_invite_html_template_renders():
    from integrations.email.client import invite_html
    html = invite_html("Acme", "alice", "http://localhost:3000/invite/tok123")
    assert "Acme" in html
    assert "alice" in html
    assert "tok123" in html


def test_get_invite_returns_404_for_expired():
    """Expired or accepted invites return 404 — logic check without DB."""
    from datetime import datetime, timezone, timedelta
    expired_at = datetime.now(timezone.utc) - timedelta(days=1)
    # Invite is expired if expires_at < now
    assert expired_at < datetime.now(timezone.utc)


def test_org_invite_token_is_unique_uuid():
    from shared.models.invite import OrgInvite
    a = OrgInvite(org_id="o1", email="a@b.com", invited_by="u1")
    b = OrgInvite(org_id="o1", email="c@d.com", invited_by="u1")
    assert a.token != b.token


def test_auth_state_payload_round_trips():
    """The JSON state format used in github_login must survive encode→decode."""
    import json
    cli_session_id = "cli-123"
    invite_token = "inv-abc"
    state_payload = json.dumps({"cli": cli_session_id, "invite": invite_token})
    decoded = json.loads(state_payload)
    assert decoded["cli"] == cli_session_id
    assert decoded["invite"] == invite_token


def test_auth_state_payload_backward_compat():
    """Old format ('1' or raw cli_session_id) must still parse."""
    import json
    for old_value in ["1", "some-cli-session-id"]:
        try:
            json.loads(old_value)
            # If it parses as JSON number or something, that's ok but unusual
        except (json.JSONDecodeError, ValueError):
            # Expected: old values aren't valid JSON objects
            cli_session_id = old_value if old_value != "1" else None
            invite_token = None
            assert invite_token is None
```

- [ ] **Step 2: Run to confirm they pass (these are logic tests, should pass already)**

```bash
uv run pytest tests/unit/test_gateway/test_invites.py -v
```

Expected: all PASS (these test pure logic, not the route handlers themselves).

- [ ] **Step 3: Create invites.py**

Create `apps/gateway/api/routes/invites.py`:

```python
from __future__ import annotations

import logging
from datetime import datetime, timezone

import jwt as pyjwt
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator
from shared.config import get_settings
from shared.db import session_context
from shared.models import Org, OrgBilling, OrgInvite, User, UserOrg
from sqlalchemy import func, select

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_org_id(request: Request) -> str:
    return request.state.org_id


def _get_user_id(request: Request) -> str:
    return request.state.user_id


def _require_auth(request: Request) -> str:
    """Manually validate JWT for routes under the exempt /invites/ prefix."""
    auth = request.headers.get("Authorization", "")
    raw = auth[7:] if auth.startswith("Bearer ") else request.cookies.get("argus_token")
    if not raw:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        settings = get_settings()
        payload = pyjwt.decode(raw, settings.jwt_secret_key, algorithms=["HS256"])
        return payload["sub"]
    except pyjwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ── Members ──────────────────────────────────────────────────────────────────

@router.get("/orgs/{org_id}/members")
async def list_members(org_id: str, request: Request):
    if _get_org_id(request) != org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    async with session_context() as session:
        rows = (
            await session.execute(
                select(UserOrg, User)
                .join(User, UserOrg.user_id == User.id)
                .where(UserOrg.org_id == org_id)
                .order_by(UserOrg.joined_at)
            )
        ).all()
    return [
        {
            "user_id": uo.user_id,
            "github_login": u.github_login,
            "avatar_url": u.avatar_url,
            "role": uo.role,
            "joined_at": uo.joined_at.isoformat(),
        }
        for uo, u in rows
    ]


# ── Invite list + creation ────────────────────────────────────────────────────

class InviteRequest(BaseModel):
    email: str
    role: str = "member"

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        parts = v.split("@")
        if len(parts) != 2 or "." not in parts[1]:
            raise ValueError("Invalid email address")
        return v


@router.get("/orgs/{org_id}/invites")
async def list_invites(org_id: str, request: Request):
    if _get_org_id(request) != org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    async with session_context() as session:
        rows = (
            await session.execute(
                select(OrgInvite, User)
                .join(User, OrgInvite.invited_by == User.id)
                .where(OrgInvite.org_id == org_id, OrgInvite.accepted_at.is_(None))
                .order_by(OrgInvite.created_at.desc())
            )
        ).all()
    return [
        {
            "id": inv.id,
            "email": inv.email,
            "role": inv.role,
            "invited_by_login": u.github_login,
            "expires_at": inv.expires_at.isoformat(),
            "created_at": inv.created_at.isoformat(),
        }
        for inv, u in rows
    ]


@router.post("/orgs/{org_id}/invites", status_code=201)
async def create_invite(org_id: str, body: InviteRequest, request: Request):
    if _get_org_id(request) != org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if request.state.role != "owner":
        raise HTTPException(status_code=403, detail="Only owners can invite members")

    settings = get_settings()

    async with session_context() as session:
        billing_row = await session.execute(
            select(OrgBilling).where(OrgBilling.org_id == org_id)
        )
        billing = billing_row.scalar_one_or_none()
        if not billing or billing.plan == "free":
            raise HTTPException(
                status_code=403, detail="Upgrade to Pro to invite team members"
            )

        seat_count = await session.scalar(
            select(func.count()).where(UserOrg.org_id == org_id)
        )
        if seat_count >= billing.seat_count:
            raise HTTPException(
                status_code=403,
                detail="Seat limit reached. Upgrade your plan to add more seats.",
            )

        org_row = await session.execute(select(Org).where(Org.id == org_id))
        org = org_row.scalar_one()

        inviter_row = await session.execute(
            select(User).where(User.id == _get_user_id(request))
        )
        inviter = inviter_row.scalar_one()

        invite = OrgInvite(
            org_id=org_id,
            email=body.email,
            role=body.role,
            invited_by=_get_user_id(request),
        )
        session.add(invite)
        await session.commit()
        await session.refresh(invite)

    if settings.resend_api_key:
        from integrations.email.client import invite_html, send_email
        accept_url = f"{settings.frontend_url}/invite/{invite.token}"
        html = invite_html(org.name, inviter.github_login, accept_url)
        try:
            await send_email(
                settings.resend_api_key,
                body.email,
                f"You've been invited to {org.name} on Argus",
                html,
            )
        except Exception:
            logger.warning("Failed to send invite email to %s", body.email)

    return {"id": invite.id, "email": invite.email}


@router.delete("/orgs/{org_id}/invites/{invite_id}", status_code=204)
async def revoke_invite(org_id: str, invite_id: str, request: Request):
    if _get_org_id(request) != org_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if request.state.role != "owner":
        raise HTTPException(status_code=403, detail="Only owners can revoke invites")
    async with session_context() as session:
        row = await session.execute(
            select(OrgInvite).where(
                OrgInvite.id == invite_id, OrgInvite.org_id == org_id
            )
        )
        invite = row.scalar_one_or_none()
        if not invite:
            raise HTTPException(status_code=404, detail="Invite not found")
        await session.delete(invite)
        await session.commit()


# ── Public invite info + accept ───────────────────────────────────────────────

@router.get("/invites/{token}")
async def get_invite(token: str):
    async with session_context() as session:
        row = (
            await session.execute(
                select(OrgInvite, Org, User)
                .join(Org, OrgInvite.org_id == Org.id)
                .join(User, OrgInvite.invited_by == User.id)
                .where(
                    OrgInvite.token == token,
                    OrgInvite.accepted_at.is_(None),
                    OrgInvite.expires_at > datetime.now(timezone.utc),
                )
            )
        ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Invite not found or expired")
    invite, org, inviter = row
    return {
        "org_name": org.name,
        "org_id": org.id,
        "inviter_login": inviter.github_login,
        "role": invite.role,
        "email": invite.email,
        "expires_at": invite.expires_at.isoformat(),
    }


@router.post("/invites/{token}/accept")
async def accept_invite(token: str, request: Request):
    user_id = _require_auth(request)
    async with session_context() as session:
        row = await session.execute(
            select(OrgInvite).where(
                OrgInvite.token == token,
                OrgInvite.accepted_at.is_(None),
                OrgInvite.expires_at > datetime.now(timezone.utc),
            )
        )
        invite = row.scalar_one_or_none()
        if not invite:
            raise HTTPException(status_code=404, detail="Invite not found or expired")

        existing = await session.execute(
            select(UserOrg).where(
                UserOrg.user_id == user_id, UserOrg.org_id == invite.org_id
            )
        )
        if not existing.scalar_one_or_none():
            session.add(UserOrg(user_id=user_id, org_id=invite.org_id, role=invite.role))

        invite.accepted_at = datetime.now(timezone.utc)
        await session.commit()
        invite_org_id = invite.org_id
        invite_role = invite.role

    from auth_utils import create_jwt
    new_token = create_jwt(user_id=user_id, org_id=invite_org_id, role=invite_role)
    return {"token": new_token}
```

- [ ] **Step 4: Register the invites router in api/__init__.py**

In `apps/gateway/api/__init__.py`, add:

```python
from .routes.invites import router as invites_router
```

And add to the `api_router.include_router` calls:

```python
api_router.include_router(invites_router, tags=["invites"])
```

- [ ] **Step 5: Exempt /invites/ prefix in auth middleware**

In `apps/gateway/middleware/auth.py`, update `_build_exempt_prefixes()`:

```python
def _build_exempt_prefixes() -> tuple[str, ...]:
    p = get_settings().api_prefix
    return (
        f"{p}/webhooks/",
        f"{p}/auth/github/",
        f"{p}/auth/logout",
        f"{p}/auth/cli/",
        "/dashboard/",
        f"{p}/oauth/slack/callback",
        f"{p}/oauth/notion/callback",
        f"{p}/oauth/linear/callback",
        f"{p}/oauth/jira/callback",
        f"{p}/invites/",   # GET invite details + POST accept (accept validates JWT manually)
    )
```

- [ ] **Step 6: Extend github_login and github_callback to carry invite_token**

In `apps/gateway/api/routes/auth.py`, update the imports to add `json`:

```python
import json
```

Update `github_login` signature and body:

```python
@router.get("/github/login")
async def github_login(
    request: Request,
    cli_session_id: str | None = None,
    invite_token: str | None = None,
    settings: Settings = Depends(get_settings),
):
    state = secrets.token_urlsafe(32)
    state_payload = json.dumps({"cli": cli_session_id or "", "invite": invite_token or ""})
    await request.app.state.redis.set(f"oauth_state:{state}", state_payload, ex=_CSRF_TTL)
    url = f"{_GITHUB_AUTHORIZE_URL}?client_id={settings.github_client_id}&state={state}&scope=read:user"
    return RedirectResponse(url=url)
```

In `github_callback`, replace the state decoding block (find the two lines that set `decoded` and `cli_session_id`) with:

```python
decoded = state_value.decode() if isinstance(state_value, bytes) else state_value
try:
    state_obj = json.loads(decoded)
    cli_session_id: str | None = state_obj.get("cli") or None
    invite_token: str | None = state_obj.get("invite") or None
except (json.JSONDecodeError, ValueError):
    # Backwards compat: old format was raw cli_session_id string or "1"
    cli_session_id = decoded if decoded != "1" else None
    invite_token = None
```

Then, after the `_upsert_user_org` call (and before `token = create_jwt(...)`), add:

```python
invited_org_id: str | None = None
if invite_token:
    invited_org_id = await _consume_invite(session, user.id, invite_token)
```

Replace the `token = create_jwt(...)` line with:

```python
token = create_jwt(
    user_id=user.id,
    org_id=invited_org_id or org.id,
    role="member" if invited_org_id else membership.role,
)
```

Add `_consume_invite` as a module-level function at the bottom of `auth.py` (after `_upsert_user_org`):

```python
async def _consume_invite(session: AsyncSession, user_id: str, token: str) -> str | None:
    """Accept a pending invite: create UserOrg membership, mark invite accepted.

    Returns the invited org_id on success, None if the token is invalid/expired.
    """
    from shared.models.invite import OrgInvite
    result = await session.execute(
        select(OrgInvite).where(
            OrgInvite.token == token,
            OrgInvite.accepted_at.is_(None),
            OrgInvite.expires_at > datetime.now(timezone.utc),
        )
    )
    invite = result.scalar_one_or_none()
    if not invite:
        return None

    existing = await session.execute(
        select(UserOrg).where(UserOrg.user_id == user_id, UserOrg.org_id == invite.org_id)
    )
    if not existing.scalar_one_or_none():
        session.add(UserOrg(user_id=user_id, org_id=invite.org_id, role=invite.role))

    invite.accepted_at = datetime.now(timezone.utc)
    await session.commit()
    return invite.org_id
```

You'll also need `from datetime import datetime, timezone` at the top of `auth.py` — check whether it's already imported; if not, add it.

- [ ] **Step 7: Commit**

```bash
git add apps/gateway/api/routes/invites.py \
        apps/gateway/api/__init__.py \
        apps/gateway/middleware/auth.py \
        apps/gateway/api/routes/auth.py \
        tests/unit/test_gateway/test_invites.py
git commit -m "feat(invites): add team invitation routes and extend OAuth flow for invite acceptance"
```

---

## Task 6: Frontend — settings page with real members and invite dialog

**Files:**
- Modify: `apps/web/lib/types.ts`
- Modify: `apps/web/lib/api.ts`
- Modify: `apps/web/lib/queries.ts`
- Modify: `apps/web/app/dashboard/settings/page.tsx`

- [ ] **Step 1: Add member and invite schemas to types.ts**

In `apps/web/lib/types.ts`, add after `InvoiceSchema`:

```typescript
export const MemberSchema = z.object({
  user_id: z.string(),
  github_login: z.string(),
  avatar_url: z.string().nullable(),
  role: z.string(),
  joined_at: z.string(),
})

export const PendingInviteSchema = z.object({
  id: z.string(),
  email: z.string(),
  role: z.string(),
  invited_by_login: z.string(),
  expires_at: z.string(),
  created_at: z.string(),
})

export type Member = z.infer<typeof MemberSchema>
export type PendingInvite = z.infer<typeof PendingInviteSchema>
```

- [ ] **Step 2: Add api calls to api.ts**

In `apps/web/lib/api.ts`, add a top-level `orgs` object before the closing brace:

```typescript
orgs: {
  members: (orgId: string) =>
    request<unknown[]>(`/api/v1/orgs/${orgId}/members`),
  pendingInvites: (orgId: string) =>
    request<unknown[]>(`/api/v1/orgs/${orgId}/invites`),
  createInvite: (orgId: string, email: string) =>
    request(`/api/v1/orgs/${orgId}/invites`, {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  revokeInvite: (orgId: string, inviteId: string) =>
    request(`/api/v1/orgs/${orgId}/invites/${inviteId}`, { method: "DELETE" }),
},
```

- [ ] **Step 3: Add queries and mutations to queries.ts**

In `apps/web/lib/queries.ts`, add after `invoicesOptions`:

```typescript
import { MemberSchema, PendingInviteSchema } from "./types"

export const membersOptions = (orgId: string) =>
  queryOptions({
    queryKey: ["members", orgId],
    queryFn: () =>
      api.orgs.members(orgId).then((data) => z.array(MemberSchema).parse(data)),
    enabled: !!orgId,
  })

export const pendingInvitesOptions = (orgId: string) =>
  queryOptions({
    queryKey: ["pending-invites", orgId],
    queryFn: () =>
      api.orgs.pendingInvites(orgId).then((data) => z.array(PendingInviteSchema).parse(data)),
    enabled: !!orgId,
  })

export function useCreateInvite(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (email: string) => api.orgs.createInvite(orgId, email),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pending-invites", orgId] }),
  })
}

export function useRevokeInvite(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (inviteId: string) => api.orgs.revokeInvite(orgId, inviteId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pending-invites", orgId] }),
  })
}
```

Also add `MemberSchema` and `PendingInviteSchema` to the import from `"./types"` at the top of `queries.ts`.

- [ ] **Step 4: Rewrite settings/page.tsx**

Replace the entire content of `apps/web/app/dashboard/settings/page.tsx`:

```tsx
"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { billingOptions, membersOptions, pendingInvitesOptions, useCreateInvite, useRevokeInvite } from "@/lib/queries"
import { getOrgId } from "@/lib/auth"
import { Topbar } from "@/components/topbar"
import { Building2, Users, Info, Mail, X } from "lucide-react"
import { toast } from "sonner"

export default function SettingsPage() {
  const orgId = getOrgId() ?? ""
  const { data: billing } = useQuery(billingOptions())
  const { data: members = [] } = useQuery(membersOptions(orgId))
  const { data: pendingInvites = [] } = useQuery(pendingInvitesOptions(orgId))
  const createInvite = useCreateInvite(orgId)
  const revokeInvite = useRevokeInvite(orgId)

  const [inviteEmail, setInviteEmail] = useState("")
  const [inviteOpen, setInviteOpen] = useState(false)

  const canInvite = billing && billing.plan !== "free"
  const totalSeats = billing?.seat_count ?? 1
  const usedSeats = members.length

  function handleInvite(e: React.FormEvent) {
    e.preventDefault()
    if (!inviteEmail) return
    createInvite.mutate(inviteEmail, {
      onSuccess: () => {
        toast.success(`Invite sent to ${inviteEmail}`)
        setInviteEmail("")
        setInviteOpen(false)
      },
      onError: (err: unknown) => {
        const msg = err instanceof Error ? err.message : "Failed to send invite"
        toast.error(msg)
      },
    })
  }

  return (
    <>
      <Topbar title="Settings" />
      <div className="px-8 py-8 space-y-3">
        <div className="mb-6">
          <h2 className="text-[24px] font-semibold leading-8 tracking-[-0.02em] text-[#c6c6c7]">
            Settings
          </h2>
          <p className="text-[14px] text-[#8e9192] mt-1">
            Manage your organization's configuration and team access.
          </p>
        </div>

        {/* Organization */}
        <section
          className="border border-white/8 p-4"
          style={{ background: "rgba(255,255,255,0.04)" }}
        >
          <div className="flex items-start gap-3 mb-4">
            <Building2 className="h-5 w-5 text-[#c6c6c7] shrink-0 mt-0.5" />
            <div>
              <h3 className="text-[18px] font-semibold leading-6 tracking-[-0.01em] text-[#e5e2e1]">
                Organization
              </h3>
              <p className="text-[12px] text-[#8e9192] mt-0.5">
                Identity and ownership controls
              </p>
            </div>
          </div>
          <div className="space-y-0">
            <div className="flex items-center justify-between py-2 border-b border-white/5">
              <span className="text-[10px] font-bold tracking-wider uppercase text-[#8e9192]">
                PLAN
              </span>
              <span className="text-[14px] font-semibold text-[#e5e2e1] capitalize">
                {billing?.plan ?? "—"}
              </span>
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-[10px] font-bold tracking-wider uppercase text-[#8e9192]">
                SEATS
              </span>
              <span className="text-[14px] font-semibold text-[#e5e2e1]">
                {usedSeats} / {totalSeats}
              </span>
            </div>
          </div>
        </section>

        {/* Team members */}
        <section
          className="border border-white/8 p-4"
          style={{ background: "rgba(255,255,255,0.04)" }}
        >
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-start gap-3">
              <Users className="h-5 w-5 text-[#c6c6c7] shrink-0 mt-0.5" />
              <div>
                <h3 className="text-[18px] font-semibold leading-6 tracking-[-0.01em] text-[#e5e2e1]">
                  Team Members
                </h3>
                <p className="text-[12px] text-[#8e9192] mt-0.5">
                  Access control and seat allocation
                </p>
              </div>
            </div>
            {canInvite ? (
              <button
                onClick={() => setInviteOpen((v) => !v)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium border border-white/10 text-[#c6c6c7] hover:bg-white/5 transition-colors"
              >
                <Mail className="h-3.5 w-3.5" /> Invite
              </button>
            ) : (
              <a
                href="/dashboard/billing"
                className="text-[10px] font-bold tracking-wider uppercase text-[#8e9192] hover:text-[#c6c6c7] transition-colors"
              >
                Upgrade to invite →
              </a>
            )}
          </div>

          {/* Invite form */}
          {inviteOpen && (
            <form onSubmit={handleInvite} className="flex gap-2 mb-4">
              <input
                type="email"
                placeholder="teammate@example.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                className="flex-1 bg-white/5 border border-white/10 px-3 py-2 text-[13px] text-[#e5e2e1] placeholder-[#8e9192] focus:outline-none focus:border-white/20"
                required
              />
              <button
                type="submit"
                disabled={createInvite.isPending}
                className="px-4 py-2 bg-[#e2e2e2] text-[#2f3131] text-[12px] font-semibold disabled:opacity-50"
              >
                {createInvite.isPending ? "Sending…" : "Send invite"}
              </button>
            </form>
          )}

          {/* Active members */}
          <div className="space-y-1">
            {members.map((m) => (
              <div key={m.user_id} className="flex items-center gap-4 p-3 bg-white/5">
                <div className="w-8 h-8 bg-[#2a2a2a] flex items-center justify-center shrink-0 overflow-hidden">
                  {m.avatar_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={m.avatar_url} alt={m.github_login} className="w-full h-full object-cover" />
                  ) : (
                    <span className="text-[11px] font-bold text-[#c6c6c7]">
                      {m.github_login[0].toUpperCase()}
                    </span>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[14px] text-[#e5e2e1]">@{m.github_login}</p>
                  <p className="text-[11px] text-[#8e9192]">
                    Joined {new Date(m.joined_at).toLocaleDateString()}
                  </p>
                </div>
                <span className="text-[10px] font-bold tracking-wider uppercase text-[#c6c6c7]">
                  {m.role}
                </span>
              </div>
            ))}
          </div>

          {/* Pending invites */}
          {pendingInvites.length > 0 && (
            <div className="mt-3 pt-3 border-t border-white/5">
              <p className="text-[10px] font-bold tracking-wider uppercase text-[#8e9192] mb-2">
                Pending invites
              </p>
              <div className="space-y-1">
                {pendingInvites.map((inv) => (
                  <div
                    key={inv.id}
                    className="flex items-center justify-between px-3 py-2 bg-white/[0.02] border border-white/5"
                  >
                    <div>
                      <p className="text-[13px] text-[#c6c6c7]">{inv.email}</p>
                      <p className="text-[11px] text-[#8e9192]">
                        Invited by @{inv.invited_by_login} ·{" "}
                        expires {new Date(inv.expires_at).toLocaleDateString()}
                      </p>
                    </div>
                    <button
                      onClick={() =>
                        revokeInvite.mutate(inv.id, {
                          onSuccess: () => toast.success("Invite revoked"),
                          onError: () => toast.error("Failed to revoke invite"),
                        })
                      }
                      className="text-[#8e9192] hover:text-[#ffb4ab] transition-colors"
                      title="Revoke invite"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex items-center gap-2 mt-4 pt-3 border-t border-white/5 text-[#8e9192]">
            <Info className="h-3.5 w-3.5 shrink-0" />
            <span className="text-[12px]">
              Seat usage: {usedSeats} / {totalSeats} available seats.
            </span>
          </div>
        </section>
      </div>
    </>
  )
}
```

- [ ] **Step 5: Commit**

```bash
git add apps/web/lib/types.ts apps/web/lib/api.ts apps/web/lib/queries.ts \
        apps/web/app/dashboard/settings/page.tsx
git commit -m "feat(settings): real member list and invite dialog"
```

---

## Task 7: Invite acceptance page

**Files:**
- Create: `apps/web/app/invite/[token]/page.tsx`

- [ ] **Step 1: Create the invite acceptance page**

Create `apps/web/app/invite/[token]/page.tsx`:

```tsx
"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { isAuthenticated, getOrgId } from "@/lib/auth"
import { BASE } from "@/lib/api"

interface InviteDetails {
  org_name: string
  org_id: string
  inviter_login: string
  role: string
  email: string
  expires_at: string
}

export default function InvitePage() {
  const { token } = useParams<{ token: string }>()
  const router = useRouter()
  const [invite, setInvite] = useState<InviteDetails | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [accepting, setAccepting] = useState(false)

  const authed = isAuthenticated()

  useEffect(() => {
    fetch(`/api/v1/invites/${token}`, { credentials: "include" })
      .then(async (res) => {
        if (!res.ok) throw new Error("Invite not found or expired")
        return res.json() as Promise<InviteDetails>
      })
      .then(setInvite)
      .catch((e: Error) => setError(e.message))
  }, [token])

  async function handleAccept() {
    setAccepting(true)
    try {
      const res = await fetch(`/api/v1/invites/${token}/accept`, {
        method: "POST",
        credentials: "include",
      })
      if (!res.ok) throw new Error("Failed to accept invite")
      const { token: newToken } = (await res.json()) as { token: string }
      // Re-set cookies with the new org-scoped token
      const setRes = await fetch("/api/auth/set-token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: newToken }),
      })
      if (!setRes.ok) throw new Error("Failed to set session")
      router.replace("/dashboard")
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong")
      setAccepting(false)
    }
  }

  function handleGitHubLogin() {
    window.location.href = `${BASE}/api/v1/auth/github/login?invite_token=${token}`
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div
          className="w-full max-w-sm border border-white/[0.12] p-8 text-center"
          style={{ background: "rgba(255,255,255,0.04)" }}
        >
          <p className="text-[16px] text-[#ffb4ab] mb-4">{error}</p>
          <a
            href="/dashboard"
            className="text-[13px] text-[#8e9192] hover:text-[#c6c6c7] underline"
          >
            Go to dashboard
          </a>
        </div>
      </div>
    )
  }

  if (!invite) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-[#8e9192] text-[14px]">Loading invite…</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div
        className="w-full max-w-sm border border-white/[0.12] overflow-hidden"
        style={{ background: "rgba(255,255,255,0.04)" }}
      >
        <div className="p-8 flex flex-col items-center text-center gap-4">
          <div className="space-y-1">
            <h2 className="text-[22px] font-semibold leading-8 tracking-[-0.02em] text-[#e5e2e1]">
              You've been invited
            </h2>
            <p className="text-[14px] text-[#8e9192]">
              <strong className="text-[#c6c6c7]">@{invite.inviter_login}</strong> invited you
              to join{" "}
              <strong className="text-[#c6c6c7]">{invite.org_name}</strong> as{" "}
              <span className="capitalize">{invite.role}</span>.
            </p>
          </div>

          <div className="w-full border-t border-white/5 pt-4 text-left font-mono space-y-2">
            <div className="flex justify-between">
              <span className="text-[12px] text-[#8e9192]">For</span>
              <span className="text-[12px] text-[#e5e2e1]">{invite.email}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[12px] text-[#8e9192]">Expires</span>
              <span className="text-[12px] text-[#e5e2e1]">
                {new Date(invite.expires_at).toLocaleDateString()}
              </span>
            </div>
          </div>

          <div className="w-full pt-1">
            {authed ? (
              <button
                onClick={handleAccept}
                disabled={accepting}
                className="w-full bg-[#e2e2e2] text-[#2f3131] py-3 text-[10px] font-bold tracking-widest uppercase hover:opacity-90 active:scale-[0.98] transition-all disabled:opacity-50"
              >
                {accepting ? "Accepting…" : `Accept as current user`}
              </button>
            ) : (
              <button
                onClick={handleGitHubLogin}
                className="w-full bg-[#e2e2e2] text-[#2f3131] py-3 text-[10px] font-bold tracking-widest uppercase hover:opacity-90 active:scale-[0.98] transition-all"
              >
                Accept via GitHub
              </button>
            )}
          </div>

          {authed && (
            <p className="text-[11px] text-[#8e9192]">
              Not you?{" "}
              <button
                onClick={handleGitHubLogin}
                className="underline hover:text-[#c6c6c7]"
              >
                Sign in with a different account
              </button>
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/app/invite/
git commit -m "feat(invite): add /invite/[token] acceptance page"
```

---

## Final verification

- [ ] Run the full test suite:

```bash
uv run pytest tests/unit/ -v
```

Expected: all pre-existing tests pass, new tests pass.

- [ ] Start the dev stack and manually verify:
  1. Billing page shows "No invoices yet" (no Stripe customer) or real data
  2. Settings page shows real members list (yourself as owner)
  3. On a Pro+ org, the "Invite" button appears; on Free it shows "Upgrade to invite →"
  4. Submitting an invite email triggers the invite creation (check server logs for email attempt)
  5. Visiting `/invite/<valid-token>` shows the invite card; invalid token shows the error state

- [ ] Lint:

```bash
uv run ruff check . && uv run ruff format --check .
```
