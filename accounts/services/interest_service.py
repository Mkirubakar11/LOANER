
from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


# --------------------------------------------------
# ADD MONTHS TO A DATE
# Example: January 31 + 1 month = February 28/29
# --------------------------------------------------

def add_months(start_date, months):

    # Calculate target year and month
    month_index = start_date.month - 1 + months
    year = start_date.year + month_index // 12
    month = month_index % 12 + 1

    # Handle months with different number of days
    last_day = monthrange(year, month)[1]
    day = min(start_date.day, last_day)

    return date(year, month, day)


# --------------------------------------------------
# CALCULATE LOAN INTEREST
# Rule:
# Monthly interest + proportional interest for extra days
# One month = 30 days for extra-day calculation
# --------------------------------------------------

def calculate_interest(
    principal_amount,
    monthly_interest_rate,
    start_date,
    end_date
):

    # Convert values safely into Decimal
    principal = Decimal(str(principal_amount))
    rate = Decimal(str(monthly_interest_rate))

    # Validate inputs
    if principal < 0:
        raise ValueError("Principal amount cannot be negative.")

    if rate < 0:
        raise ValueError("Interest rate cannot be negative.")

    if end_date < start_date:
        raise ValueError("End date cannot be before start date.")

    # Calculate completed calendar months
    completed_months = 0

    while add_months(start_date, completed_months + 1) <= end_date:
        completed_months += 1

    # Find the date after completed months
    last_month_date = add_months(start_date, completed_months)

    # Calculate remaining days
    remaining_days = Decimal((end_date - last_month_date).days)

    # Calculate interest for completed months
    monthly_interest = (
        principal * rate / Decimal("100")
    )

    full_month_interest = monthly_interest * completed_months

    # Calculate interest for remaining days using 30-day method
    extra_days_interest = (
        monthly_interest * remaining_days / Decimal("30")
    )

    # Calculate total interest
    total_interest = full_month_interest + extra_days_interest

    # Round to 2 decimal places
    return total_interest.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )
