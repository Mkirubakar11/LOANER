
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework import status

from .models import (
    Shop,
    ShopSettings,
    Customer,
    Loan,
    GoldItem,
    Payment,
    LoanCreditBalance,
    LoanCreditTransaction,
)

from .serializers import (
    OwnerRegistrationSerializer,
    ShopSerializer,
    ShopSettingsSerializer,
    CustomerSerializer,
    CustomerStatusSerializer,
    LoanSerializer,
    LoanStatusSerializer,
    GoldItemSerializer,
    PaymentSerializer,
    CreditBalanceSerializer,
    CreditTransactionSerializer,
    CreditAdjustmentSerializer,
    CreditRefundSerializer,
)

from .services.receipt_service import generate_payment_receipt

from .services.payment_service import (
    record_payment,
    get_loan_settlement_summary,
)

from .services.credit_service import (
    get_or_create_credit_balance,
    adjust_loan_credit,
    refund_loan_credit,
)

# ==========================================
# OWNER REGISTRATION
# ==========================================

class OwnerRegistrationView(generics.CreateAPIView):

    serializer_class = OwnerRegistrationSerializer
    permission_classes = [AllowAny]


# ==========================================
# SHOP MANAGEMENT
# ==========================================

class ShopListCreateView(generics.ListCreateAPIView):

    serializer_class = ShopSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        return Shop.objects.filter(
            owner=self.request.user
        ).order_by("-created_at")

    def perform_create(self, serializer):

        serializer.save(owner=self.request.user)


# ==========================================
# SHOP SETTINGS MANAGEMENT
# ==========================================

class ShopSettingsView(generics.RetrieveUpdateAPIView):

    serializer_class = ShopSettingsSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):

        shop = get_object_or_404(
            Shop,
            id=self.kwargs["shop_id"],
            owner=self.request.user
        )

        settings, created = ShopSettings.objects.get_or_create(
            shop=shop
        )

        return settings


# ==========================================
# CUSTOMER MANAGEMENT
# ==========================================


# ==========================================
# CUSTOMER LIST & CREATE
# ==========================================

class CustomerListCreateView(generics.ListCreateAPIView):

    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def get_shop(self):

        return get_object_or_404(
            Shop,
            id=self.kwargs["shop_id"],
            owner=self.request.user
        )

    def get_queryset(self):

        return Customer.objects.filter(
            shop=self.get_shop()
        ).order_by("full_name")

    def perform_create(self, serializer):

        serializer.save(
            shop=self.get_shop()
        )



# ==========================================
# CUSTOMER DETAIL & UPDATE
# ==========================================

class CustomerDetailView(generics.RetrieveUpdateAPIView):

    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        return Customer.objects.filter(
            shop__owner=self.request.user,
            shop_id=self.kwargs["shop_id"]
        )

# ==========================================
# CUSTOMER ACTIVATE / DEACTIVATE
# ==========================================


class CustomerStatusView(generics.UpdateAPIView):

    serializer_class = CustomerStatusSerializer
    permission_classes = [IsAuthenticated]

    http_method_names = ["patch", "options"]

    def get_queryset(self):

        return Customer.objects.filter(
            shop__owner=self.request.user,
            shop_id=self.kwargs["shop_id"]
        )



# ==========================================
# LOAN MANAGEMENT
# ==========================================

class LoanListCreateView(generics.ListCreateAPIView):

    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated]

    def get_shop(self):

        return get_object_or_404(
            Shop,
            id=self.kwargs["shop_id"],
            owner=self.request.user,
            is_active=True
        )

    def get_queryset(self):

        return Loan.objects.filter(
            shop=self.get_shop()
        ).select_related(
            "customer",
            "shop"
        ).order_by("-created_at")

    def perform_create(self, serializer):

        shop = self.get_shop()

        customer = serializer.validated_data["customer"]

        if customer.shop_id != shop.id:
            from rest_framework.exceptions import ValidationError

            raise ValidationError(
                "Customer does not belong to this shop."
            )

        serializer.save(
            shop=shop,
            interest_rate=shop.settings.monthly_interest_rate
        )


# ==========================================
# LOAN DETAIL & UPDATE
# ==========================================

