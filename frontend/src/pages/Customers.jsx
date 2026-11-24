
import { useEffect, useState } from "react";
import {
  Users,
  Search,
  Plus,
  RefreshCw,
  Pencil,
  UserCheck,
  UserX,
  X,
  Phone,
  MapPin,
} from "lucide-react";

import api from "../services/api";
import "./Customers.css";

const emptyForm = {
  customer_number: "",
  full_name: "",
  phone_number: "",
  address: "",
  id_proof_type: "",
  id_proof_number: "",
};

function Customers({ shopId }) {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  const [showForm, setShowForm] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Fetch customers
  useEffect(() => {
    let cancelled = false;

    const loadCustomers = async () => {
      if (!shopId) {
        setLoading(false);
        return;
      }

      try {
        const response = await api.get(
          `shops/${shopId}/customers/`
        );

        if (!cancelled) {
          setCustomers(
            Array.isArray(response.data) ? response.data : []
          );
          setError("");
        }
      } catch (err) {
        console.error("Customers API error:", err);

        if (!cancelled) {
          setError("Unable to load customers. Please try again.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadCustomers();

    return () => {
      cancelled = true;
    };
  }, [shopId]);

  // Refresh customers
  const fetchCustomers = async () => {
    if (!shopId) return;

    try {
      setError("");

      const response = await api.get(
        `shops/${shopId}/customers/`
      );

      setCustomers(
        Array.isArray(response.data) ? response.data : []
      );
    } catch (err) {
      console.error("Customers API error:", err);
      setError("Unable to load customers. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    setLoading(true);
    fetchCustomers();
  };

  // Generate next customer ID
  const generateCustomerNumber = () => {
    const usedNumbers = customers
      .map((customer) => {
        const match = customer.customer_number?.match(/^CUS(\d+)$/i);
        return match ? Number(match[1]) : null;
      })
      .filter((number) => number !== null);

    let nextNumber = 1;

    while (usedNumbers.includes(nextNumber)) {
      nextNumber++;
    }

    return `CUS${String(nextNumber).padStart(3, "0")}`;
  };

  // Open add form
  const openAddForm = () => {
    setEditingCustomer(null);

    setForm({
      ...emptyForm,
      customer_number: generateCustomerNumber(),
    });

    setFormError("");
    setSuccessMessage("");
    setShowForm(true);
  };

  // Open edit form
  const openEditForm = (customer) => {
    setEditingCustomer(customer);

    setForm({
      customer_number: customer.customer_number || "",
      full_name: customer.full_name || "",
      phone_number: customer.phone_number || "",
      address: customer.address || "",
      id_proof_type: customer.id_proof_type || "",
      id_proof_number: customer.id_proof_number || "",
    });

    setFormError("");
    setSuccessMessage("");
    setShowForm(true);
  };

  // Close form
  const closeForm = () => {
    setShowForm(false);
    setEditingCustomer(null);
    setForm(emptyForm);
    setFormError("");
  };

  // Handle form changes
  const handleChange = (event) => {
    const { name, value } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }));
  };

  // Add or update customer
  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!shopId) {
      setFormError("Please select a shop first.");
      return;
    }

    try {
      setSaving(true);
      setFormError("");
      setSuccessMessage("");

      const payload = {
        customer_number: form.customer_number.trim(),
        full_name: form.full_name.trim(),
        phone_number: form.phone_number.trim(),
        address: form.address.trim(),
        id_proof_type: form.id_proof_type.trim(),
        id_proof_number: form.id_proof_number.trim(),
      };

      if (editingCustomer) {
        await api.patch(
          `shops/${shopId}/customers/${editingCustomer.id}/`,
          payload
        );
      } else {
        await api.post(
          `shops/${shopId}/customers/`,
          payload
        );
      }

      await fetchCustomers();

      setSuccessMessage(
        editingCustomer
          ? "Customer updated successfully."
          : "Customer added successfully."
      );

      closeForm();
    } catch (err) {
      console.error("Customer save error:", err);

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
          : "Unable to save customer. Please check the details.";

      setFormError(message);
    } finally {
      setSaving(false);
    }
  };

  // Activate or deactivate customer
  const handleStatusChange = async (customer) => {
    const nextStatus = !customer.is_active;

    const confirmed = window.confirm(
      `Are you sure you want to ${
        nextStatus ? "activate" : "deactivate"
      } ${customer.full_name}?`
    );

    if (!confirmed) return;

    try {
      await api.patch(
        `shops/${shopId}/customers/${customer.id}/status/`,
        { is_active: nextStatus }
      );

      setCustomers((previous) =>
        previous.map((item) =>
          item.id === customer.id
            ? { ...item, is_active: nextStatus }
            : item
        )
      );

      setSuccessMessage(
        `Customer ${nextStatus ? "activated" : "deactivated"} successfully.`
      );
    } catch (err) {
      console.error("Customer status error:", err);
      setError("Unable to update customer status.");
    }
  };

  // Search customers
  const filteredCustomers = customers.filter((customer) =>
    [
      customer.customer_number,
      customer.full_name,
      customer.phone_number,
      customer.id_proof_number,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase()
      .includes(search.toLowerCase())
  );

  const activeCount = customers.filter(
    (customer) => customer.is_active
  ).length;

  const inactiveCount = customers.length - activeCount;

  return (
    <div className="customers-page">
      <div className="customers-heading">
        <div>
          <span className="customers-eyebrow">
            CUSTOMER MANAGEMENT
          </span>

          <h1>Customers</h1>

          <p>Manage your pawn shop customer records.</p>
        </div>

        <button
          className="customers-add-button"
          onClick={openAddForm}
          type="button"
          disabled={!shopId}
        >
          <Plus size={18} />
          Add Customer
        </button>
      </div>

      {/* Customer summary */}
      <div className="customers-summary">
        <div className="customer-summary-card">
          <div className="customer-summary-icon">
            <Users size={22} />
          </div>

          <div>
            <span>Total Customers</span>
            <h2>{loading ? "..." : customers.length}</h2>
          </div>
        </div>

        <div className="customer-summary-card">
          <div className="customer-summary-icon active-summary-icon">
            <UserCheck size={22} />
          </div>

          <div>
            <span>Active Customers</span>
            <h2>{loading ? "..." : activeCount}</h2>
          </div>
        </div>

        <div className="customer-summary-card">
          <div className="customer-summary-icon inactive-summary-icon">
            <UserX size={22} />
          </div>

          <div>
            <span>Inactive Customers</span>
            <h2>{loading ? "..." : inactiveCount}</h2>
          </div>
        </div>
      </div>

      {/* Search and refresh */}
      <div className="customers-toolbar">
        <div className="customers-search">
          <Search size={18} />

          <input
            type="text"
            placeholder="Search name, customer number or phone..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>

        <button
          className="customers-refresh-button"
          onClick={handleRefresh}
          type="button"
          disabled={loading}
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      {/* Success message */}
      {successMessage && (
        <div className="customers-success">
          {successMessage}

          <button
            type="button"
            onClick={() => setSuccessMessage("")}
            aria-label="Dismiss message"
          >
            <X size={15} />
          </button>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="customers-error">
          {error}

          <button
            type="button"
            onClick={handleRefresh}
          >
            Try Again
          </button>
        </div>
      )}

      {/* Customer list */}
      {loading ? (
        <div className="customers-empty">
          Loading customers...
        </div>
      ) : !error && filteredCustomers.length === 0 ? (
        <div className="customers-empty">
          <Users size={36} />

          <h3>No customers found</h3>

          <p>
            {search
              ? "Try another search term."
              : "Add your first customer to get started."}
          </p>
        </div>
      ) : !error ? (
        <div className="customers-table-wrapper">
          <table className="customers-table">
            <thead>
              <tr>
                <th>Customer</th>
                <th>Customer No.</th>
                <th>Phone Number</th>
                <th>Address</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>

            <tbody>
              {filteredCustomers.map((customer) => (
                <tr key={customer.id}>
                  <td>
                    <div className="customer-name-cell">
                      <div className="customer-avatar">
                        {(customer.full_name || "?")
                          .charAt(0)
                          .toUpperCase()}
                      </div>

                      <div>
                        <strong>{customer.full_name}</strong>
                        <span>ID #{customer.id}</span>
                      </div>
                    </div>
                  </td>

                  <td>{customer.customer_number || "—"}</td>

                  <td>
                    <span className="customer-phone">
                      <Phone size={14} />
                      {customer.phone_number || "—"}
                    </span>
                  </td>

                  <td>
                    <span className="customer-address">
                      <MapPin size={14} />
                      {customer.address || "—"}
                    </span>
                  </td>

                  <td>
                    <span
                      className={`customer-status ${
                        customer.is_active
                          ? "customer-active"
                          : "customer-inactive"
                      }`}
                    >
                      {customer.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>

                  <td>
                    <div className="customer-actions">
                      <button
                        type="button"
                        className="customer-edit-button"
                        title="Edit customer"
                        onClick={() => openEditForm(customer)}
                      >
                        <Pencil size={16} />
                      </button>

                      <button
                        type="button"
                        className="customer-status-button"
                        title={
                          customer.is_active
                            ? "Deactivate customer"
                            : "Activate customer"
                        }
                        onClick={() => handleStatusChange(customer)}
                      >
                        {customer.is_active ? (
                          <UserX size={16} />
                        ) : (
                          <UserCheck size={16} />
                        )}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {/* Add / Edit Customer Modal */}
      {showForm && (
        <div
          className="customer-modal-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closeForm();
            }
          }}
        >
          <div
            className="customer-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="customer-modal-title"
          >
            <div className="customer-modal-heading">
              <div>
                <span className="customers-eyebrow">
                  CUSTOMER DETAILS
                </span>

                <h2 id="customer-modal-title">
                  {editingCustomer
                    ? "Edit Customer"
                    : "Add New Customer"}
                </h2>
              </div>

              <button
                type="button"
                className="customer-modal-close"
                onClick={closeForm}
                aria-label="Close form"
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="customer-form-grid">
                <label>
                  Customer ID
                  <input
                    name="customer_number"
                    value={form.customer_number}
                    readOnly
                    required
                    placeholder="Auto generated"
                  />
                </label>

                <label>
                  Full Name *
                  <input
                    name="full_name"
                    value={form.full_name}
                    onChange={handleChange}
                    placeholder="Enter customer name"
                    required
                  />
                </label>

                <label>
                  Phone Number
                  <input
                    name="phone_number"
                    value={form.phone_number}
                    onChange={handleChange}
                    placeholder="Enter phone number"
                  />
                </label>

                <label>
                  ID Proof Type
                  <input
                    name="id_proof_type"
                    value={form.id_proof_type}
                    onChange={handleChange}
                    placeholder="Example: Aadhaar"
                  />
                </label>

                <label className="customer-form-full">
                  ID Proof Number
                  <input
                    name="id_proof_number"
                    value={form.id_proof_number}
                    onChange={handleChange}
                    placeholder="Enter ID proof number"
                  />
                </label>

                <label className="customer-form-full">
                  Address
                  <textarea
                    name="address"
                    value={form.address}
                    onChange={handleChange}
                    placeholder="Enter customer address"
                    rows={3}
                  />
                </label>
              </div>

              {formError && (
                <div className="customer-form-error">
                  {formError}
                </div>
              )}

              <div className="customer-form-actions">
                <button
                  type="button"
                  className="customer-cancel-button"
                  onClick={closeForm}
                  disabled={saving}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="customer-save-button"
                  disabled={saving}
                >
                  {saving
                    ? "Saving..."
                    : editingCustomer
                      ? "Update Customer"
                      : "Save Customer"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Customers;
