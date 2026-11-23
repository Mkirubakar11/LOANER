
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import (
    Loan,
    Payment,
    LoanCreditBalance,
    LoanCreditTransaction,
)


# --------------------------------------------------
# MONEY VALIDATION
# --------------------------------------------------

def money(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError("Invalid monetary amount.")

    if not amount.is_finite():
        raise ValidationError("Amount must be a finite number.")

    rounded = amount.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    if amount != rounded:
        raise ValidationError(
            "Amount can have a maximum of two decimal places."
        )

    if rounded <= Decimal("0.00"):
        raise ValidationError("Amount must be greater than zero.")

    return rounded


# --------------------------------------------------
# GET OR CREATE LOAN CREDIT BALANCE
# --------------------------------------------------

def get_or_create_credit_balance(loan):
    balance, created = LoanCreditBalance.objects.get_or_create(
        loan=loan
    )

    return balance


# --------------------------------------------------
# RECORD EXCESS INTEREST AS SEPARATE CREDIT
# --------------------------------------------------


@transaction.atomic
def record_excess_interest_credit(
    *,
    loan_id,
    payment_id,
    owner
):
    loan = Loan.objects.select_for_update().filter(
        id=loan_id,
        shop__owner=owner
    ).first()

    if not loan:
        raise ValidationError("Loan not found or access denied.")

    payment = Payment.objects.select_for_update().filter(
        id=payment_id,
        loan=loan
    ).first()

    if not payment:
        raise ValidationError("Payment not found for this loan.")

    # Prevent duplicate credit for the same payment.
    if LoanCreditTransaction.objects.filter(
        reference_payment=payment,
        transaction_type="CREDIT"
    ).exists():
        raise ValidationError(
            "Credit already recorded for this payment."
        )

    # Get loan credit balance.
    balance, _ = LoanCreditBalance.objects.get_or_create(
        loan=loan
    )

    # Calculate accrued interest.
    from accounts.services.payment_service import (
        get_total_accrued_interest,
    )

    accrued_interest = get_total_accrued_interest(
        loan,
        payment.payment_date
    )

    # Calculate interest paid up to this payment.
    from django.db.models import Sum

    paid_interest = Payment.objects.filter(
        loan=loan,
        payment_date__lte=payment.payment_date,
        created_at__lte=payment.created_at,
        id__lte=payment.id
    ).aggregate(
        total=Sum("interest_amount")
    )["total"] or Decimal("0.00")

    # Calculate cumulative excess.
    cumulative_excess = max(
        accrued_interest.__class__("0.00"),
        paid_interest - accrued_interest
    )

    new_credit = (
        cumulative_excess - balance.total_credit_received
    )

    if new_credit <= Decimal("0.00"):
        return None

    new_credit = money(new_credit)

    # Create immutable credit transaction.
    record = LoanCreditTransaction(
        credit_balance=balance,
        transaction_type="CREDIT",
        amount=new_credit,
        reference_payment=payment,
        created_by=owner,
        notes="Excess interest recorded as separate loan credit."
    )

    record.save()

    # Update credit balance.
    balance.total_credit_received += new_credit
    balance.available_balance += new_credit
    balance.save()

    return record



# --------------------------------------------------
# INTERNAL CREDIT OUTGOING TRANSACTION
# --------------------------------------------------

@transaction.atomic
def _record_credit_outgoing(
    *,
    loan_id,
    owner,
    amount,
    transaction_type,
    adjustment_target="",
    customer_confirmed=False,
    confirmation_method="",
    customer_confirmed_at=None,
    notes=""
):
    amount = money(amount)

    loan = Loan.objects.select_for_update().filter(
        id=loan_id,
        shop__owner=owner
    ).first()

    if not loan:
        raise ValidationError("Loan not found or access denied.")

    balance = LoanCreditBalance.objects.select_for_update().filter(
        loan=loan
    ).first()

    if not balance:
        raise ValidationError("This loan has no credit balance.")

    if amount > balance.available_balance:
        raise ValidationError(
            f"Insufficient credit balance. "
            f"Available balance: {balance.available_balance}"
        )

    if not customer_confirmed:
        raise ValidationError("Customer confirmation is required.")

    if not confirmation_method:
        raise ValidationError("Confirmation method is required.")

    if not confirmation_method in dict(
        LoanCreditTransaction.CONFIRMATION_METHODS
    ):
        raise ValidationError("Invalid confirmation method.")

    if not customer_confirmed_at:
        raise ValidationError(
            "Customer confirmation date and time are required."
        )

    if transaction_type == "ADJUSTMENT":
        if adjustment_target not in dict(
            LoanCreditTransaction.ADJUSTMENT_TARGETS
        ):
            raise ValidationError("Invalid adjustment target.")

        if adjustment_target == "OTHER" and not notes.strip():
            raise ValidationError(
                "A reason is required for other adjustments."
            )

    elif transaction_type == "REFUND":
        adjustment_target = ""

    else:
        raise ValidationError("Invalid credit transaction type.")

    record = LoanCreditTransaction(
        credit_balance=balance,
        transaction_type=transaction_type,
        amount=amount,
        adjustment_target=adjustment_target,
        created_by=owner,
        customer_confirmed=True,
        confirmation_method=confirmation_method,
        customer_confirmed_at=customer_confirmed_at,
        notes=notes
    )

    record.save()

    if transaction_type == "ADJUSTMENT":
        balance.total_credit_adjusted += amount
    else:
        balance.total_refunded += amount

    balance.available_balance -= amount
    balance.save()

    return record


# --------------------------------------------------
# ADJUST CREDIT AGAINST INTEREST / PRINCIPAL / OTHER
# --------------------------------------------------

def adjust_loan_credit(
    *,
    loan_id,
    owner,
    amount,
    adjustment_target,
    customer_confirmed,
    confirmation_method,
    customer_confirmed_at,
    notes=""
):
    return _record_credit_outgoing(
        loan_id=loan_id,
        owner=owner,
        amount=amount,
        transaction_type="ADJUSTMENT",
        adjustment_target=adjustment_target,
        customer_confirmed=customer_confirmed,
        confirmation_method=confirmation_method,
        customer_confirmed_at=customer_confirmed_at,
        notes=notes
    )


# --------------------------------------------------
# REFUND CREDIT TO CUSTOMER
# --------------------------------------------------

def refund_loan_credit(
    *,
    loan_id,
    owner,
    amount,
    customer_confirmed,
    confirmation_method,
    customer_confirmed_at,
    notes=""
):
    return _record_credit_outgoing(
        loan_id=loan_id,
        owner=owner,
        amount=amount,
        transaction_type="REFUND",
        customer_confirmed=customer_confirmed,
        confirmation_method=confirmation_method,
        customer_confirmed_at=customer_confirmed_at,
        notes=notes
    )
