
import { useEffect, useState } from "react";
import {
  Receipt,
  Search,
  RefreshCw,
  Plus,
  Eye,
  Download,
  X,
  IndianRupee,
  Wallet,
  Printer,
} from "lucide-react";

import api from "../services/api";
import "./Payments.css";

const emptyForm = {
  loan: "",
  payment_type: "INTEREST",
  amount: "",
  interest_amount: "",
  principal_amount: "",
  payment_date: new Date().toISOString().slice(0, 10),
  notes: "",
};

const getList = (data) => {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  if (Array.isArray(data?.payments)) return data.payments;
  if (Array.isArray(data?.shops)) return data.shops;
  return [];
};

function Payments({ shopId }) {
  const [loans, setLoans] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [payments, setPayments] = useState([]);
  const [shopName, setShopName] = useState("");

  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);
  const [error, setError] = useState("");

  const [search, setSearch] = useState("");
  const [selectedType, setSelectedType] = useState("ALL");

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const [selectedPayment, setSelectedPayment] = useState(null);
  const [downloadingId, setDownloadingId] = useState(null);
  const [printingId, setPrintingId] = useState(null);

  // Load shop, loans, customers and payment history
  useEffect(() => {
    let cancelled = false;

    const fetchData = async () => {
      try {
        setError("");

        const [loanResponse, customerResponse, shopResponse] =
          await Promise.all([
            api.get(`shops/${shopId}/loans/`),
            api.get(`shops/${shopId}/customers/`),
            api.get("shops/"),
          ]);

        const loanList = getList(loanResponse.data);
        const customerList = getList(customerResponse.data);
        const shopList = getList(shopResponse.data);

        if (cancelled) return;

        setLoans(loanList);
        setCustomers(customerList);

        const currentShop = shopList.find(
          (shop) => String(shop.id) === String(shopId)
        );

        setShopName(currentShop?.name || "Pawn Shop");

        const historyResponses = await Promise.all(
          loanList.map((loan) =>
            api.get(
              `shops/${shopId}/loans/${loan.id}/payments/history/`
            )
          )
        );

        const allPayments = historyResponses.flatMap(
          (response, index) => {
            const loan = loanList[index];

            return getList(response.data).map((payment) => ({
              ...payment,
              loan_id: loan.id,
              loan_number: loan.loan_number,
            }));
          }
        );

        if (!cancelled) {
          setPayments(allPayments);
        }
      } catch (err) {
        console.error("Payments loading error:", err);

        if (!cancelled) {
          setError("Unable to load payment records. Please refresh.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      cancelled = true;
    };
  }, [shopId, refreshKey]);

  const refreshData = () => {
    setLoading(true);
    setRefreshKey((previous) => previous + 1);
  };

  const getLoan = (loanId) =>
    loans.find((loan) => String(loan.id) === String(loanId));

  const getCustomerName = (loan) => {
    if (typeof loan?.customer === "object" && loan.customer !== null) {
      return (
        loan.customer.full_name ||
        loan.customer.name ||
        `Customer #${loan.customer.id}`
      );
    }

    const customer = customers.find(
      (item) => String(item.id) === String(loan?.customer)
    );

    return customer?.full_name || customer?.name || "Customer";
  };

  const formatCurrency = (value) =>
    new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(Number(value || 0));

  const formatDate = (value) => {
    if (!value) return "—";

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) return value;

    return date.toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  };

  const totalAmount = payments.reduce(
    (sum, payment) => sum + Number(payment.amount || 0),
    0
  );

  const totalInterest = payments.reduce(
    (sum, payment) => sum + Number(payment.interest_amount || 0),
    0
  );

  const totalPrincipal = payments.reduce(
    (sum, payment) => sum + Number(payment.principal_amount || 0),
    0
  );

  // Search and filter
  const filteredPayments = payments.filter((payment) => {
    const loan = getLoan(payment.loan_id);
    const customerName = getCustomerName(loan);

    const text = [
      payment.receipt_number,
      payment.loan_number,
      customerName,
      payment.payment_type,
      payment.notes,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();

    const matchesSearch = text.includes(search.toLowerCase());

    const matchesType =
      selectedType === "ALL" ||
      String(payment.payment_type).toUpperCase() === selectedType;

    return matchesSearch && matchesType;
  });

  const openAddForm = () => {
    setForm({
      ...emptyForm,
      loan: loans[0]?.id ? String(loans[0].id) : "",
    });
    setFormError("");
    setShowForm(true);
  };

  const closeForm = () => {
    setShowForm(false);
    setForm(emptyForm);
    setFormError("");
  };

  const handleTypeChange = (event) => {
    const paymentType = event.target.value;

    setForm((previous) => ({
      ...previous,
      payment_type: paymentType,
      amount: "",
      interest_amount: "",
      principal_amount: "",
    }));
  };

  const handleAmountChange = (event) => {
    const amount = event.target.value;

    setForm((previous) => {
      if (previous.payment_type === "INTEREST") {
        return {
          ...previous,
          amount,
          interest_amount: amount,
          principal_amount: "0",
        };
      }

      if (previous.payment_type === "PRINCIPAL") {
        return {
          ...previous,
          amount,
          interest_amount: "0",
          principal_amount: amount,
        };
      }

      return {
        ...previous,
        amount,
      };
    });
  };

  const handleAllocationChange = (event) => {
    const { name, value } = event.target;

    setForm((previous) => {
      const next = {
        ...previous,
        [name]: value,
      };

      next.amount = (
        Number(
          name === "interest_amount"
            ? value
            : previous.interest_amount || 0
        ) +
        Number(
          name === "principal_amount"
            ? value
            : previous.principal_amount || 0
        )
      ).toFixed(2);

      return next;
    });
  };

  // Create payment
  const handleSubmit = async (event) => {
    event.preventDefault();

    const amount = Number(form.amount);
    const interest = Number(form.interest_amount || 0);
    const principal = Number(form.principal_amount || 0);

    if (!form.loan) {
      setFormError("Please select a loan.");
      return;
    }

    if (
      !Number.isFinite(amount) ||
      !Number.isFinite(interest) ||
      !Number.isFinite(principal) ||
      amount <= 0
    ) {
      setFormError("Enter a valid payment amount.");
      return;
    }

    if (Math.abs(amount - interest - principal) > 0.001) {
      setFormError(
        "Payment amount must equal interest plus principal."
      );
      return;
    }

    if (
      form.payment_type === "INTEREST" &&
      (interest <= 0 || principal !== 0)
    ) {
      setFormError("Interest payment must contain only interest.");
      return;
    }

    if (
      form.payment_type === "PRINCIPAL" &&
      (principal <= 0 || interest !== 0)
    ) {
      setFormError("Principal payment must contain only principal.");
      return;
    }

    if (
      form.payment_type === "BOTH" &&
      (interest <= 0 || principal <= 0)
    ) {
      setFormError(
        "Both interest and principal amounts must be greater than zero."
      );
      return;
    }

    const payload = {
      amount: amount.toFixed(2),
      interest_amount: interest.toFixed(2),
      principal_amount: principal.toFixed(2),
      payment_type: form.payment_type,
      payment_date: form.payment_date,
      notes: form.notes.trim(),
    };

    try {
      setSaving(true);
      setFormError("");

      await api.post(
        `shops/${shopId}/loans/${form.loan}/payments/`,
        payload
      );

      closeForm();
      setSuccessMessage("Payment recorded successfully.");
      refreshData();
    } catch (err) {
      console.error("Payment creation error:", err);

      const data = err.response?.data;

      const message =
        data && typeof data === "object"
          ? Object.entries(data)
              .map(([key, value]) => {
                const detail = Array.isArray(value)
                  ? value.join(", ")
                  : String(value);

                return `${key}: ${detail}`;
              })
              .join(" | ")
          : "Unable to record payment. Please check the details.";

      setFormError(message);
    } finally {
      setSaving(false);
    }
  };

  // Get PDF receipt from existing backend API
  const getReceiptBlob = async (payment) => {
    const response = await api.get(
      `shops/${shopId}/loans/${payment.loan_id}/payments/${payment.id}/receipt/`,
      { responseType: "blob" }
    );

    return new Blob([response.data], {
      type: "application/pdf",
    });
  };

  // Download PDF receipt
  const downloadReceipt = async (payment) => {
    let url;

    try {
      setDownloadingId(payment.id);

      const blob = await getReceiptBlob(payment);
      url = window.URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.href = url;
      link.download = `${
        payment.receipt_number || "payment-receipt"
      }.pdf`;

      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error("Receipt download error:", err);
      setError("Unable to download receipt.");
    } finally {
      if (url) {
        setTimeout(() => window.URL.revokeObjectURL(url), 60000);
      }
      setDownloadingId(null);
    }
  };

  // Open PDF receipt and trigger browser print
  const printReceipt = async (payment) => {
    let url;

    try {
      setPrintingId(payment.id);

      // Open a blank tab immediately to avoid popup blocking
      const printWindow = window.open("", "_blank");

      if (!printWindow) {
        setError("Please allow pop-ups in your browser to print receipts.");
        return;
      }

      const blob = await getReceiptBlob(payment);
      url = window.URL.createObjectURL(blob);

      printWindow.location.href = url;

      // Give the browser PDF viewer time to load before printing
      setTimeout(() => {
        try {
          printWindow.focus();
          printWindow.print();
        } catch (err) {
          console.error("Print dialog error:", err);
        }
      }, 1500);

      // Keep the PDF URL alive while the browser loads it
      setTimeout(() => {
        if (url) window.URL.revokeObjectURL(url);
      }, 60000);
    } catch (err) {
      console.error("Receipt print error:", err);
      setError("Unable to open receipt for printing.");

      if (url) {
        window.URL.revokeObjectURL(url);
      }
    } finally {
      setPrintingId(null);
    }
  };

  return (
    <div className="payments-page">
      <div className="payments-heading">
        <div>
          <span className="payments-eyebrow">PAYMENT MANAGEMENT</span>
          <h1>Payments</h1>
          <p>Track collections, payment history and receipts.</p>
        </div>

        <button
          type="button"
          className="payment-add-button"
          onClick={openAddForm}
          disabled={loans.length === 0}
        >
          <Plus size={18} />
          Record Payment
        </button>
      </div>

      <div className="payments-summary">
        <div className="payment-summary-card">
          <div className="payment-summary-icon">
            <Receipt size={21} />
          </div>
          <div>
            <span>Total Payments</span>
            <h2>{loading ? "..." : payments.length}</h2>
          </div>
        </div>

        <div className="payment-summary-card">
          <div className="payment-summary-icon interest-icon">
            <IndianRupee size={21} />
          </div>
          <div>
            <span>Interest Collected</span>
            <h2>{loading ? "..." : formatCurrency(totalInterest)}</h2>
          </div>
        </div>

        <div className="payment-summary-card">
          <div className="payment-summary-icon principal-icon">
            <Wallet size={21} />
          </div>
          <div>
            <span>Principal Collected</span>
            <h2>{loading ? "..." : formatCurrency(totalPrincipal)}</h2>
          </div>
        </div>

        <div className="payment-summary-card">
          <div className="payment-summary-icon total-icon">
            <IndianRupee size={21} />
          </div>
          <div>
            <span>Total Amount</span>
            <h2>{loading ? "..." : formatCurrency(totalAmount)}</h2>
          </div>
        </div>
      </div>

      <div className="payments-toolbar">
        <div className="payments-search">
          <Search size={18} />
          <input
            placeholder="Search receipt, loan or customer..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>

        <select
          className="payment-type-filter"
          value={selectedType}
          onChange={(event) => setSelectedType(event.target.value)}
        >
          <option value="ALL">All Payment Types</option>
          <option value="INTEREST">Interest</option>
          <option value="PRINCIPAL">Principal</option>
          <option value="BOTH">Both</option>
        </select>

        <button
          type="button"
          className="payment-refresh-button"
          onClick={refreshData}
          disabled={loading}
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      {successMessage && (
        <div className="payment-success">
          {successMessage}
          <button
            type="button"
            onClick={() => setSuccessMessage("")}
            aria-label="Dismiss"
          >
            <X size={15} />
          </button>
        </div>
      )}

      {error && (
        <div className="payment-error">
          {error}
          <button type="button" onClick={refreshData}>
            Try Again
          </button>
        </div>
      )}

      {loading ? (
        <div className="payments-empty">
          Loading payment records...
        </div>
      ) : !error && filteredPayments.length === 0 ? (
        <div className="payments-empty">
          <Receipt size={38} />
          <h3>No payment records found</h3>
          <p>
            {search || selectedType !== "ALL"
              ? "Try changing your search or filter."
              : "Payment records will appear here."}
          </p>
        </div>
      ) : !error ? (
        <div className="payments-table-wrapper">
          <table className="payments-table">
            <thead>
              <tr>
                <th>Receipt No.</th>
                <th>Loan Number</th>
                <th>Customer</th>
                <th>Payment Date</th>
                <th>Payment Type</th>
                <th>Interest</th>
                <th>Principal</th>
                <th>Total Amount</th>
                <th>Actions</th>
              </tr>
            </thead>

            <tbody>
              {filteredPayments.map((payment) => {
                const loan = getLoan(payment.loan_id);

                return (
                  <tr key={payment.id}>
                    <td>
                      <strong>
                        {payment.receipt_number || `#${payment.id}`}
                      </strong>
                    </td>

                    <td>
                      {payment.loan_number || loan?.loan_number || "—"}
                    </td>

                    <td>{getCustomerName(loan)}</td>

                    <td>{formatDate(payment.payment_date)}</td>

                    <td>
                      <span
                        className={`payment-type-badge ${String(
                          payment.payment_type
                        ).toLowerCase()}`}
                      >
                        {payment.payment_type}
                      </span>
                    </td>

                    <td>{formatCurrency(payment.interest_amount)}</td>

                    <td>{formatCurrency(payment.principal_amount)}</td>

                    <td>
                      <strong>{formatCurrency(payment.amount)}</strong>
                    </td>

                    <td>
                      <div className="payment-actions">
                        <button
                          type="button"
                          className="payment-action-button"
                          title="View details"
                          onClick={() => setSelectedPayment(payment)}
                        >
                          <Eye size={16} />
                        </button>

                        <button
                          type="button"
                          className="payment-action-button"
                          title="Download receipt"
                          onClick={() => downloadReceipt(payment)}
                          disabled={downloadingId === payment.id}
                        >
                          <Download size={16} />
                        </button>

                        <button
                          type="button"
                          className="payment-action-button"
                          title="Print receipt"
                          onClick={() => printReceipt(payment)}
                          disabled={printingId === payment.id}
                        >
                          <Printer size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}

      {/* Record payment modal */}
      {showForm && (
        <div
          className="payment-modal-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) closeForm();
          }}
        >
          <div
            className="payment-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="payment-modal-title"
          >
            <div className="payment-modal-heading">
              <div>
                <span className="payments-eyebrow">NEW TRANSACTION</span>
                <h2 id="payment-modal-title">Record Payment</h2>
              </div>

              <button
                type="button"
                className="payment-modal-close"
                onClick={closeForm}
                aria-label="Close"
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="payment-form-grid">
                <label className="payment-form-full">
                  Select Loan *
                  <select
                    value={form.loan}
                    onChange={(event) =>
                      setForm((previous) => ({
                        ...previous,
                        loan: event.target.value,
                      }))
                    }
                    required
                  >
                    <option value="">Choose a loan</option>

                    {loans.map((loan) => (
                      <option key={loan.id} value={loan.id}>
                        {loan.loan_number} - {getCustomerName(loan)}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="payment-form-full">
                  Payment Type *
                  <select
                    value={form.payment_type}
                    onChange={handleTypeChange}
                    required
                  >
                    <option value="INTEREST">Interest</option>
                    <option value="PRINCIPAL">Principal</option>
                    <option value="BOTH">Both</option>
                  </select>
                </label>

                {form.payment_type === "BOTH" ? (
                  <>
                    <label>
                      Interest Amount *
                      <input
                        type="number"
                        name="interest_amount"
                        min="0.01"
                        step="0.01"
                        value={form.interest_amount}
                        onChange={handleAllocationChange}
                        required
                      />
                    </label>

                    <label>
                      Principal Amount *
                      <input
                        type="number"
                        name="principal_amount"
                        min="0.01"
                        step="0.01"
                        value={form.principal_amount}
                        onChange={handleAllocationChange}
                        required
                      />
                    </label>
                  </>
                ) : (
                  <label className="payment-form-full">
                    {form.payment_type === "INTEREST"
                      ? "Interest Amount *"
                      : "Principal Amount *"}
                    <input
                      type="number"
                      min="0.01"
                      step="0.01"
                      value={form.amount}
                      onChange={handleAmountChange}
                      required
                    />
                  </label>
                )}

                <label>
                  Total Payment Amount
                  <input
                    type="number"
                    value={form.amount}
                    readOnly
                    className="payment-total-input"
                  />
                </label>

                <label>
                  Payment Date *
                  <input
                    type="date"
                    value={form.payment_date}
                    max={new Date().toISOString().slice(0, 10)}
                    onChange={(event) =>
                      setForm((previous) => ({
                        ...previous,
                        payment_date: event.target.value,
                      }))
                    }
                    required
                  />
                </label>

                <label className="payment-form-full">
                  Notes
                  <textarea
                    rows={3}
                    placeholder="Optional payment notes..."
                    value={form.notes}
                    onChange={(event) =>
                      setForm((previous) => ({
                        ...previous,
                        notes: event.target.value,
                      }))
                    }
                  />
                </label>
              </div>

              {formError && (
                <div className="payment-form-error">{formError}</div>
              )}

              <div className="payment-form-actions">
                <button
                  type="button"
                  className="payment-cancel-button"
                  onClick={closeForm}
                  disabled={saving}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="payment-save-button"
                  disabled={saving}
                >
                  {saving ? "Saving..." : "Save Payment"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Payment details modal */}
      {selectedPayment && (
        <div
          className="payment-modal-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setSelectedPayment(null);
            }
          }}
        >
          <div className="payment-modal payment-details-modal">
            <div className="payment-modal-heading">
              <div>
                <span className="payments-eyebrow">
                  PAYMENT INFORMATION
                </span>
                <h2>
                  {selectedPayment.receipt_number ||
                    `Payment #${selectedPayment.id}`}
                </h2>
              </div>

              <button
                type="button"
                className="payment-modal-close"
                onClick={() => setSelectedPayment(null)}
                aria-label="Close"
              >
                <X size={20} />
              </button>
            </div>

            <div className="payment-detail-list">
              <div>
                <span>Shop Name</span>
                <strong>{shopName || "—"}</strong>
              </div>

              <div>
                <span>Loan Number</span>
                <strong>{selectedPayment.loan_number}</strong>
              </div>

              <div>
                <span>Customer</span>
                <strong>
                  {getCustomerName(getLoan(selectedPayment.loan_id))}
                </strong>
              </div>

              <div>
                <span>Payment Date</span>
                <strong>{formatDate(selectedPayment.payment_date)}</strong>
              </div>

              <div>
                <span>Payment Type</span>
                <strong>{selectedPayment.payment_type}</strong>
              </div>

              <div>
                <span>Interest Amount</span>
                <strong>
                  {formatCurrency(selectedPayment.interest_amount)}
                </strong>
              </div>

              <div>
                <span>Principal Amount</span>
                <strong>
                  {formatCurrency(selectedPayment.principal_amount)}
                </strong>
              </div>

              <div>
                <span>Total Amount</span>
                <strong>{formatCurrency(selectedPayment.amount)}</strong>
              </div>

              <div>
                <span>Notes</span>
                <strong>{selectedPayment.notes || "—"}</strong>
              </div>
            </div>

            <div style={{ display: "grid", gap: "10px" }}>
              <button
                type="button"
                className="payment-save-button payment-detail-download"
                onClick={() => printReceipt(selectedPayment)}
                disabled={printingId === selectedPayment.id}
              >
                <Printer size={16} />
                {printingId === selectedPayment.id
                  ? "Opening Print..."
                  : "Print Receipt"}
              </button>

              <button
                type="button"
                className="payment-save-button payment-detail-download"
                onClick={() => downloadReceipt(selectedPayment)}
                disabled={downloadingId === selectedPayment.id}
              >
                <Download size={16} />
                {downloadingId === selectedPayment.id
                  ? "Downloading..."
                  : "Download Receipt"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Payments;