class LoanDetailView(generics.RetrieveUpdateAPIView):

    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        return Loan.objects.filter(
            shop__owner=self.request.user,
            shop_id=self.kwargs["shop_id"]
        ).select_related(
            "customer",
            "shop"
        )


# ==========================================
# LOAN STATUS MANAGEMENT
# ==========================================

class LoanStatusView(generics.UpdateAPIView):

    serializer_class = LoanStatusSerializer
    permission_classes = [IsAuthenticated]

    http_method_names = ["patch", "options"]

    def get_queryset(self):

        return Loan.objects.filter(
            shop__owner=self.request.user,
            shop_id=self.kwargs["shop_id"]
        ).select_related("customer", "shop")


# ==========================================
# GOLD ITEM MANAGEMENT
# ==========================================

class GoldItemListCreateView(generics.ListCreateAPIView):

    serializer_class = GoldItemSerializer
    permission_classes = [IsAuthenticated]

    def get_loan(self):

        return get_object_or_404(
            Loan,
            id=self.kwargs["loan_id"],
            shop__owner=self.request.user,
            shop_id=self.kwargs["shop_id"]
        )

    def get_queryset(self):

        return GoldItem.objects.filter(
            loan=self.get_loan()
        ).order_by("-created_at")

    def perform_create(self, serializer):

        serializer.save(
            loan=self.get_loan()
        )

# Retrieve, update and delete a specific gold item
class GoldItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = GoldItemSerializer
    lookup_url_kwarg = "gold_item_id"
    def get_queryset(self):
        return GoldItem.objects.filter(
            id=self.kwargs["gold_item_id"],
            loan_id=self.kwargs["loan_id"],
            loan__shop_id=self.kwargs["shop_id"],
            loan__shop__owner=self.request.user
        ).select_related("loan")


# ==========================================
# PAYMENT CREATE VIEW
# ==========================================


class PaymentCreateView(generics.CreateAPIView):

    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):

        # Validate incoming payment data
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        # Get loan from URL
        loan_id = self.kwargs["loan_id"]

        # Verify shop and owner access
        loan = get_object_or_404(
            Loan,
            id=loan_id,
            shop_id=self.kwargs["shop_id"],
            shop__owner=request.user
        )

        # Record payment with proper API error handling
        try:
            payment = record_payment(
                loan_id=loan.id,
                owner=request.user,
                amount=data["amount"],
                interest_amount=data["interest_amount"],
                principal_amount=data["principal_amount"],
                payment_type=data["payment_type"],
                payment_date=data["payment_date"],
                receipt_number=data["receipt_number"],
                notes=data.get("notes", "")
            )

        except DjangoValidationError as exc:
            raise DRFValidationError(exc.messages) from exc

        # Return saved payment details
        response_serializer = self.get_serializer(payment)

        return Response(
            response_serializer.data,
            status=201
        )



# ==========================================
# PAYMENT HISTORY VIEW
# List payments for a specific loan
# ==========================================

class PaymentListView(generics.ListAPIView):

    # Convert payment records into JSON
    serializer_class = PaymentSerializer

    # Login required
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        # Get payments only from the requested loan,
        # shop and logged-in owner's shops
        return Payment.objects.filter(
            loan_id=self.kwargs["loan_id"],
            shop_id=self.kwargs["shop_id"],
            shop__owner=self.request.user
        ).select_related(
            "loan",
            "shop"
        ).order_by(
            "-payment_date",
            "-created_at"
        )


# ==========================================
# PAYMENT DETAIL VIEW
# Retrieve one payment receipt
# ==========================================

class PaymentDetailView(generics.RetrieveAPIView):

    # Convert payment record into JSON
    serializer_class = PaymentSerializer

    # Login required
    permission_classes = [IsAuthenticated]

    # Payment ID from URL
    lookup_url_kwarg = "payment_id"

    def get_queryset(self):

        # Only allow the owner to view payments
        # belonging to the requested shop and loan
        return Payment.objects.filter(
            id=self.kwargs["payment_id"],
            loan_id=self.kwargs["loan_id"],
            shop_id=self.kwargs["shop_id"],
            shop__owner=self.request.user
        ).select_related(
            "loan",
            "shop"
        )


# ==========================================
# PAYMENT PDF RECEIPT VIEW
# ==========================================

