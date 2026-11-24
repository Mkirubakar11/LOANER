
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from rest_framework import serializers

from .models import (
    OwnerProfile,
    Shop,
    ShopSettings,
    Customer,
    Loan,
    GoldItem,
    Payment,
    LoanCreditBalance,
    LoanCreditTransaction,
)

User = get_user_model()


# ==========================================
# OWNER REGISTRATION
# ==========================================

class OwnerRegistrationSerializer(serializers.Serializer):

    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        trim_whitespace=False
    )

    phone_number = serializers.CharField(
        max_length=15,
        required=False,
        allow_blank=True
    )

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(
                "This username is already registered."
            )
        return value

    def validate_email(self, value):
        value = value.strip().lower()

        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "This email is already registered."
            )
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    @transaction.atomic
    def create(self, validated_data):

        phone_number = validated_data.pop(
            "phone_number", ""
        )

        owner = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"]
        )

        OwnerProfile.objects.create(
            user=owner,
            phone_number=phone_number
        )

        return owner


# ==========================================
# SHOP MANAGEMENT SERIALIZER
# ==========================================

class ShopSerializer(serializers.ModelSerializer):

    class Meta:
        model = Shop

        fields = [
            "id",
            "name",
            "shop_code",
            "address",
            "phone_number",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "shop_code",
            "is_active",
            "created_at",
            "updated_at",
        ]


# ==========================================
# SHOP SETTINGS SERIALIZER
# ==========================================

class ShopSettingsSerializer(serializers.ModelSerializer):

    class Meta:
        model = ShopSettings

        fields = [
            "id",
            "shop",
            "monthly_interest_rate",
            "charge_full_month_for_partial",
        ]

        read_only_fields = [
            "id",
            "shop",
        ]


# ==========================================
# CUSTOMER MANAGEMENT SERIALIZER
# ==========================================

class CustomerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Customer

        fields = [
            "id",
            "shop",
            "customer_number",
            "full_name",
            "phone_number",
            "address",
            "id_proof_type",
            "id_proof_number",
            "photo",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "shop",
            "customer_number",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def validate_full_name(self, value):

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Customer name cannot be empty."
            )

        return value


# ==========================================
# CUSTOMER STATUS SERIALIZER
# ==========================================

class CustomerStatusSerializer(serializers.ModelSerializer):

    class Meta:
        model = Customer

        fields = ["id", "is_active"]

        read_only_fields = ["id"]


# ==========================================
# LOAN MANAGEMENT SERIALIZER
# ==========================================

class LoanSerializer(serializers.ModelSerializer):

    class Meta:
        model = Loan

        fields = [
            "id",
            "shop",
            "customer",
            "loan_number",
            "principal_amount",
            "interest_rate",
            "loan_date",
            "due_date",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "shop",
            "loan_number",
            "interest_rate",
            "status",
            "created_at",
            "updated_at",
        ]

    def validate_principal_amount(self, value):

        if value <= 0:
            raise serializers.ValidationError(
                "Principal amount must be greater than zero."
            )

        return value

    def validate_interest_rate(self, value):

        if value < 0:
            raise serializers.ValidationError(
                "Interest rate cannot be negative."
            )

        return value

    def validate(self, attrs):

        loan_date = attrs.get(
            "loan_date",
            getattr(self.instance, "loan_date", None)
        )

        due_date = attrs.get(
            "due_date",
            getattr(self.instance, "due_date", None)
        )

        if loan_date and due_date and due_date < loan_date:
            raise serializers.ValidationError({
                "due_date": "Due date cannot be before loan date."
            })

        return attrs


# ==========================================
# LOAN STATUS SERIALIZER
# ==========================================

class LoanStatusSerializer(serializers.ModelSerializer):

    class Meta:
        model = Loan

        fields = ["id", "status"]

        read_only_fields = ["id"]

    def validate_status(self, value):

        if value == "CLOSED":
            raise serializers.ValidationError(
                "A loan can only be closed after full payment settlement."
            )

        return value


# ==========================================
# GOLD ITEM MANAGEMENT SERIALIZER
# ==========================================

class GoldItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = GoldItem

        fields = [
            "id",
            "loan",
            "item_type",
            "description",
            "gross_weight",
            "net_weight",
            "purity",
            "item_photo",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "loan",
            "created_at",
        ]

    def validate(self, attrs):

        gross_weight = attrs.get(
            "gross_weight",
            getattr(self.instance, "gross_weight", None)
        )

        net_weight = attrs.get(
            "net_weight",
            getattr(self.instance, "net_weight", None)
        )

        if (
            gross_weight is not None
            and net_weight is not None
            and net_weight > gross_weight
        ):
            raise serializers.ValidationError({
                "net_weight": "Net weight cannot exceed gross weight."
            })

        return attrs


