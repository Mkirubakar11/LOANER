
import { useCallback, useEffect, useState } from "react";
import {
  HandCoins,
  Search,
  Plus,
  RefreshCw,
  CalendarDays,
  UserRound,
  X,
  Eye,
} from "lucide-react";

import api from "../services/api";
import "./Loans.css";

const emptyForm = {
  customer: "",
  principal_amount: "",
  interest_rate: "",
  loan_date: new Date().toISOString().slice(0, 10),
  due_date: "",
};

function Loans({ shopId }) {
  const [loans, setLoans] = useState([]);
  const [customers, setCustomers] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const [selectedLoan, setSelectedLoan] = useState(null);

  const getList = (data) => {
    if (Array.isArray(data)) return data;
    if (Array.isArray(data?.results)) return data.results;
    if (Array.isArray(data?.loans)) return data.loans;
    return [];
  };

  // Load loans and customers
  const loadData = useCallback(async () => {
    if (!shopId) {
      setError("No shop selected.");
      setLoading(false);
      return;
    }

    try {
      setError("");

      const [loanResponse, customerResponse] = await Promise.all([
        api.get(`shops/${shopId}/loans/`),
        api.get(`shops/${shopId}/customers/`),
      ]);

      setLoans(getList(loanResponse.data));
      setCustomers(getList(customerResponse.data));
    } catch (err) {
      console.error("Loans loading error:", err);
      setError("Unable to load loans. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [shopId]);

  useEffect(() => {
    let cancelled = false;

    const fetchData = async () => {
      if (!shopId) {
        setLoading(false);
        return;
      }

      setLoading(true);

      try {
        const [loanResponse, customerResponse] = await Promise.all([
          api.get(`shops/${shopId}/loans/`),
          api.get(`shops/${shopId}/customers/`),
        ]);

        if (!cancelled) {
          setLoans(getList(loanResponse.data));
          setCustomers(getList(customerResponse.data));
          setError("");
        }
      } catch (err) {
        console.error("Loans loading error:", err);

        if (!cancelled) {
          setError("Unable to load loans. Please try again.");
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
  }, [shopId]);

  const handleRefresh = () => {
    setLoading(true);
    loadData();
  };

  const openAddForm = () => {
    setForm({
      ...emptyForm,
      loan_date: new Date().toISOString().slice(0, 10),
    });
    setFormError("");
    setShowForm(true);
  };

  const closeForm = () => {
    setShowForm(false);
    setForm(emptyForm);
    setFormError("");
  };

  const handleChange = (event) => {
    const { name, value } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }));
  };

  // Create loan with automatic loan number
  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!shopId) {
      setFormError("Please select a shop first.");
      return;
    }

    try {
      setSaving(true);
      setFormError("");

      const payload = {
        customer: Number(form.customer),
        principal_amount: form.principal_amount,
        interest_rate: form.interest_rate,
        loan_date: form.loan_date,
        due_date: form.due_date,
      };

      const response = await api.post(
        `shops/${shopId}/loans/`,
        payload
      );

      const generatedNumber = response.data?.loan_number;

      closeForm();

      setSuccessMessage(
        generatedNumber
          ? `Loan ${generatedNumber} created successfully.`
          : "Loan created successfully."
      );

      setLoading(true);
      await loadData();
    } catch (err) {
      console.error("Create loan error:", err);

      const responseData = err.response?.data;

      const message =
        responseData && typeof responseData === "object"
          ? Object.entries(responseData)
              .map(([key, value]) => {
                const detail = Array.isArray(value)
                  ? value.join(", ")
                  : String(value);

                return `${key}: ${detail}`;
              })
              .join(" | ")
          : "Unable to create loan. Please check the details.";

      setFormError(message);
    } finally {
      setSaving(false);
    }
  };

  const formatCurrency = (amount) =>
    new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(Number(amount || 0));

  const getCustomerName = (loan) => {
    if (typeof loan.customer === "object" && loan.customer !== null) {
      return (
        loan.customer.full_name ||
        loan.customer.name ||
        `Customer #${loan.customer.id}`
      );
    }

    const customer = customers.find(
      (item) => String(item.id) === String(loan.customer)
    );

    return customer?.full_name || `Customer #${loan.customer}`;
  };

  const getStatus = (loan) => {
    const status = String(loan.status || "ACTIVE").toUpperCase();

    if (status === "CLOSED") return "Closed";
    if (status === "OVERDUE") return "Overdue";

    return "Active";
  };

  const filteredLoans = loans.filter((loan) => {
    const customerName = getCustomerName(loan);

    return [
      loan.loan_number,
      customerName,
      loan.status,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase()
      .includes(search.toLowerCase());
  });

  const activeCount = loans.filter(
    (loan) => getStatus(loan) === "Active"
  ).length;

  const closedCount = loans.filter(
    (loan) => getStatus(loan) === "Closed"
  ).length;

  const overdueCount = loans.filter(
    (loan) => getStatus(loan) === "Overdue"
  ).length;

  const totalPrincipal = loans.reduce(
    (total, loan) =>
      total + Number(loan.principal_amount || 0),
    0
  );

  return (
    <div className="loans-page">
      <div className="loans-heading">
        <div>
          <span className="loans-eyebrow">LOAN MANAGEMENT</span>
          <h1>Loans</h1>
          <p>Manage customer loans and track outstanding amounts.</p>
        </div>

        <button
          className="loans-add-button"
          onClick={openAddForm}
          type="button"
          disabled={!shopId}
        >
          <Plus size={18} />
          New Loan
        </button>
      </div>

      {/* Loan summary */}
      <div className="loans-summary">
        <div className="loan-summary-card">
          <div className="loan-summary-icon">
            <HandCoins size={22} />
          </div>
          <div>
            <span>Total Loan Principal</span>
            <h2>{loading ? "..." : formatCurrency(totalPrincipal)}</h2>
          </div>
        </div>

        <div className="loan-summary-card">
          <div className="loan-summary-icon loan-active-icon">
            <HandCoins size={22} />
          </div>
          <div>
            <span>Active Loans</span>
            <h2>{loading ? "..." : activeCount}</h2>
          </div>
        </div>

        <div className="loan-summary-card">
          <div className="loan-summary-icon loan-closed-icon">
            <CalendarDays size={22} />
          </div>
          <div>
            <span>Closed Loans</span>
            <h2>{loading ? "..." : closedCount}</h2>
          </div>
        </div>

        <div className="loan-summary-card">
          <div className="loan-summary-icon loan-overdue-icon">
            <CalendarDays size={22} />
          </div>
          <div>
            <span>Overdue Loans</span>
            <h2>{loading ? "..." : overdueCount}</h2>
          </div>
        </div>
      </div>

      {/* Search and refresh */}
      <div className="loans-toolbar">
        <div className="loans-search">
          <Search size={18} />
          <input
            type="text"
            placeholder="Search loan number or customer..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>

        <button
          className="loans-refresh-button"
          onClick={handleRefresh}
          type="button"
          disabled={loading}
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      {successMessage && (
        <div className="loans-success">
          {successMessage}
          <button
            type="button"
            onClick={() => setSuccessMessage("")}
          >
            <X size={15} />
          </button>
        </div>
      )}

      {error && (
        <div className="loans-error">
          {error}
          <button type="button" onClick={handleRefresh}>
            Try Again
          </button>
        </div>
      )}

      {/* Loans table */}
      {loading ? (
        <div className="loans-empty">Loading loans...</div>
      ) : !error && filteredLoans.length === 0 ? (
        <div className="loans-empty">
          <HandCoins size={36} />
          <h3>No loans found</h3>
          <p>
            {search
              ? "Try another search term."
              : "Create your first loan to get started."}
          </p>
        </div>
      ) : !error ? (
        <div className="loans-table-wrapper">
          <table className="loans-table">
            <thead>
              <tr>
                <th>Loan Number</th>
                <th>Customer</th>
                <th>Principal Amount</th>
                <th>Interest Rate</th>
                <th>Loan Date</th>
                <th>Due Date</th>
                <th>Status</th>
                <th>Details</th>
              </tr>
            </thead>

            <tbody>
              {filteredLoans.map((loan) => {
                const status = getStatus(loan);

                return (
                  <tr key={loan.id}>
                    <td>
                      <strong className="loan-number">
                        {loan.loan_number || `Loan #${loan.id}`}
                      </strong>
                    </td>

                    <td>
                      <span className="loan-customer">
                        <UserRound size={15} />
                        {getCustomerName(loan)}
                      </span>
                    </td>

                    <td className="loan-amount">
                      {formatCurrency(loan.principal_amount)}
                    </td>

                    <td>{loan.interest_rate}%</td>

                    <td>{loan.loan_date || "—"}</td>

                    <td>{loan.due_date || "—"}</td>

                    <td>
                      <span
                        className={`loan-status loan-status-${status.toLowerCase()}`}
                      >
                        {status}
                      </span>
                    </td>

                    <td>
                      <button
                        className="loan-view-button"
                        type="button"
                        title="View loan details"
                        onClick={() => setSelectedLoan(loan)}
                      >
                        <Eye size={16} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}

      {/* Add Loan modal */}
      {showForm && (
        <div
          className="loan-modal-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closeForm();
            }
          }}
        >
          <div
            className="loan-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="loan-modal-title"
          >
            <div className="loan-modal-heading">
              <div>
                <span className="loans-eyebrow">LOAN DETAILS</span>
                <h2 id="loan-modal-title">Create New Loan</h2>
              </div>

              <button
                className="loan-modal-close"
                type="button"
                onClick={closeForm}
                aria-label="Close"
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="loan-form-grid">
                <label className="loan-form-full">
                  Select Customer *
                  <select
                    name="customer"
                    value={form.customer}
                    onChange={handleChange}
                    required
                  >
                    <option value="">Choose a customer</option>
                    {customers
                      .filter((customer) => customer.is_active)
                      .map((customer) => (
                        <option
                          key={customer.id}
                          value={customer.id}
                        >
                          {customer.full_name} - {customer.customer_number}
                        </option>
                      ))}
                  </select>
                </label>

                <div className="loan-form-full loan-auto-number-note">
                  Loan Number will be generated automatically for this shop.
                </div>

                <label>
                  Principal Amount (₹) *
                  <input
                    name="principal_amount"
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={form.principal_amount}
                    onChange={handleChange}
                    placeholder="Enter amount"
                    required
                  />
                </label>

                <label>
                  Interest Rate (%) *
                  <input
                    name="interest_rate"
                    type="number"
                    min="0"
                    step="0.01"
                    value={form.interest_rate}
                    onChange={handleChange}
                    placeholder="Example: 2"
                    required
                  />
                </label>

                <label>
                  Loan Date *
                  <input
                    name="loan_date"
                    type="date"
                    value={form.loan_date}
                    onChange={handleChange}
                    required
                  />
                </label>

                <label className="loan-form-full">
                  Due Date *
                  <input
                    name="due_date"
                    type="date"
                    min={form.loan_date}
                    value={form.due_date}
                    onChange={handleChange}
                    required
                  />
                </label>
              </div>

              {formError && (
                <div className="loan-form-error">
                  {formError}
                </div>
              )}

              <div className="loan-form-actions">
                <button
                  className="loan-cancel-button"
                  type="button"
                  onClick={closeForm}
                  disabled={saving}
                >
                  Cancel
                </button>

                <button
                  className="loan-save-button"
                  type="submit"
                  disabled={saving || customers.length === 0}
                >
                  {saving ? "Saving..." : "Create Loan"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Loan details modal */}
      {selectedLoan && (
        <div
          className="loan-modal-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setSelectedLoan(null);
            }
          }}
        >
          <div className="loan-modal loan-details-modal">
            <div className="loan-modal-heading">
              <div>
                <span className="loans-eyebrow">LOAN INFORMATION</span>
                <h2>
                  {selectedLoan.loan_number || `Loan #${selectedLoan.id}`}
                </h2>
              </div>

              <button
                className="loan-modal-close"
                type="button"
                onClick={() => setSelectedLoan(null)}
                aria-label="Close"
              >
                <X size={20} />
              </button>
            </div>

            <div className="loan-detail-list">
              <div>
                <span>Customer</span>
                <strong>{getCustomerName(selectedLoan)}</strong>
              </div>

              <div>
                <span>Principal Amount</span>
                <strong>
                  {formatCurrency(selectedLoan.principal_amount)}
                </strong>
              </div>

              <div>
                <span>Interest Rate</span>
                <strong>{selectedLoan.interest_rate}%</strong>
              </div>

              <div>
                <span>Loan Date</span>
                <strong>{selectedLoan.loan_date || "—"}</strong>
              </div>

              <div>
                <span>Due Date</span>
                <strong>{selectedLoan.due_date || "—"}</strong>
              </div>

              <div>
                <span>Status</span>
                <strong>{getStatus(selectedLoan)}</strong>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Loans;