class PaymentReceiptView(generics.GenericAPIView):

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: OpenApiTypes.BINARY,
        }
    )
    def get(self, request, *args, **kwargs):

        payment = get_object_or_404(
            Payment.objects.select_related(
                "shop",
                "loan",
                "loan__customer"
            ),
            id=kwargs["payment_id"],
            shop_id=kwargs["shop_id"],
            loan_id=kwargs["loan_id"],
            shop__owner=request.user
        )

        pdf_file = generate_payment_receipt(payment)

        response = HttpResponse(
            pdf_file.getvalue(),
            content_type="application/pdf"
        )

        response["Content-Disposition"] = (
            f'attachment; filename="receipt_{payment.receipt_number}.pdf"'
        )

        return response
    

# ==========================================
# LOAN SETTLEMENT SUMMARY VIEW
# ==========================================

class LoanSettlementView(generics.GenericAPIView):

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: OpenApiTypes.OBJECT,
        }
    )
    def get(self, request, *args, **kwargs):

        loan = get_object_or_404(
            Loan.objects.select_related("shop", "customer"),
            id=kwargs["loan_id"],
            shop_id=kwargs["shop_id"],
            shop__owner=request.user,
        )

        from django.utils import timezone

        settlement_date = timezone.localdate()

        summary = get_loan_settlement_summary(
            loan,
            settlement_date,
        )

        return Response(summary)
    
# ==========================================
# LOAN CREDIT BALANCE VIEW
# ==========================================

class LoanCreditBalanceView(generics.GenericAPIView):

    serializer_class = CreditBalanceSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):

        loan = get_object_or_404(
            Loan,
            id=kwargs["loan_id"],
            shop_id=kwargs["shop_id"],
            shop__owner=request.user,
        )

        balance = get_or_create_credit_balance(loan)

        serializer = self.get_serializer(balance)

        return Response(serializer.data)


# ==========================================
# LOAN CREDIT TRANSACTION HISTORY
# ==========================================

class LoanCreditTransactionListView(generics.ListAPIView):

    serializer_class = CreditTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        return LoanCreditTransaction.objects.filter(
            credit_balance__loan_id=self.kwargs["loan_id"],
            credit_balance__loan__shop_id=self.kwargs["shop_id"],
            credit_balance__loan__shop__owner=self.request.user,
        ).select_related(
            "credit_balance",
            "credit_balance__loan",
            "reference_payment",
            "created_by",
        ).order_by("-created_at")


# ==========================================
# LOAN CREDIT ADJUSTMENT VIEW
# ==========================================

class LoanCreditAdjustmentView(generics.GenericAPIView):

    serializer_class = CreditAdjustmentSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):

        loan = get_object_or_404(
            Loan,
            id=kwargs["loan_id"],
            shop_id=kwargs["shop_id"],
            shop__owner=request.user,
        )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        try:
            transaction_record = adjust_loan_credit(
                loan_id=loan.id,
                owner=request.user,
                amount=data["amount"],
                adjustment_target=data["adjustment_target"],
                customer_confirmed=data["customer_confirmed"],
                confirmation_method=data["confirmation_method"],
                customer_confirmed_at=data["customer_confirmed_at"],
                notes=data.get("notes", ""),
            )

        except DjangoValidationError as exc:
            raise DRFValidationError(exc.messages) from exc

        response_serializer = CreditTransactionSerializer(
            transaction_record
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


# ==========================================
# LOAN CREDIT REFUND VIEW
# ==========================================

class LoanCreditRefundView(generics.GenericAPIView):

    serializer_class = CreditRefundSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):

        loan = get_object_or_404(
            Loan,
            id=kwargs["loan_id"],
            shop_id=kwargs["shop_id"],
            shop__owner=request.user,
        )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        try:
            transaction_record = refund_loan_credit(
                loan_id=loan.id,
                owner=request.user,
                amount=data["amount"],
                customer_confirmed=data["customer_confirmed"],
                confirmation_method=data["confirmation_method"],
                customer_confirmed_at=data["customer_confirmed_at"],
                notes=data.get("notes", ""),
            )

        except DjangoValidationError as exc:
            raise DRFValidationError(exc.messages) from exc

        response_serializer = CreditTransactionSerializer(
            transaction_record
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )