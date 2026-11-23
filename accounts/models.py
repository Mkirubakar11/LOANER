
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q


# --------------------------------------------------
# OWNER PROFILE
# One owner account can manage multiple shops.
# --------------------------------------------------

class OwnerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owner_profile"
    )
    phone_number = models.CharField(max_length=15, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username


# --------------------------------------------------
# SHOP
# Each owner can have multiple shops.
# --------------------------------------------------

class Shop(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shops"
    )
    name = models.CharField(max_length=150)
    shop_code = models.CharField(max_length=30)
    address = models.TextField(blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "shop_code"],
                name="unique_shop_code_per_owner"
            )
        ]

    def __str__(self):
        return self.name


# --------------------------------------------------
# SHOP SETTINGS
# Interest rules are configurable per shop.
# --------------------------------------------------

class ShopSettings(models.Model):
    shop = models.OneToOneField(
        Shop,
        on_delete=models.CASCADE,
        related_name="settings"
    )
    monthly_interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("2.00"),
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    charge_full_month_for_partial = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(monthly_interest_rate__gte=0),
                name="shop_interest_rate_non_negative"
            )
        ]

    def __str__(self):
        return f"{self.shop.name} Settings"


# --------------------------------------------------
# CUSTOMER
# Customer records are separate for each shop.
# Customers do not have login accounts.
# --------------------------------------------------

class Customer(models.Model):
    shop = models.ForeignKey(
        Shop,
        on_delete=models.PROTECT,
        related_name="customers"
    )
    customer_number = models.CharField(max_length=30)
    full_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=15, db_index=True)
    address = models.TextField(blank=True)
    id_proof_type = models.CharField(max_length=50, blank=True)
    id_proof_number = models.CharField(max_length=100, blank=True)
    photo = models.ImageField(
        upload_to="customers/",
        blank=True,
        null=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "customer_number"],
                name="unique_customer_number_per_shop"
            )
        ]
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.customer_number} - {self.full_name}"


# --------------------------------------------------
# LOAN
# One customer can have many loans in the same shop.
# Each loan belongs to exactly one shop and customer.
# --------------------------------------------------

class Loan(models.Model):

    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("CLOSED", "Closed"),
        ("OVERDUE", "Overdue"),
    ]

    shop = models.ForeignKey(
        Shop,
        on_delete=models.PROTECT,
        related_name="loans"
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="loans"
    )
    loan_number = models.CharField(max_length=30)
    principal_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))]
    )
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    loan_date = models.DateField()
    due_date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="ACTIVE",
        db_index=True
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "loan_number"],
                name="unique_loan_number_per_shop"
            ),
            models.CheckConstraint(
                condition=Q(principal_amount__gt=0),
                name="loan_principal_must_be_positive"
            ),
            models.CheckConstraint(
                condition=Q(interest_rate__gte=0),
                name="loan_interest_rate_non_negative"
            ),
            models.CheckConstraint(
                condition=Q(due_date__gte=F("loan_date")),
                name="loan_due_date_valid"
            ),
        ]
        ordering = ["-created_at"]

    def clean(self):
        super().clean()

        errors = {}

        if self.shop_id and self.customer_id:
            if not Customer.objects.filter(
                pk=self.customer_id,
                shop_id=self.shop_id
            ).exists():
                errors["customer"] = (
                    "This customer does not belong to the selected shop."
                )

        if self.loan_date and self.due_date:
            if self.due_date < self.loan_date:
                errors["due_date"] = (
                    "Due date cannot be before loan date."
                )

        if self.principal_amount is not None:
            if self.principal_amount <= 0:
                errors["principal_amount"] = (
                    "Principal amount must be greater than zero."
                )

        if self.interest_rate is not None:
            if self.interest_rate < 0:
                errors["interest_rate"] = (
                    "Interest rate cannot be negative."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.loan_number} - {self.customer.full_name}"


# --------------------------------------------------
# GOLD ITEMS
# One loan can contain any number of gold items.
# --------------------------------------------------

