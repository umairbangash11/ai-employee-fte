"""Reader for accounting data from vault/Accounting/.

Parses invoices/ and payments/ subdirectories to aggregate
accounting summary data.
"""

from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import frontmatter

from briefing_generator.config import VAULT_DIRS
from briefing_generator.models import AccountingSummary, OverdueInvoice


def _parse_amount(value) -> Decimal | None:
    """Parse amount from frontmatter value."""
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _parse_date(value) -> date | None:
    """Parse date from frontmatter value."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (ValueError, AttributeError):
        return None


def read_accounting_data(
    vault_path: Path,
    data_gaps: list[str] | None = None,
) -> AccountingSummary:
    """Read accounting data from vault/Accounting/.

    Args:
        vault_path: Path to vault root.
        data_gaps: Optional list to append parse errors.

    Returns:
        AccountingSummary with aggregated data.
    """
    accounting_dir = vault_path / VAULT_DIRS["accounting"]
    if not accounting_dir.is_dir():
        return AccountingSummary(has_data=False)

    invoices_dir = accounting_dir / "invoices"
    payments_dir = accounting_dir / "payments"

    total_invoiced = Decimal("0")
    invoice_count = 0
    total_paid = Decimal("0")
    payment_count = 0
    overdue_invoices: list[OverdueInvoice] = []
    has_data = False
    today = date.today()

    # Process invoices
    if invoices_dir.is_dir():
        for md_file in invoices_dir.rglob("*.md"):
            try:
                post = frontmatter.load(md_file)
                metadata = post.metadata

                amount = _parse_amount(metadata.get("amount"))
                if amount is None:
                    if data_gaps is not None:
                        data_gaps.append(f"{md_file}: missing or invalid amount")
                    continue

                has_data = True
                total_invoiced += amount
                invoice_count += 1

                # Check for overdue
                status = metadata.get("status", "").lower()
                due_date = _parse_date(metadata.get("due_date"))

                is_overdue = status == "overdue" or (
                    due_date is not None and due_date < today and status != "paid"
                )

                if is_overdue and due_date:
                    partner = metadata.get("odoo_partner") or metadata.get("partner") or "Unknown"
                    days_overdue = (today - due_date).days
                    overdue_invoices.append(
                        OverdueInvoice(
                            file_path=md_file,
                            partner=partner,
                            amount=amount,
                            due_date=due_date,
                            days_overdue=days_overdue,
                        )
                    )

            except Exception as e:
                if data_gaps is not None:
                    data_gaps.append(f"{md_file}: {e}")
                continue

    # Process payments
    if payments_dir.is_dir():
        for md_file in payments_dir.rglob("*.md"):
            try:
                post = frontmatter.load(md_file)
                metadata = post.metadata

                amount = _parse_amount(metadata.get("amount"))
                if amount is None:
                    if data_gaps is not None:
                        data_gaps.append(f"{md_file}: missing or invalid amount")
                    continue

                has_data = True
                total_paid += amount
                payment_count += 1

            except Exception as e:
                if data_gaps is not None:
                    data_gaps.append(f"{md_file}: {e}")
                continue

    # Sort overdue invoices by days overdue descending
    overdue_invoices.sort(key=lambda x: x.days_overdue, reverse=True)

    return AccountingSummary(
        total_invoiced=total_invoiced,
        invoice_count=invoice_count,
        total_paid=total_paid,
        payment_count=payment_count,
        overdue_invoices=overdue_invoices,
        has_data=has_data,
    )
