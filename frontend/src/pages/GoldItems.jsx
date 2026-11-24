
import { useEffect, useState } from "react";
import {
  Gem,
  Search,
  Plus,
  RefreshCw,
  Eye,
  X,
  Scale,
} from "lucide-react";

import api from "../services/api";
import "./GoldItems.css";

const emptyForm = {
  loan: "",
  item_type: "",
  description: "",
  gross_weight: "",
  net_weight: "",
  purity: "22K",
};

const getList = (data) => {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  if (Array.isArray(data?.gold_items)) return data.gold_items;
  return [];
};

function GoldItems({ shopId }) {
  const [loans, setLoans] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [goldItems, setGoldItems] = useState([]);

  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);
  const [error, setError] = useState("");

  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [selectedItem, setSelectedItem] = useState(null);

  // Load loans, customers and their gold items
  useEffect(() => {
    let cancelled = false;

    const fetchData = async () => {
      try {
        setError("");

        const [loanResponse, customerResponse] = await Promise.all([
          api.get(`shops/${shopId}/loans/`),
          api.get(`shops/${shopId}/customers/`),
        ]);

        const loanList = getList(loanResponse.data);
        const customerList = getList(customerResponse.data);

        if (cancelled) return;

        setLoans(loanList);
        setCustomers(customerList);

        const itemResponses = await Promise.all(
          loanList.map(async (loan) => {
            try {
              const response = await api.get(
                `shops/${shopId}/loans/${loan.id}/gold-items/`
              );

              return getList(response.data).map((item) => ({
                ...item,
                loan_id: loan.id,
              }));
            } catch (err) {
              console.error(
                `Gold item loading error for loan ${loan.id}:`,
                err
              );
              throw err;
            }
          })
        );

        if (!cancelled) {
          setGoldItems(itemResponses.flat());
        }
      } catch (err) {
        console.error("Gold items API error:", err);

        if (!cancelled) {
          setError("Unable to load gold items. Please try again.");
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

    return (
      customer?.full_name ||
      customer?.name ||
      "Customer"
    );
  };

  const getLoanNumber = (loanId) => {
    const loan = getLoan(loanId);
    return loan?.loan_number || `Loan #${loanId}`;
  };

  const formatWeight = (value) =>
    `${Number(value || 0).toFixed(3)} g`;

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

  const handleChange = (event) => {
    const { name, value } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }));
  };

  // Add gold item
  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!form.loan) {
      setFormError("Please select a loan.");
      return;
    }

    const grossWeight = Number(form.gross_weight);
    const netWeight = Number(form.net_weight);

    if (
      !Number.isFinite(grossWeight) ||
      !Number.isFinite(netWeight) ||
      grossWeight <= 0 ||
      netWeight <= 0 ||
      netWeight > grossWeight
    ) {
      setFormError(
        "Enter valid weights. Net weight cannot exceed gross weight."
      );
      return;
    }

    try {
      setSaving(true);
      setFormError("");

      const payload = {
        item_type: form.item_type.trim(),
        description: form.description.trim(),
        gross_weight: form.gross_weight,
        net_weight: form.net_weight,
        purity: form.purity,
      };

      await api.post(
        `shops/${shopId}/loans/${form.loan}/gold-items/`,
        payload
      );

      closeForm();
      setSuccessMessage("Gold item added successfully.");
      refreshData();
    } catch (err) {
      console.error("Create gold item error:", err);

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
          : "Unable to add gold item. Please check the details.";

      setFormError(message);
    } finally {
      setSaving(false);
    }
  };

  const filteredItems = goldItems.filter((item) => {
    const loanId = item.loan_id ?? item.loan;
    const customerName = getCustomerName(getLoan(loanId));

    const searchableText = [
      item.item_type,
      item.description,
      item.purity,
      getLoanNumber(loanId),
      customerName,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();

    return searchableText.includes(search.toLowerCase());
  });

  const totalGrossWeight = goldItems.reduce(
    (total, item) => total + Number(item.gross_weight || 0),
    0
  );

  const totalNetWeight = goldItems.reduce(
    (total, item) => total + Number(item.net_weight || 0),
    0
  );

  return (
    <div className="gold-page">
      <div className="gold-heading">
        <div>
          <span className="gold-eyebrow">GOLD MANAGEMENT</span>
          <h1>Gold Items</h1>
          <p>Manage pledged gold items linked to customer loans.</p>
        </div>

        <button
          className="gold-add-button"
          type="button"
          onClick={openAddForm}
          disabled={loans.length === 0}
        >
          <Plus size={18} />
          Add Gold Item
        </button>
      </div>

      {/* Summary cards */}
      <div className="gold-summary">
        <div className="gold-summary-card">
          <div className="gold-summary-icon">
            <Gem size={22} />
          </div>
          <div>
            <span>Total Gold Items</span>
            <h2>{loading ? "..." : goldItems.length}</h2>
          </div>
        </div>

        <div className="gold-summary-card">
          <div className="gold-summary-icon gold-weight-icon">
            <Scale size={22} />
          </div>
          <div>
            <span>Total Gross Weight</span>
            <h2>{loading ? "..." : formatWeight(totalGrossWeight)}</h2>
          </div>
        </div>

        <div className="gold-summary-card">
          <div className="gold-summary-icon gold-net-icon">
            <Scale size={22} />
          </div>
          <div>
            <span>Total Net Weight</span>
            <h2>{loading ? "..." : formatWeight(totalNetWeight)}</h2>
          </div>
        </div>
      </div>

      {/* Search and refresh */}
      <div className="gold-toolbar">
        <div className="gold-search">
          <Search size={18} />
          <input
            type="text"
            placeholder="Search item, loan number or customer..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>

        <button
          className="gold-refresh-button"
          type="button"
          onClick={refreshData}
          disabled={loading}
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      {successMessage && (
        <div className="gold-success">
          {successMessage}
          <button
            type="button"
            onClick={() => setSuccessMessage("")}
            aria-label="Dismiss success message"
          >
            <X size={15} />
          </button>
        </div>
      )}

      {error && (
        <div className="gold-error">
          {error}
          <button type="button" onClick={refreshData}>
            Try Again
          </button>
        </div>
      )}

      {/* Gold items table */}
      {loading ? (
        <div className="gold-empty">Loading gold items...</div>
      ) : !error && filteredItems.length === 0 ? (
        <div className="gold-empty">
          <Gem size={38} />
          <h3>No gold items found</h3>
          <p>
            {search
              ? "Try another search term."
              : "Add gold items to your existing loans."}
          </p>
        </div>
      ) : !error ? (
        <div className="gold-table-wrapper">
          <table className="gold-table">
            <thead>
              <tr>
                <th>Item Type</th>
                <th>Loan Number</th>
                <th>Customer</th>
                <th>Gross Weight</th>
                <th>Net Weight</th>
                <th>Purity</th>
                <th>Details</th>
              </tr>
            </thead>

            <tbody>
              {filteredItems.map((item) => {
                const loanId = item.loan_id ?? item.loan;
                const loan = getLoan(loanId);

                return (
                  <tr key={item.id}>
                    <td>
                      <div className="gold-item-name">
                        <div className="gold-item-avatar">
                          <Gem size={17} />
                        </div>
                        <strong>{item.item_type}</strong>
                      </div>
                    </td>

                    <td>{getLoanNumber(loanId)}</td>
                    <td>{getCustomerName(loan)}</td>
                    <td>{formatWeight(item.gross_weight)}</td>
                    <td>{formatWeight(item.net_weight)}</td>

                    <td>
                      <span className="gold-purity">
                        {item.purity}
                      </span>
                    </td>

                    <td>
                      <button
                        type="button"
                        className="gold-view-button"
                        title="View details"
                        onClick={() => setSelectedItem(item)}
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

      {/* Add gold item modal */}
      {showForm && (
        <div
          className="gold-modal-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) closeForm();
          }}
        >
          <div
            className="gold-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="gold-modal-title"
          >
            <div className="gold-modal-heading">
              <div>
                <span className="gold-eyebrow">GOLD DETAILS</span>
                <h2 id="gold-modal-title">Add Gold Item</h2>
              </div>

              <button
                type="button"
                className="gold-modal-close"
                onClick={closeForm}
                aria-label="Close"
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="gold-form-grid">
                <label className="gold-form-full">
                  Select Loan *
                  <select
                    name="loan"
                    value={form.loan}
                    onChange={handleChange}
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

                <label>
                  Item Type *
                  <input
                    name="item_type"
                    value={form.item_type}
                    onChange={handleChange}
                    placeholder="Example: Gold Chain"
                    required
                  />
                </label>

                <label>
                  Purity *
                  <select
                    name="purity"
                    value={form.purity}
                    onChange={handleChange}
                    required
                  >
                    <option value="22K">22K</option>
                    <option value="24K">24K</option>
                    <option value="20K">20K</option>
                    <option value="18K">18K</option>
                    <option value="14K">14K</option>
                  </select>
                </label>

                <label>
                  Gross Weight (g) *
                  <input
                    name="gross_weight"
                    type="number"
                    min="0.001"
                    step="0.001"
                    value={form.gross_weight}
                    onChange={handleChange}
                    placeholder="15.500"
                    required
                  />
                </label>

                <label>
                  Net Weight (g) *
                  <input
                    name="net_weight"
                    type="number"
                    min="0.001"
                    step="0.001"
                    value={form.net_weight}
                    onChange={handleChange}
                    placeholder="14.800"
                    required
                  />
                </label>

                <label className="gold-form-full">
                  Description
                  <textarea
                    name="description"
                    value={form.description}
                    onChange={handleChange}
                    placeholder="Enter gold item description"
                    rows={3}
                  />
                </label>
              </div>

              {formError && (
                <div className="gold-form-error">
                  {formError}
                </div>
              )}

              <div className="gold-form-actions">
                <button
                  type="button"
                  className="gold-cancel-button"
                  onClick={closeForm}
                  disabled={saving}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="gold-save-button"
                  disabled={saving || loans.length === 0}
                >
                  {saving ? "Saving..." : "Save Gold Item"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* View details modal */}
      {selectedItem && (
        <div
          className="gold-modal-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setSelectedItem(null);
            }
          }}
        >
          <div className="gold-modal gold-details-modal">
            <div className="gold-modal-heading">
              <div>
                <span className="gold-eyebrow">ITEM INFORMATION</span>
                <h2>{selectedItem.item_type}</h2>
              </div>

              <button
                type="button"
                className="gold-modal-close"
                onClick={() => setSelectedItem(null)}
                aria-label="Close"
              >
                <X size={20} />
              </button>
            </div>

            <div className="gold-detail-list">
              <div>
                <span>Loan Number</span>
                <strong>
                  {getLoanNumber(
                    selectedItem.loan_id ?? selectedItem.loan
                  )}
                </strong>
              </div>

              <div>
                <span>Customer</span>
                <strong>
                  {getCustomerName(
                    getLoan(selectedItem.loan_id ?? selectedItem.loan)
                  )}
                </strong>
              </div>

              <div>
                <span>Description</span>
                <strong>{selectedItem.description || "—"}</strong>
              </div>

              <div>
                <span>Gross Weight</span>
                <strong>{formatWeight(selectedItem.gross_weight)}</strong>
              </div>

              <div>
                <span>Net Weight</span>
                <strong>{formatWeight(selectedItem.net_weight)}</strong>
              </div>

              <div>
                <span>Purity</span>
                <strong>{selectedItem.purity}</strong>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default GoldItems;
