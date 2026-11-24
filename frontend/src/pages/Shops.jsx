
import { useEffect, useState } from "react";
import {
  Store,
  MapPin,
  Plus,
  RefreshCw,
  Search,
  X,
} from "lucide-react";

import api from "../services/api";
import "./Shops.css";

const emptyForm = {
  name: "",
  address: "",
  phone_number: "",
};

function Shops() {
  const [shops, setShops] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");
  const [success, setSuccess] = useState("");

  // Initial shop loading
  useEffect(() => {
    let cancelled = false;

    api
      .get("shops/")
      .then((response) => {
        if (!cancelled) {
          setShops(response.data);
        }
      })
      .catch((err) => {
        console.error("Shops API error:", err);

        if (!cancelled) {
          setError("Unable to load shops. Please try again.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Refresh shops
  const handleRefresh = async () => {
    try {
      setLoading(true);
      setError("");
      setSuccess("");

      const response = await api.get("shops/");
      setShops(response.data);
    } catch (err) {
      console.error("Shops API error:", err);
      setError("Unable to load shops. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // Handle form fields
  const handleInputChange = (event) => {
    const { name, value } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }));
  };

  // Open Add Shop modal
  const openAddModal = () => {
    setForm(emptyForm);
    setFormError("");
    setSuccess("");
    setShowModal(true);
  };

  // Create new shop
  const handleCreateShop = async (event) => {
    event.preventDefault();

    setFormError("");
    setSuccess("");

    if (!form.name.trim()) {
      setFormError("Shop name is required.");
      return;
    }

    try {
      setSaving(true);

      const response = await api.post("shops/", {
        name: form.name.trim(),
        address: form.address.trim(),
        phone_number: form.phone_number.trim(),
      });

      setShops((previous) => [
        response.data,
        ...previous,
      ]);

      setForm(emptyForm);
      setShowModal(false);
      setSuccess("Shop created successfully.");
    } catch (err) {
      console.error("Create shop error:", err);

      const data = err.response?.data;

      if (data && typeof data === "object") {
        const firstError = Object.values(data).flat()[0];

        setFormError(
          typeof firstError === "string"
            ? firstError
            : "Unable to create shop. Please check your details."
        );
      } else {
        setFormError(
          "Unable to create shop. Please try again."
        );
      }
    } finally {
      setSaving(false);
    }
  };

  // Search shops
  const filteredShops = shops.filter((shop) =>
    [shop.name, shop.shop_code, shop.address]
      .filter(Boolean)
      .join(" ")
      .toLowerCase()
      .includes(search.toLowerCase())
  );

  return (
    <div className="shops-page">

      {/* PAGE HEADER */}
      <div className="shops-heading">
        <div>
          <span className="shops-eyebrow">
            BUSINESS MANAGEMENT
          </span>

          <h1>My Shops</h1>

          <p>
            Manage and monitor all your pawn shop locations.
          </p>
        </div>

        <button
          className="shops-refresh-button"
          onClick={handleRefresh}
          type="button"
          disabled={loading}
        >
          <RefreshCw size={17} />
          Refresh
        </button>
      </div>

      {/* SUCCESS MESSAGE */}
      {success && (
        <div className="shops-success">
          {success}
        </div>
      )}

      {/* SHOP OVERVIEW */}
      <div className="shops-overview">
        <div className="shops-overview-icon">
          <Store size={23} />
        </div>

        <div>
          <span>Total Shops</span>
          <h2>{loading ? "..." : shops.length}</h2>
        </div>
      </div>

      {/* SEARCH AND ADD */}
      <div className="shops-toolbar">
        <div className="shops-search">
          <Search size={18} />

          <input
            type="text"
            placeholder="Search shop name, code or location..."
            value={search}
            onChange={(event) =>
              setSearch(event.target.value)
            }
          />
        </div>

        <button
          className="shops-add-button"
          type="button"
          onClick={openAddModal}
        >
          <Plus size={18} />
          Add Shop
        </button>
      </div>

      {/* SHOP CONTENT */}
      {loading ? (
        <div className="shops-message">
          Loading shops...
        </div>
      ) : error ? (
        <div className="shops-message shops-error">
          {error}

          <button
            onClick={handleRefresh}
            type="button"
          >
            Try Again
          </button>
        </div>
      ) : filteredShops.length === 0 ? (
        <div className="shops-empty">
          <Store size={35} />

          <h3>No shops found</h3>

          <p>
            {search
              ? "Try another search term."
              : "No shops are available in your account."}
          </p>
        </div>
      ) : (
        <div className="shops-grid">
          {filteredShops.map((shop) => (
            <div className="shop-card" key={shop.id}>
              <div className="shop-card-top">
                <div className="shop-card-icon">
                  <Store size={25} />
                </div>

                <span
                  className={`shop-status ${
                    shop.is_active
                      ? "shop-active"
                      : "shop-inactive"
                  }`}
                >
                  {shop.is_active ? "Active" : "Inactive"}
                </span>
              </div>

              <h3>{shop.name}</h3>

              <p className="shop-card-location">
                <MapPin size={15} />
                {shop.address || "Address not available"}
              </p>

              <div className="shop-card-divider" />

              <div className="shop-card-details">
                <div>
                  <span>Shop Code</span>
                  <strong>{shop.shop_code || "Generating..."}</strong>
                </div>

                <div>
                  <span>Shop ID</span>
                  <strong>#{shop.id}</strong>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ADD SHOP MODAL */}
      {showModal && (
        <div
          className="shop-modal-overlay"
          onMouseDown={(event) => {
            if (
              event.target === event.currentTarget &&
              !saving
            ) {
              setShowModal(false);
            }
          }}
        >
          <div
            className="shop-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="shop-modal-title"
          >
            <div className="shop-modal-header">
              <div>
                <span className="shops-eyebrow">
                  BUSINESS MANAGEMENT
                </span>

                <h2 id="shop-modal-title">
                  Add New Shop
                </h2>

                <p>
                  Enter your pawn shop details below.
                </p>
              </div>

              <button
                type="button"
                className="shop-modal-close"
                onClick={() => setShowModal(false)}
                disabled={saving}
                aria-label="Close"
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleCreateShop}>
              <div className="shop-form-grid">

                <div className="shop-form-group shop-form-full">
                  <label htmlFor="shop-name">
                    Shop Name *
                  </label>

                  <input
                    id="shop-name"
                    name="name"
                    value={form.name}
                    onChange={handleInputChange}
                    placeholder="Enter shop name"
                    required
                    maxLength={150}
                  />
                </div>

                <div className="shop-form-group shop-form-full">
                  <label htmlFor="shop-phone">
                    Phone Number
                  </label>

                  <input
                    id="shop-phone"
                    name="phone_number"
                    type="tel"
                    value={form.phone_number}
                    onChange={handleInputChange}
                    placeholder="Enter phone number"
                    maxLength={15}
                  />
                </div>

                <div className="shop-form-group shop-form-full">
                  <label htmlFor="shop-address">
                    Shop Address
                  </label>

                  <textarea
                    id="shop-address"
                    name="address"
                    value={form.address}
                    onChange={handleInputChange}
                    placeholder="Enter complete shop address"
                    rows={3}
                  />
                </div>

              </div>

              <p className="shops-auto-code-note">
                Shop Code will be generated automatically.
              </p>

              {formError && (
                <div className="shop-form-error">
                  {formError}
                </div>
              )}

              <div className="shop-form-actions">
                <button
                  type="button"
                  className="shop-cancel-button"
                  onClick={() => setShowModal(false)}
                  disabled={saving}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="shop-save-button"
                  disabled={saving}
                >
                  {saving ? "Creating..." : "Create Shop"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}

export default Shops;
