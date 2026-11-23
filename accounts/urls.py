
from django.urls import path

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import (
    OwnerRegistrationView,
    ShopListCreateView,
    ShopSettingsView,
    CustomerListCreateView,
    CustomerDetailView,
    CustomerStatusView,
    LoanListCreateView,
    LoanDetailView,
    LoanStatusView,
    GoldItemListCreateView,
    GoldItemDetailView,
    PaymentCreateView,
    PaymentListView,
    PaymentDetailView,
    PaymentReceiptView,
    LoanSettlementView,
    LoanCreditBalanceView,
    LoanCreditTransactionListView,
    LoanCreditAdjustmentView,
    LoanCreditRefundView,
)


urlpatterns = [

    # Owner authentication
    path(
        "register/",
        OwnerRegistrationView.as_view(),
        name="owner-register"
    ),

    path(
        "login/",
        TokenObtainPairView.as_view(),
        name="token-obtain-pair"
    ),

    path(
        "token/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh"
    ),

    # Shop management
    path(
        "shops/",
        ShopListCreateView.as_view(),
        name="shop-list-create"
    ),

    # Shop settings
    path(
        "shops/<int:shop_id>/settings/",
        ShopSettingsView.as_view(),
        name="shop-settings"
    ),

    # Customer management
    path(
        "shops/<int:shop_id>/customers/",
        CustomerListCreateView.as_view(),
        name="customer-list-create"
    ),

    # Customer detail and update
    path(
        "shops/<int:shop_id>/customers/<int:pk>/",
        CustomerDetailView.as_view(),
        name="customer-detail"
    ),
    
    
    # Customer activate / deactivate
    path(
        "shops/<int:shop_id>/customers/<int:pk>/status/",
        CustomerStatusView.as_view(),
        name="customer-status"
    ),
    
    # Loan management
    path(
        "shops/<int:shop_id>/loans/",
        LoanListCreateView.as_view(),
        name="loan-list-create"
    ),
    
    # Loan detail and update
    path(
        "shops/<int:shop_id>/loans/<int:pk>/",
        LoanDetailView.as_view(),
        name="loan-detail"
    ),
    
    # Loan status management
    path(
        "shops/<int:shop_id>/loans/<int:pk>/status/",
        LoanStatusView.as_view(),
        name="loan-status"
    ),
    
    # Gold item management
    path(
        "shops/<int:shop_id>/loans/<int:loan_id>/gold-items/",
        GoldItemListCreateView.as_view(),
        name="gold-item-list-create"
    ),
    
    # Retrieve a specific gold item from a loan
    path(
    "shops/<int:shop_id>/loans/<int:loan_id>/gold-items/<int:gold_item_id>/",
    GoldItemDetailView.as_view(),
    name="gold-item-detail"
),
    
    path(
    "shops/<int:shop_id>/loans/<int:loan_id>/payments/",
    PaymentCreateView.as_view(),
    name="payment-create",
),
    
    path(
    "shops/<int:shop_id>/loans/<int:loan_id>/payments/history/",
    PaymentListView.as_view(),
    name="payment-history",
),

    path(
    "shops/<int:shop_id>/loans/<int:loan_id>/payments/<int:payment_id>/",
    PaymentDetailView.as_view(),
    name="payment-detail",
),
    
    path(
    "shops/<int:shop_id>/loans/<int:loan_id>/payments/<int:payment_id>/receipt/",
    PaymentReceiptView.as_view(),
    name="payment-receipt",
),
    
    # Loan settlement summary
    path(
    "shops/<int:shop_id>/loans/<int:loan_id>/settlement/",
    LoanSettlementView.as_view(),
    name="loan-settlement",
),
    
        # Loan credit balance
    path(
        "shops/<int:shop_id>/loans/<int:loan_id>/credit/",
        LoanCreditBalanceView.as_view(),
        name="loan-credit-balance",
    ),

    # Loan credit transaction history
    path(
        "shops/<int:shop_id>/loans/<int:loan_id>/credit/transactions/",
        LoanCreditTransactionListView.as_view(),
        name="loan-credit-transactions",
    ),

    # Loan credit adjustment
    path(
        "shops/<int:shop_id>/loans/<int:loan_id>/credit/adjust/",
        LoanCreditAdjustmentView.as_view(),
        name="loan-credit-adjust",
    ),

    # Loan credit refund
    path(
        "shops/<int:shop_id>/loans/<int:loan_id>/credit/refund/",
        LoanCreditRefundView.as_view(),
        name="loan-credit-refund",
    ),
]