class GoldItem(models.Model):
    loan = models.ForeignKey(
        Loan,
        on_delete=models.PROTECT,
        related_name="gold_items"
    )
    item_type = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    gross_weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))]
    )
    net_weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))]
    )
    purity = models.CharField(max_length=20, blank=True)
    item_photo = models.ImageField(
        upload_to="gold_items/",
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(gross_weight__gt=0),
                name="gold_gross_weight_positive"
            ),
            models.CheckConstraint(
                condition=Q(net_weight__gt=0),
                name="gold_net_weight_positive"
            ),
            models.CheckConstraint(
                condition=Q(net_weight__lte=F("gross_weight")),
                name="gold_net_weight_not_above_gross"
            ),
        ]

    def clean(self):
        super().clean()

        if (
            self.gross_weight is not None
            and self.net_weight is not None
        ):
            if self.net_weight > self.gross_weight:
                raise ValidationError({
                    "net_weight": (
                        "Net weight cannot exceed gross weight."
                    )
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_type} - {self.loan.loan_number}"


# --------------------------------------------------
# PAYMENTS
# Each payment belongs to one specific loan.
# Interest and principal portions are recorded separately.
# --------------------------------------------------

class Payment(models.Model):

    PAYMENT_TYPES = [
        ("INTEREST", "Interest"),
        ("PRINCIPAL", "Principal"),
        ("BOTH", "Interest and Principal"),
    ]

    shop = models.ForeignKey(
        Shop,
        on_delete=models.PROTECT,
        related_name="payments"
    )
    loan = models.ForeignKey(
        Loan,
        on_delete=models.PROTECT,
        related_name="payments"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))]
    )
    interest_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )
    principal_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )
    payment_type = models.CharField(
        max_length=10,
        choices=PAYMENT_TYPES
    )
    payment_date = models.DateField()
    receipt_number = models.CharField(max_length=30)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "receipt_number"],
                name="unique_receipt_number_per_shop"
            ),
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="payment_amount_positive"
            ),
            models.CheckConstraint(
                condition=Q(interest_amount__gte=0),
                name="payment_interest_non_negative"
            ),
            models.CheckConstraint(
                condition=Q(principal_amount__gte=0),
                name="payment_principal_non_negative"
            ),
            models.CheckConstraint(
                condition=Q(
                    amount=F("interest_amount") + F("principal_amount")
                ),
                name="payment_amount_matches_allocation"
            ),
        ]
        ordering = ["-payment_date", "-created_at"]

    def clean(self):
        super().clean()

        errors = {}

        if self.loan_id and self.shop_id:
            if self.loan.shop_id != self.shop_id:
                errors["shop"] = (
                    "The selected shop does not match this loan."
                )

        if self.loan_id and self.payment_date:
            if self.payment_date < self.loan.loan_date:
                errors["payment_date"] = (
                    "Payment date cannot be before the loan date."
                )

        if self.amount is not None:
            if self.amount <= 0:
                errors["amount"] = (
                    "Payment amount must be greater than zero."
                )

        if (
            self.amount is not None
            and self.interest_amount is not None
            and self.principal_amount is not None
        ):
            if self.amount != (
                self.interest_amount + self.principal_amount
            ):
                errors["amount"] = (
                    "Total amount must equal interest plus principal."
                )

        if self.payment_type == "INTEREST":
            if (
                self.interest_amount != self.amount
                or self.principal_amount != Decimal("0.00")
            ):
                errors["payment_type"] = (
                    "Interest payment must be allocated entirely to interest."
                )

        elif self.payment_type == "PRINCIPAL":
            if (
                self.principal_amount != self.amount
                or self.interest_amount != Decimal("0.00")
            ):
                errors["payment_type"] = (
                    "Principal payment must be allocated entirely to principal."
                )

        elif self.payment_type == "BOTH":
            if (
                self.interest_amount <= 0
                or self.principal_amount <= 0
            ):
                errors["payment_type"] = (
                    "Both interest and principal amounts must be greater than zero."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.receipt_number} - Rs. {self.amount}"


# --------------------------------------------------
# LOAN PHOTOS
# Pledge and release verification photos.
# Photos belong to a specific loan.
# --------------------------------------------------

class LoanPhoto(models.Model):

    PHOTO_TYPES = [
        ("CUSTOMER_PLEDGE", "Customer at Pledge"),
        ("JEWELLERY_PLEDGE", "Jewellery at Pledge"),
        ("CUSTOMER_RELEASE", "Customer at Release"),
        ("JEWELLERY_RELEASE", "Jewellery at Release"),
    ]

    loan = models.ForeignKey(
        Loan,
        on_delete=models.PROTECT,
        related_name="photos"
    )
    photo_type = models.CharField(
        max_length=30,
        choices=PHOTO_TYPES
    )
    image = models.ImageField(upload_to="loan_photos/")
    captured_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="captured_loan_photos"
    )
    captured_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-captured_at"]

    def __str__(self):
        return f"{self.loan.loan_number} - {self.photo_type}"


# --------------------------------------------------
# LOAN CREDIT BALANCE
# Each loan maintains its own separate credit balance.
# --------------------------------------------------

