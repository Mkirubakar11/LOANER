
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.contrib.auth.models import User

from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import (
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

from accounts.services.payment_service import record_payment

from accounts.services.credit_service import (
    adjust_loan_credit,
    refund_loan_credit,
)



class TenantIsolationTests(APITestCase):

    @classmethod
    def setUpTestData(cls):

        # Create Owner 1
        cls.owner1 = User.objects.create_user(
            username="owner_one",
            password="TestPassword@123"
        )
        OwnerProfile.objects.create(user=cls.owner1)

        # Create Owner 2
        cls.owner2 = User.objects.create_user(
            username="owner_two",
            password="TestPassword@123"
        )
        OwnerProfile.objects.create(user=cls.owner2)

        # Create separate shops
        cls.shop1 = Shop.objects.create(
            owner=cls.owner1,
            name="SHOP ONE",
            shop_code="SHOP001",
            address="Address One",
            phone_number="9000000001",
        )

        cls.shop2 = Shop.objects.create(
            owner=cls.owner2,
            name="SHOP TWO",
            shop_code="SHOP002",
            address="Address Two",
            phone_number="9000000002",
        )

        ShopSettings.objects.create(shop=cls.shop1)
        ShopSettings.objects.create(shop=cls.shop2)

        # Create customers
        cls.customer1 = Customer.objects.create(
            shop=cls.shop1,
            customer_number="CUS001",
            full_name="Customer One",
            phone_number="9000000003",
        )

        cls.customer2 = Customer.objects.create(
            shop=cls.shop2,
            customer_number="CUS002",
            full_name="Customer Two",
            phone_number="9000000004",
        )

        # Create loans
        cls.loan1 = Loan.objects.create(
            shop=cls.shop1,
            customer=cls.customer1,
            loan_number="LN001",
            principal_amount="10000.00",
            interest_rate="2.00",
            loan_date="2026-01-01",
            due_date="2027-01-01",
        )

        cls.loan2 = Loan.objects.create(
            shop=cls.shop2,
            customer=cls.customer2,
            loan_number="LN002",
            principal_amount="15000.00",
            interest_rate="2.00",
            loan_date="2026-01-01",
            due_date="2027-01-01",
        )

        # Create gold items
        cls.gold1 = GoldItem.objects.create(
            loan=cls.loan1,
            item_type="CHAIN",
            description="Shop One Gold",
            gross_weight="10.000",
            net_weight="9.000",
            purity="22K",
        )

        cls.gold2 = GoldItem.objects.create(
            loan=cls.loan2,
            item_type="CHAIN",
            description="Shop Two Gold",
            gross_weight="12.000",
            net_weight="11.000",
            purity="22K",
        )

    def authenticate_owner2(self):

        refresh = RefreshToken.for_user(self.owner2)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
        )

    def test_owner2_cannot_access_shop1_customers(self):

        self.authenticate_owner2()

        response = self.client.get(
            f"/api/accounts/shops/{self.shop1.id}/customers/"
        )

        self.assertEqual(response.status_code, 404)

    def test_owner2_cannot_access_shop1_customer_detail(self):

        self.authenticate_owner2()

        response = self.client.get(
            f"/api/accounts/shops/{self.shop1.id}/customers/{self.customer1.id}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_owner2_cannot_access_shop1_loans(self):

        self.authenticate_owner2()

        response = self.client.get(
            f"/api/accounts/shops/{self.shop1.id}/loans/"
        )

        self.assertEqual(response.status_code, 404)

    def test_owner2_cannot_access_shop1_loan_detail(self):

        self.authenticate_owner2()

        response = self.client.get(
            f"/api/accounts/shops/{self.shop1.id}/loans/{self.loan1.id}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_owner2_cannot_access_shop1_gold_items(self):

        self.authenticate_owner2()

        response = self.client.get(
            f"/api/accounts/shops/{self.shop1.id}/loans/{self.loan1.id}/gold-items/"
        )

        self.assertEqual(response.status_code, 404)

    def test_owner2_cannot_access_shop1_gold_item_detail(self):

        self.authenticate_owner2()

        response = self.client.get(
            f"/api/accounts/shops/{self.shop1.id}/loans/{self.loan1.id}/gold-items/{self.gold1.id}/"
        )

        self.assertEqual(response.status_code, 404)

    def test_owner2_cannot_update_shop1_gold_item(self):

        self.authenticate_owner2()

        response = self.client.patch(
            f"/api/accounts/shops/{self.shop1.id}/loans/{self.loan1.id}/gold-items/{self.gold1.id}/",
            {"description": "Unauthorized update"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_owner2_cannot_delete_shop1_gold_item(self):

        self.authenticate_owner2()

        response = self.client.delete(
            f"/api/accounts/shops/{self.shop1.id}/loans/{self.loan1.id}/gold-items/{self.gold1.id}/"
        )

        self.assertEqual(response.status_code, 404)

        # Confirm original gold item still exists
        self.assertTrue(
            GoldItem.objects.filter(id=self.gold1.id).exists()
        )

class PaymentServiceTests(TestCase):

    def setUp(self):

        self.owner = User.objects.create_user(
            username="payment_owner",
            password="TestPassword@123"
        )

        OwnerProfile.objects.create(user=self.owner)

        self.shop = Shop.objects.create(
            owner=self.owner,
            name="PAYMENT TEST SHOP",
            shop_code="PAY001",
            address="Test Address",
            phone_number="9000000010",
        )

        ShopSettings.objects.create(shop=self.shop)

        self.customer = Customer.objects.create(
            shop=self.shop,
            customer_number="PAYCUS001",
            full_name="Payment Test Customer",
            phone_number="9000000011",
        )

        self.loan = Loan.objects.create(
            shop=self.shop,
            customer=self.customer,
            loan_number="PAYLN001",
            principal_amount="10000.00",
            interest_rate="2.00",
            loan_date="2026-01-01",
            due_date="2027-01-01",
        )

    def make_payment(
        self,
        amount,
        interest_amount,
        principal_amount,
        payment_type,
        receipt_number,
        payment_date=datetime(2026, 2, 1, tzinfo=dt_timezone.utc)
    ):

        return record_payment(
            loan_id=self.loan.id,
            owner=self.owner,
            amount=amount,
            interest_amount=interest_amount,
            principal_amount=principal_amount,
            payment_type=payment_type,
            payment_date=payment_date,
            receipt_number=receipt_number,
        )

    def test_interest_only_payment(self):

        self.make_payment(
            amount="200.00",
            interest_amount="200.00",
            principal_amount="0.00",
            payment_type="INTEREST",
            receipt_number="REC001",
        )

        self.loan.refresh_from_db()

        self.assertEqual(self.loan.status, "ACTIVE")

        self.assertEqual(
            Payment.objects.filter(loan=self.loan).count(),
            1
        )

    def test_partial_principal_payment(self):

        self.make_payment(
            amount="5000.00",
            interest_amount="0.00",
            principal_amount="5000.00",
            payment_type="PRINCIPAL",
            receipt_number="REC002",
        )

        from accounts.services.payment_service import (
            get_outstanding_principal,
        )

        outstanding = get_outstanding_principal(
            self.loan,
            "2026-02-01"
        )

        self.assertEqual(
            outstanding,
            Decimal("5000.00")
        )

        self.loan.refresh_from_db()

        self.assertEqual(self.loan.status, "ACTIVE")

    def test_advance_interest_credit(self):

        self.make_payment(
            amount="300.00",
            interest_amount="300.00",
            principal_amount="0.00",
            payment_type="INTEREST",
            receipt_number="REC003",
        )

        from accounts.services.payment_service import (
            get_interest_balances,
        )

        balances = get_interest_balances(
            self.loan,
            datetime(2026, 2, 1, tzinfo=dt_timezone.utc)
        )

        self.assertEqual(
            balances["accrued_interest"],
            Decimal("200.00")
        )

        self.assertEqual(
            balances["advance_interest_credit"],
            Decimal("100.00")
        )

        self.assertEqual(
            balances["outstanding_interest"],
            Decimal("0.00")
        )
    
    def test_excess_interest_is_recorded_as_separate_credit(self):

        self.make_payment(
            amount="1500.00",
            interest_amount="1500.00",
            principal_amount="0.00",
            payment_type="INTEREST",
            receipt_number="REC008",
        )

        balance = LoanCreditBalance.objects.get(
            loan=self.loan
        )

        self.assertEqual(
            balance.total_credit_received,
            Decimal("1300.00")
        )

        self.assertEqual(
            balance.available_balance,
            Decimal("1300.00")
        )

    def test_full_settlement_closes_loan(self):

        self.make_payment(
            amount="10200.00",
            interest_amount="200.00",
            principal_amount="10000.00",
            payment_type="BOTH",
            receipt_number="REC004",
        )

        self.loan.refresh_from_db()

        self.assertEqual(self.loan.status, "CLOSED")

    def test_loan_remains_open_when_interest_is_outstanding(self):

        self.make_payment(
            amount="100.00",
            interest_amount="100.00",
            principal_amount="0.00",
            payment_type="INTEREST",
            receipt_number="REC005",
        )

        self.loan.refresh_from_db()

        self.assertEqual(self.loan.status, "ACTIVE")

    def test_closed_loan_rejects_further_payment(self):

        self.make_payment(
            amount="10200.00",
            interest_amount="200.00",
            principal_amount="10000.00",
            payment_type="BOTH",
            receipt_number="REC006",
        )

        with self.assertRaises(ValidationError):

            self.make_payment(
                amount="100.00",
                interest_amount="100.00",
                principal_amount="0.00",
                payment_type="INTEREST",
                receipt_number="REC007",
            )
    
    def test_existing_credit_is_preserved_after_later_payment(self):

        self.make_payment(
            amount="1500.00",
            interest_amount="1500.00",
            principal_amount="0.00",
            payment_type="INTEREST",
            receipt_number="REC009",
            payment_date=datetime(
                2026, 2, 1, tzinfo=dt_timezone.utc
            ),
        )

        self.make_payment(
            amount="500.00",
            interest_amount="500.00",
            principal_amount="0.00",
            payment_type="INTEREST",
            receipt_number="REC010",
            payment_date=datetime(
                2026, 3, 1, tzinfo=dt_timezone.utc
            ),
        )

        balance = LoanCreditBalance.objects.get(
            loan=self.loan
        )

        self.assertEqual(
            balance.total_credit_received,
            Decimal("1600.00")
        )

        self.assertEqual(
            balance.available_balance,
            Decimal("1600.00")
        )
    def test_new_credit_is_added_after_previous_adjustment(self):

        # First payment creates ₹1,300 credit.
        self.make_payment(
            amount="1500.00",
            interest_amount="1500.00",
            principal_amount="0.00",
            payment_type="INTEREST",
            receipt_number="REC011",
            payment_date=datetime(
                2026, 2, 1, tzinfo=dt_timezone.utc
            ),
        )

        # Owner adjusts ₹500 from available credit.
        adjust_loan_credit(
            loan_id=self.loan.id,
            owner=self.owner,
            amount="500.00",
            adjustment_target="INTEREST",
            customer_confirmed=True,
            confirmation_method="IN_PERSON",
            customer_confirmed_at=datetime(
                2026, 2, 1, 10, 0,
                tzinfo=dt_timezone.utc
            ),
        )

        # Later payment creates another ₹300 excess.
        self.make_payment(
            amount="500.00",
            interest_amount="500.00",
            principal_amount="0.00",
            payment_type="INTEREST",
            receipt_number="REC012",
            payment_date=datetime(
                2026, 3, 1, tzinfo=dt_timezone.utc
            ),
        )

        balance = LoanCreditBalance.objects.get(
            loan=self.loan
        )

        self.assertEqual(
            balance.total_credit_received,
            Decimal("1600.00")
        )

        self.assertEqual(
            balance.total_credit_adjusted,
            Decimal("500.00")
        )

        self.assertEqual(
            balance.available_balance,
            Decimal("1100.00")
        )
        
    def test_new_credit_is_added_after_previous_refund(self):

        # First payment creates ₹1,300 credit.
        self.make_payment(
            amount="1500.00",
            interest_amount="1500.00",
            principal_amount="0.00",
            payment_type="INTEREST",
            receipt_number="REC013",
            payment_date=datetime(
                2026, 2, 1, tzinfo=dt_timezone.utc
            ),
        )

        # Owner refunds ₹500 to customer.
        refund_loan_credit(
            loan_id=self.loan.id,
            owner=self.owner,
            amount="500.00",
            customer_confirmed=True,
            confirmation_method="IN_PERSON",
            customer_confirmed_at=datetime(
                2026, 2, 1, 10, 0,
                tzinfo=dt_timezone.utc
            ),
            notes="Customer refund request",
        )

        # Later payment creates another ₹300 excess.
        self.make_payment(
            amount="500.00",
            interest_amount="500.00",
            principal_amount="0.00",
            payment_type="INTEREST",
            receipt_number="REC014",
            payment_date=datetime(
                2026, 3, 1, tzinfo=dt_timezone.utc
            ),
        )

        balance = LoanCreditBalance.objects.get(
            loan=self.loan
        )

        self.assertEqual(
            balance.total_credit_received,
            Decimal("1600.00")
        )

        self.assertEqual(
            balance.total_refunded,
            Decimal("500.00")
        )

        self.assertEqual(
            balance.available_balance,
            Decimal("1100.00")
        )
        
               
class SettlementAPITests(APITestCase):

    def setUp(self):

        # Create owner
        self.owner = User.objects.create_user(
            username="settlement_owner",
            password="TestPassword@123"
        )
        OwnerProfile.objects.create(user=self.owner)

        # Create another owner
        self.other_owner = User.objects.create_user(
            username="settlement_other",
            password="TestPassword@123"
        )
        OwnerProfile.objects.create(user=self.other_owner)

        # Create shop
        self.shop = Shop.objects.create(
            owner=self.owner,
            name="SETTLEMENT TEST SHOP",
            shop_code="SETT001",
            address="Test Address",
            phone_number="9000000020",
        )

        # Create customer
        self.customer = Customer.objects.create(
            shop=self.shop,
            customer_number="SETCUS001",
            full_name="Settlement Test Customer",
            phone_number="9000000021",
        )

        # Create loan
        self.loan = Loan.objects.create(
            shop=self.shop,
            customer=self.customer,
            loan_number="SETLN001",
            principal_amount="10000.00",
            interest_rate="2.00",
            loan_date="2026-01-01",
            due_date="2027-01-01",
        )

        self.url = (
            f"/api/accounts/shops/{self.shop.id}/"
            f"loans/{self.loan.id}/settlement/"
        )

    def test_owner_can_access_own_loan_settlement(self):

        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        self.assertIn("outstanding_principal", response.data)
        self.assertIn("outstanding_interest", response.data)
        self.assertIn("settlement_amount", response.data)
        self.assertIn("can_close", response.data)

    def test_unauthenticated_user_cannot_access_settlement(self):

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)

    def test_other_owner_cannot_access_settlement(self):

        self.client.force_authenticate(user=self.other_owner)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    def test_invalid_loan_id_returns_404(self):

        self.client.force_authenticate(user=self.owner)

        invalid_url = (
            f"/api/accounts/shops/{self.shop.id}/"
            f"loans/999999/settlement/"
        )

        response = self.client.get(invalid_url)

        self.assertEqual(response.status_code, 404)

    def test_interest_credit_adjustment_reduces_settlement(self):

        self.client.force_authenticate(user=self.owner)

        # Create available customer credit.
        balance = LoanCreditBalance.objects.create(
            loan=self.loan,
            total_credit_received=Decimal("1000.00"),
            available_balance=Decimal("1000.00"),
        )

        # Get settlement before adjustment.
        before = self.client.get(self.url)

        self.assertEqual(before.status_code, 200)

        settlement_before = Decimal(
            str(before.data["settlement_amount"])
        )

        # Owner adjusts ₹500 against interest.
        adjust_loan_credit(
            loan_id=self.loan.id,
            owner=self.owner,
            amount="500.00",
            adjustment_target="INTEREST",
            customer_confirmed=True,
            confirmation_method="IN_PERSON",
            customer_confirmed_at=datetime.now(
                dt_timezone.utc
            ),
        )

        # Get settlement after adjustment.
        after = self.client.get(self.url)

        self.assertEqual(after.status_code, 200)

        settlement_after = Decimal(
            str(after.data["settlement_amount"])
        )

        self.assertEqual(
            settlement_after,
            settlement_before - Decimal("500.00")
        )

    def test_principal_credit_adjustment_reduces_settlement(self):

        self.client.force_authenticate(user=self.owner)

        # Create available customer credit.
        LoanCreditBalance.objects.create(
            loan=self.loan,
            total_credit_received=Decimal("1000.00"),
            available_balance=Decimal("1000.00"),
        )

        # Get settlement before adjustment.
        before = self.client.get(self.url)

        self.assertEqual(before.status_code, 200)

        settlement_before = Decimal(
            str(before.data["settlement_amount"])
        )

        # Owner adjusts ₹500 against principal.
        adjust_loan_credit(
            loan_id=self.loan.id,
            owner=self.owner,
            amount="500.00",
            adjustment_target="PRINCIPAL",
            customer_confirmed=True,
            confirmation_method="IN_PERSON",
            customer_confirmed_at=datetime.now(
                dt_timezone.utc
            ),
        )

        # Get settlement after adjustment.
        after = self.client.get(self.url)

        self.assertEqual(after.status_code, 200)

        settlement_after = Decimal(
            str(after.data["settlement_amount"])
        )

        self.assertEqual(
            after.data["outstanding_principal"],
            Decimal("9500.00")
        )

        self.assertEqual(
            settlement_after,
            settlement_before - Decimal("500.00")
        )


class CreditOutgoingTests(TestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            username="credit_owner",
            password="TestPassword@123"
        )
        OwnerProfile.objects.create(user=self.owner)

        self.shop = Shop.objects.create(
            owner=self.owner,
            name="CREDIT TEST SHOP",
            shop_code="CRD001",
            address="Test Address",
            phone_number="9000000030",
        )

        self.customer = Customer.objects.create(
            shop=self.shop,
            customer_number="CRDCUS001",
            full_name="Credit Test Customer",
            phone_number="9000000031",
        )

        self.loan = Loan.objects.create(
            shop=self.shop,
            customer=self.customer,
            loan_number="CRDLN001",
            principal_amount="10000.00",
            interest_rate="2.00",
            loan_date="2026-01-01",
            due_date="2027-01-01",
        )

        self.balance = LoanCreditBalance.objects.create(
            loan=self.loan,
            total_credit_received=Decimal("1000.00"),
            total_credit_adjusted=Decimal("0.00"),
            total_refunded=Decimal("0.00"),
            available_balance=Decimal("1000.00"),
        )

        self.confirmed_at = datetime(
            2026, 11, 18, 10, 0,
            tzinfo=dt_timezone.utc
        )

    def test_adjust_credit_against_interest(self):
        record = adjust_loan_credit(
            loan_id=self.loan.id,
            owner=self.owner,
            amount="200.00",
            adjustment_target="INTEREST",
            customer_confirmed=True,
            confirmation_method="IN_PERSON",
            customer_confirmed_at=self.confirmed_at,
        )

        self.balance.refresh_from_db()

        self.assertEqual(record.transaction_type, "ADJUSTMENT")
        self.assertEqual(record.adjustment_target, "INTEREST")
        self.assertEqual(self.balance.available_balance, Decimal("800.00"))
        self.assertEqual(self.balance.total_credit_adjusted, Decimal("200.00"))

    def test_adjustment_rejected_without_customer_confirmation(self):
        with self.assertRaises(ValidationError):
            adjust_loan_credit(
                loan_id=self.loan.id,
                owner=self.owner,
                amount="100.00",
                adjustment_target="PRINCIPAL",
                customer_confirmed=False,
                confirmation_method="IN_PERSON",
                customer_confirmed_at=self.confirmed_at,
            )

    def test_adjustment_rejected_when_balance_is_insufficient(self):
        with self.assertRaises(ValidationError):
            adjust_loan_credit(
                loan_id=self.loan.id,
                owner=self.owner,
                amount="1500.00",
                adjustment_target="INTEREST",
                customer_confirmed=True,
                confirmation_method="IN_PERSON",
                customer_confirmed_at=self.confirmed_at,
            )

    def test_refund_credit_successfully(self):
        record = refund_loan_credit(
            loan_id=self.loan.id,
            owner=self.owner,
            amount="300.00",
            customer_confirmed=True,
            confirmation_method="WHATSAPP",
            customer_confirmed_at=self.confirmed_at,
            notes="Customer refund request",
        )

        self.balance.refresh_from_db()

        self.assertEqual(record.transaction_type, "REFUND")
        self.assertEqual(self.balance.available_balance, Decimal("700.00"))
        self.assertEqual(self.balance.total_refunded, Decimal("300.00"))

    def test_invalid_adjustment_target_is_rejected(self):
        with self.assertRaises(ValidationError):
            adjust_loan_credit(
                loan_id=self.loan.id,
                owner=self.owner,
                amount="100.00",
                adjustment_target="INVALID",
                customer_confirmed=True,
                confirmation_method="IN_PERSON",
                customer_confirmed_at=self.confirmed_at,
            )

# ==========================================
# LOAN CREDIT API TESTS
# ==========================================

class LoanCreditAPITests(APITestCase):

    def setUp(self):

        # Create owner
        self.owner = User.objects.create_user(
            username="credit_api_owner",
            password="TestPassword@123"
        )
        OwnerProfile.objects.create(user=self.owner)

        # Create another owner
        self.other_owner = User.objects.create_user(
            username="credit_api_other",
            password="TestPassword@123"
        )
        OwnerProfile.objects.create(user=self.other_owner)

        # Create shop
        self.shop = Shop.objects.create(
            owner=self.owner,
            name="CREDIT API SHOP",
            shop_code="CRDAPI001",
            address="Test Address",
            phone_number="9000000040",
        )

        # Create customer
        self.customer = Customer.objects.create(
            shop=self.shop,
            customer_number="CRDAPICUS001",
            full_name="Credit API Customer",
            phone_number="9000000041",
        )

        # Create loan
        self.loan = Loan.objects.create(
            shop=self.shop,
            customer=self.customer,
            loan_number="CRDAPI-LN001",
            principal_amount="10000.00",
            interest_rate="2.00",
            loan_date="2026-01-01",
            due_date="2027-01-01",
        )

        # Create available credit
        self.balance = LoanCreditBalance.objects.create(
            loan=self.loan,
            total_credit_received=Decimal("1000.00"),
            total_credit_adjusted=Decimal("0.00"),
            total_refunded=Decimal("0.00"),
            available_balance=Decimal("1000.00"),
        )

        self.base_url = (
            f"/api/accounts/shops/{self.shop.id}/"
            f"loans/{self.loan.id}/credit/"
        )

        self.client.force_authenticate(user=self.owner)

        self.confirmed_at = "2026-11-18T10:00:00Z"

    # --------------------------------------
    # CREDIT BALANCE API
    # --------------------------------------

    def test_owner_can_view_credit_balance(self):

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Decimal(str(response.data["available_balance"])),
            Decimal("1000.00")
        )

    # --------------------------------------
    # CREDIT TRANSACTION HISTORY API
    # --------------------------------------

    def test_owner_can_view_credit_transactions(self):

        response = self.client.get(
            self.base_url + "transactions/"
        )

        self.assertEqual(response.status_code, 200)

    # --------------------------------------
    # CREDIT ADJUSTMENT API
    # --------------------------------------

    def test_owner_can_adjust_credit(self):

        payload = {
            "amount": "200.00",
            "adjustment_target": "INTEREST",
            "customer_confirmed": True,
            "confirmation_method": "IN_PERSON",
            "customer_confirmed_at": self.confirmed_at,
            "notes": "Customer confirmed interest adjustment",
        }

        response = self.client.post(
            self.base_url + "adjust/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        self.balance.refresh_from_db()

        self.assertEqual(
            self.balance.available_balance,
            Decimal("800.00")
        )

        self.assertEqual(
            self.balance.total_credit_adjusted,
            Decimal("200.00")
        )

    # --------------------------------------
    # CREDIT REFUND API
    # --------------------------------------

    def test_owner_can_refund_credit(self):

        payload = {
            "amount": "300.00",
            "customer_confirmed": True,
            "confirmation_method": "IN_PERSON",
            "customer_confirmed_at": self.confirmed_at,
            "notes": "Customer confirmed credit refund",
        }

        response = self.client.post(
            self.base_url + "refund/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        self.balance.refresh_from_db()

        self.assertEqual(
            self.balance.available_balance,
            Decimal("700.00")
        )

        self.assertEqual(
            self.balance.total_refunded,
            Decimal("300.00")
        )

    # --------------------------------------
    # AUTHENTICATION TEST
    # --------------------------------------

    def test_unauthenticated_user_cannot_view_credit(self):

        self.client.force_authenticate(user=None)

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, 401)

    # --------------------------------------
    # TENANT ISOLATION TEST
    # --------------------------------------

    def test_other_owner_cannot_view_credit(self):

        self.client.force_authenticate(user=self.other_owner)

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, 404)