# ==========================================
# PAYMENT MANAGEMENT SERIALIZER
# ==========================================

class PaymentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Payment

        fields = [
            "id",
            "shop",
            "loan",
            "amount",
            "interest_amount",
            "principal_amount",
            "payment_type",
            "payment_date",
            "receipt_number",
            "notes",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "shop",
            "loan",
            "created_at",
        ]

    def validate_amount(self, value):

        if value <= 0:
            raise serializers.ValidationError(
                "Payment amount must be greater than zero."
            )

        return value

    def validate_interest_amount(self, value):

        if value < 0:
            raise serializers.ValidationError(
                "Interest amount cannot be negative."
            )

        return value

    def validate_principal_amount(self, value):

        if value < 0:
            raise serializers.ValidationError(
                "Principal amount cannot be negative."
            )

        return value

    def validate(self, attrs):

        amount = attrs.get("amount")
        interest = attrs.get("interest_amount")
        principal = attrs.get("principal_amount")
        payment_type = attrs.get("payment_type")

        if (
            amount is not None
            and interest is not None
            and principal is not None
            and amount != interest + principal
        ):
            raise serializers.ValidationError({
                "amount": (
                    "Total payment must equal interest "
                    "plus principal."
                )
            })

        if payment_type == "INTEREST":
            if interest != amount or principal != 0:
                raise serializers.ValidationError({
                    "payment_type": "Invalid interest allocation."
                })

        elif payment_type == "PRINCIPAL":
            if principal != amount or interest != 0:
                raise serializers.ValidationError({
                    "payment_type": "Invalid principal allocation."
                })

        elif payment_type == "BOTH":
            if interest <= 0 or principal <= 0:
                raise serializers.ValidationError({
                    "payment_type": (
                        "Both interest and principal "
                        "must be greater than zero."
                    )
                })

        return attrs


# ==========================================
# LOAN CREDIT BALANCE
# ==========================================

class CreditBalanceSerializer(serializers.ModelSerializer):

    class Meta:
        model = LoanCreditBalance

        fields = [
            "id",
            "loan",
            "total_credit_received",
            "total_credit_adjusted",
            "total_refunded",
            "available_balance",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


# ==========================================
# LOAN CREDIT TRANSACTION HISTORY
# ==========================================

class CreditTransactionSerializer(serializers.ModelSerializer):

    class Meta:
        model = LoanCreditTransaction

        fields = [
            "id",
            "transaction_type",
            "amount",
            "adjustment_target",
            "reference_payment",
            "customer_confirmed",
            "confirmation_method",
            "customer_confirmed_at",
            "created_by",
            "notes",
            "created_at",
        ]

        read_only_fields = fields


# ==========================================
# CREDIT ADJUSTMENT REQUEST
# ==========================================

class CreditAdjustmentSerializer(serializers.Serializer):

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01")
    )

    adjustment_target = serializers.ChoiceField(
        choices=LoanCreditTransaction.ADJUSTMENT_TARGETS
    )

    customer_confirmed = serializers.BooleanField()

    confirmation_method = serializers.ChoiceField(
        choices=LoanCreditTransaction.CONFIRMATION_METHODS
    )

    customer_confirmed_at = serializers.DateTimeField()

    notes = serializers.CharField(
        required=False,
        allow_blank=True
    )

    def validate(self, attrs):

        if not attrs["customer_confirmed"]:
            raise serializers.ValidationError({
                "customer_confirmed": (
                    "Customer confirmation is required."
                )
            })

        if (
            attrs["adjustment_target"] == "OTHER"
            and not attrs.get("notes", "").strip()
        ):
            raise serializers.ValidationError({
                "notes": "A reason is required for other adjustments."
            })

        return attrs


# ==========================================
# CREDIT REFUND REQUEST
# ==========================================

class CreditRefundSerializer(serializers.Serializer):

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01")
    )

    customer_confirmed = serializers.BooleanField()

    confirmation_method = serializers.ChoiceField(
        choices=LoanCreditTransaction.CONFIRMATION_METHODS
    )

    customer_confirmed_at = serializers.DateTimeField()

    notes = serializers.CharField(
        required=False,
        allow_blank=True
    )

    def validate_customer_confirmed(self, value):

        if not value:
            raise serializers.ValidationError(
                "Customer confirmation is required."
            )

        return value