class LoanCreditBalance(models.Model):

    loan = models.OneToOneField(
        Loan,
        on_delete=models.PROTECT,
        related_name="credit_balance"
    )

    total_credit_received = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    total_credit_adjusted = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    total_refunded = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    available_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(total_credit_received__gte=0),
                name="credit_received_non_negative"
            ),
            models.CheckConstraint(
                condition=Q(total_credit_adjusted__gte=0),
                name="credit_adjusted_non_negative"
            ),
            models.CheckConstraint(
                condition=Q(total_refunded__gte=0),
                name="credit_refunded_non_negative"
            ),
            models.CheckConstraint(
                condition=Q(available_balance__gte=0),
                name="credit_balance_non_negative"
            ),
            models.CheckConstraint(
                condition=Q(
                    available_balance=(
                        F("total_credit_received")
                        - F("total_credit_adjusted")
                        - F("total_refunded")
                    )
                ),
                name="credit_balance_matches_transactions"
            ),
        ]

    def __str__(self):
        return f"{self.loan.loan_number} - Credit Balance"


# --------------------------------------------------
# LOAN CREDIT TRANSACTIONS
# Every credit, adjustment and refund is audited.
# Transactions cannot be edited or deleted.
# --------------------------------------------------

class LoanCreditTransaction(models.Model):

    TRANSACTION_TYPES = [
        ("CREDIT", "Credit Received"),
        ("ADJUSTMENT", "Credit Adjustment"),
        ("REFUND", "Refund"),
    ]

    ADJUSTMENT_TARGETS = [
        ("INTEREST", "Interest"),
        ("PRINCIPAL", "Principal"),
        ("OTHER", "Other"),
    ]

    CONFIRMATION_METHODS = [
        ("IN_PERSON", "In Person"),
        ("PHONE", "Phone"),
        ("WHATSAPP", "WhatsApp"),
        ("SMS", "SMS"),
        ("WRITTEN", "Written"),
    ]

    credit_balance = models.ForeignKey(
        LoanCreditBalance,
        on_delete=models.PROTECT,
        related_name="transactions"
    )

    transaction_type = models.CharField(
        max_length=15,
        choices=TRANSACTION_TYPES
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))]
    )

    adjustment_target = models.CharField(
        max_length=15,
        choices=ADJUSTMENT_TARGETS,
        blank=True
    )

    reference_payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="credit_transactions"
    )

    # Customer confirmation details
    customer_confirmed = models.BooleanField(default=False)

    confirmation_method = models.CharField(
        max_length=15,
        choices=CONFIRMATION_METHODS,
        blank=True
    )

    customer_confirmed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # User who recorded this transaction
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="loan_credit_transactions"
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="loan_credit_transaction_amount_positive"
            ),
        ]

    def clean(self):
        super().clean()

        errors = {}

        # Payment must belong to the same loan.
        if self.reference_payment_id and self.credit_balance_id:
            if (
                self.reference_payment.loan_id
                != self.credit_balance.loan_id
            ):
                errors["reference_payment"] = (
                    "Payment must belong to the same loan."
                )

        # CREDIT must reference its original payment.
        if self.transaction_type == "CREDIT":
            if not self.reference_payment_id:
                errors["reference_payment"] = (
                    "Credit transaction must reference its payment."
                )

            if self.adjustment_target:
                errors["adjustment_target"] = (
                    "Credit transactions cannot have an adjustment target."
                )

        # ADJUSTMENT validation.
        if self.transaction_type == "ADJUSTMENT":

            if not self.adjustment_target:
                errors["adjustment_target"] = (
                    "Adjustment target is required."
                )

            if not self.customer_confirmed:
                errors["customer_confirmed"] = (
                    "Customer confirmation is required."
                )

            if not self.confirmation_method:
                errors["confirmation_method"] = (
                    "Confirmation method is required."
                )

            if not self.customer_confirmed_at:
                errors["customer_confirmed_at"] = (
                    "Customer confirmation date and time are required."
                )

            if (
                self.adjustment_target == "OTHER"
                and not self.notes.strip()
            ):
                errors["notes"] = (
                    "A reason is required for other adjustments."
                )

        # REFUND validation.
        if self.transaction_type == "REFUND":

            if self.adjustment_target:
                errors["adjustment_target"] = (
                    "Refund transactions cannot have an adjustment target."
                )

            if not self.customer_confirmed:
                errors["customer_confirmed"] = (
                    "Customer confirmation is required."
                )

            if not self.confirmation_method:
                errors["confirmation_method"] = (
                    "Confirmation method is required."
                )

            if not self.customer_confirmed_at:
                errors["customer_confirmed_at"] = (
                    "Customer confirmation date and time are required."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # Financial transaction records are immutable.
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError(
                "Credit transactions cannot be edited. "
                "Create a new transaction to correct the record."
            )

        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            "Credit transactions cannot be deleted. "
            "Use a reversal transaction when correction is necessary."
        )

    def __str__(self):
        return (
            f"{self.transaction_type} - "
            f"{self.amount} - "
            f"{self.credit_balance.loan.loan_number}"
        )
