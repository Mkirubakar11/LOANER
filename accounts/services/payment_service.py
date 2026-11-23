
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from django.db.models import Sum

from accounts.models import (Payment, Loan, LoanCreditTransaction,)
from accounts.services.interest_service import calculate_interest


# --------------------------------------------------
# DATE NORMALIZATION
# --------------------------------------------------

def to_date(value):
    """Convert datetime to date; leave date values unchanged."""
    if isinstance(value, datetime):
        return value.date()
    return value


# --------------------------------------------------
# MONEY ROUNDING
# --------------------------------------------------

def round_money(amount):
    return Decimal(str(amount)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


# --------------------------------------------------
# GET OUTSTANDING PRINCIPAL
# --------------------------------------------------


def get_outstanding_principal(loan, as_of_date=None):

    payments = Payment.objects.filter(loan=loan)

    adjustments = LoanCreditTransaction.objects.filter(
        credit_balance__loan=loan,
        transaction_type="ADJUSTMENT",
        adjustment_target="PRINCIPAL",
        customer_confirmed=True,
    )

    if as_of_date is not None:
        calculation_day = to_date(as_of_date)

        payments = payments.filter(
            payment_date__lte=calculation_day
        )

        adjustments = adjustments.filter(
            customer_confirmed_at__date__lte=calculation_day
        )

    payment_result = payments.aggregate(
        total_paid=Sum("principal_amount")
    )

    adjustment_result = adjustments.aggregate(
        total_adjusted=Sum("amount")
    )

    total_paid = (
        payment_result["total_paid"] or Decimal("0.00")
    )

    total_adjusted = (
        adjustment_result["total_adjusted"] or Decimal("0.00")
    )

    outstanding = (
        loan.principal_amount
        - total_paid
        - total_adjusted
    )

    return round_money(
        max(outstanding, Decimal("0.00"))
    )

# --------------------------------------------------
# GET TOTAL ACCRUED INTEREST
# --------------------------------------------------


def get_total_accrued_interest(loan, as_of_date):

    calculation_day = to_date(as_of_date)

    if calculation_day < loan.loan_date:
        raise ValueError(
            "Calculation date cannot be before the loan date."
        )

    current_principal = loan.principal_amount
    period_start = loan.loan_date
    total_interest = Decimal("0.00")

    # Normal principal payments.
    principal_payments = Payment.objects.filter(
        loan=loan,
        payment_date__lte=calculation_day,
        principal_amount__gt=0
    ).order_by(
        "payment_date",
        "created_at",
        "id"
    )

    # Customer-confirmed principal credit adjustments.
    principal_adjustments = LoanCreditTransaction.objects.filter(
        credit_balance__loan=loan,
        transaction_type="ADJUSTMENT",
        adjustment_target="PRINCIPAL",
        customer_confirmed=True,
        customer_confirmed_at__date__lte=calculation_day,
    ).order_by(
        "customer_confirmed_at",
        "id"
    )

    # Combine both types of principal reductions by date.
    principal_reductions = {}

    for payment in principal_payments:

        payment_day = to_date(payment.payment_date)

        principal_reductions.setdefault(
            payment_day,
            Decimal("0.00")
        )

        principal_reductions[payment_day] += (
            payment.principal_amount
        )

    for adjustment in principal_adjustments:

        adjustment_day = to_date(
            adjustment.customer_confirmed_at
        )

        principal_reductions.setdefault(
            adjustment_day,
            Decimal("0.00")
        )

        principal_reductions[adjustment_day] += (
            adjustment.amount
        )

    # Process reductions chronologically.
    for reduction_day in sorted(principal_reductions):

        principal_paid = principal_reductions[reduction_day]

        interest = calculate_interest(
            principal_amount=current_principal,
            monthly_interest_rate=loan.interest_rate,
            start_date=period_start,
            end_date=reduction_day
        )

        total_interest += interest

        current_principal -= principal_paid

        if current_principal < 0:
            raise ValueError(
                "Principal reductions exceed the loan balance."
            )

        period_start = reduction_day

    # Calculate interest on the remaining principal.
    remaining_interest = calculate_interest(
        principal_amount=current_principal,
        monthly_interest_rate=loan.interest_rate,
        start_date=period_start,
        end_date=calculation_day
    )

    total_interest += remaining_interest

    return round_money(total_interest)


# --------------------------------------------------
# GET INTEREST BALANCES
# --------------------------------------------------

def get_interest_balances(loan, as_of_date):

    calculation_day = to_date(as_of_date)

    accrued_interest = get_total_accrued_interest(
        loan,
        calculation_day
    )

    result = Payment.objects.filter(
        loan=loan,
        payment_date__lte=calculation_day
    ).aggregate(
        total_paid=Sum("interest_amount")
    )

    paid_interest = result["total_paid"] or Decimal("0.00")

    # Get customer-confirmed interest adjustments.
    adjustment_result = LoanCreditTransaction.objects.filter(
        credit_balance__loan=loan,
        transaction_type="ADJUSTMENT",
        adjustment_target="INTEREST",
        customer_confirmed=True,
        customer_confirmed_at__date__lte=calculation_day,
    ).aggregate(
        total_adjusted=Sum("amount")
    )

    adjusted_interest = (
        adjustment_result["total_adjusted"]
        or Decimal("0.00")
    )

    # Subtract actual interest payments and confirmed adjustments.
    difference = (
        accrued_interest
        - paid_interest
        - adjusted_interest
    )

    outstanding_interest = max(
        difference,
        Decimal("0.00")
    )

    # Held credit is not automatically used.
    advance_credit = max(
        paid_interest - accrued_interest,
        Decimal("0.00")
    )

    return {
        "accrued_interest": round_money(accrued_interest),
        "paid_interest": round_money(paid_interest),
        "adjusted_interest": round_money(adjusted_interest),
        "outstanding_interest": round_money(outstanding_interest),
        "advance_interest_credit": round_money(advance_credit),
    }

# --------------------------------------------------
# GET OUTSTANDING INTEREST
# --------------------------------------------------

def get_outstanding_interest(loan, as_of_date):

    balances = get_interest_balances(loan, as_of_date)

    return balances["outstanding_interest"]


# --------------------------------------------------
# GET ADVANCE INTEREST CREDIT
# --------------------------------------------------

def get_advance_interest_credit(loan, as_of_date):

    balances = get_interest_balances(loan, as_of_date)

    return balances["advance_interest_credit"]


# --------------------------------------------------
# GET LOAN SETTLEMENT SUMMARY
# --------------------------------------------------

def get_loan_settlement_summary(loan, as_of_date):

    outstanding_principal = get_outstanding_principal(
        loan,
        as_of_date
    )

    interest_balances = get_interest_balances(
        loan,
        as_of_date
    )

    outstanding_interest = interest_balances[
        "outstanding_interest"
    ]

    advance_credit = interest_balances[
        "advance_interest_credit"
    ]

    settlement_amount = round_money(
        outstanding_principal + outstanding_interest
    )

    return {
        "loan_id": loan.id,
        "loan_number": loan.loan_number,
        "calculation_date": as_of_date,
        "outstanding_principal": outstanding_principal,
        "accrued_interest": interest_balances["accrued_interest"],
        "paid_interest": interest_balances["paid_interest"],
        "outstanding_interest": outstanding_interest,
        "advance_interest_credit": advance_credit,
        "settlement_amount": settlement_amount,
        "can_close": (
            outstanding_principal == Decimal("0.00")
            and outstanding_interest == Decimal("0.00")
        ),
    }


# --------------------------------------------------
# RECORD PAYMENT
# --------------------------------------------------

@transaction.atomic
def record_payment(
    *,
    loan_id,
    owner,
    amount,
    interest_amount,
    principal_amount,
    payment_type,
    payment_date,
    receipt_number,
    notes=""
):

    # Lock loan for concurrent payment safety
    try:
        loan = Loan.objects.select_for_update().get(
            id=loan_id,
            shop__owner=owner
        )

    except Loan.DoesNotExist:
        raise ValidationError(
            "Loan not found or access denied."
        )

    # Closed loans cannot receive payments
    if loan.status == "CLOSED":
        raise ValidationError(
            "Cannot record payment for a closed loan."
        )

    # Convert monetary values safely
    try:
        amount = Decimal(str(amount))
        interest_amount = Decimal(str(interest_amount))
        principal_amount = Decimal(str(principal_amount))

    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError(
            "Invalid payment amount."
        )

    # Validate finite monetary values
    if not all(value.is_finite() for value in (
        amount,
        interest_amount,
        principal_amount
    )):
        raise ValidationError(
            "Payment amounts must be finite numbers."
        )

    # Require two-decimal monetary precision
    if any(
        value != round_money(value)
        for value in (amount, interest_amount, principal_amount)
    ):
        raise ValidationError(
            "Payment amounts can have a maximum of two decimal places."
        )

    # Normalize payment date for loan-date comparison
    payment_day = to_date(payment_date)

    # Validate payment date
    if payment_day < loan.loan_date:
        raise ValidationError(
            "Payment date cannot be before the loan date."
        )

    # Prevent backdated payments
    latest_payment = Payment.objects.filter(
        loan=loan
    ).order_by(
        "-payment_date",
        "-created_at",
        "-id"
    ).first()

    if latest_payment:
        latest_payment_day = to_date(latest_payment.payment_date)

        if payment_day < latest_payment_day:
            raise ValidationError(
                "Backdated payments are not allowed. "
                "Payment date must be on or after the latest payment date."
            )

    # Validate payment amount
    if amount <= 0:
        raise ValidationError(
            "Payment amount must be greater than zero."
        )

    if interest_amount < 0 or principal_amount < 0:
        raise ValidationError(
            "Payment allocations cannot be negative."
        )

    # Total must match allocations
    if amount != interest_amount + principal_amount:
        raise ValidationError(
            "Total payment must equal interest plus principal."
        )

    # Validate payment type
    if payment_type == "INTEREST":

        if interest_amount != amount or principal_amount != 0:
            raise ValidationError(
                "Invalid interest payment allocation."
            )

    elif payment_type == "PRINCIPAL":

        if principal_amount != amount or interest_amount != 0:
            raise ValidationError(
                "Invalid principal payment allocation."
            )

    elif payment_type == "BOTH":

        if interest_amount <= 0 or principal_amount <= 0:
            raise ValidationError(
                "Both interest and principal must be greater than zero."
            )

    else:
        raise ValidationError(
            "Invalid payment type."
        )

    # Check outstanding principal
    outstanding_principal = get_outstanding_principal(
        loan,
        payment_date
    )

    if principal_amount > outstanding_principal:
        raise ValidationError(
            f"Principal payment exceeds outstanding principal "
            f"of {outstanding_principal}."
        )

    # Validate receipt number
    receipt_number = str(receipt_number or "").strip()

    if not receipt_number:
        raise ValidationError(
            "Receipt number is required."
        )

    if Payment.objects.filter(
        shop=loan.shop,
        receipt_number=receipt_number
    ).exists():
        raise ValidationError(
            "This receipt number already exists."
        )

    # Create payment record
    try:
        payment = Payment.objects.create(
            shop=loan.shop,
            loan=loan,
            amount=amount,
            interest_amount=interest_amount,
            principal_amount=principal_amount,
            payment_type=payment_type,
            payment_date=payment_date,
            receipt_number=receipt_number,
            notes=notes
        )

    except IntegrityError:
        raise ValidationError(
            "Payment could not be saved. "
            "Check the receipt number and payment details."
        )
    
    # Record excess interest as separate customer credit.
    from accounts.services.credit_service import (
        record_excess_interest_credit,
    )

    record_excess_interest_credit(
        loan_id=loan.id,
        payment_id=payment.id,
        owner=owner,
    )
    
    # Recalculate balances after saving payment
    settlement = get_loan_settlement_summary(
        loan,
        payment_date
    )

    # Close only when both balances are zero
    if settlement["can_close"]:

        loan.status = "CLOSED"

        loan.save(
            update_fields=["status", "updated_at"]
        )

    return payment
