from __future__ import annotations

from html import escape

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
  <p style="color:#666;margin:0 0 24px">Your Argus {escape(plan.title())} plan is now active.</p>
  <table style="width:100%;border-collapse:collapse;margin-bottom:24px">
    <tr>
      <td style="padding:8px 0;border-bottom:1px solid #eee;color:#666">Invoice</td>
      <td style="padding:8px 0;border-bottom:1px solid #eee;text-align:right">{escape(invoice_number)}</td>
    </tr>
    <tr>
      <td style="padding:8px 0;color:#666">Amount paid</td>
      <td style="padding:8px 0;text-align:right;font-weight:600">{amount}</td>
    </tr>
  </table>
  <a href="{escape(invoice_pdf_url)}"
     style="background:#000;color:#fff;padding:12px 24px;text-decoration:none;font-size:14px;display:inline-block">
    Download invoice PDF
  </a>
</div>
"""


def invite_html(org_name: str, inviter_login: str, accept_url: str) -> str:
    return f"""
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:24px">
  <h2 style="margin:0 0 8px">You&#39;ve been invited to {escape(org_name)}</h2>
  <p style="color:#666;margin:0 0 24px">
    <strong>{escape(inviter_login)}</strong> has invited you to join their team on Argus.
  </p>
  <a href="{escape(accept_url)}"
     style="background:#000;color:#fff;padding:12px 24px;text-decoration:none;font-size:14px;display:inline-block">
    Accept invite
  </a>
  <p style="color:#999;font-size:12px;margin-top:24px">
    This invite expires in 7 days. If you didn&#39;t expect this, you can safely ignore this email.
  </p>
</div>
"""
