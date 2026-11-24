
import { useCallback, useEffect, useState } from "react";
import {
  Settings as SettingsIcon,
  Percent,
  CalendarDays,
  Save,
  RefreshCw,
  AlertCircle,
  CheckCircle,
} from "lucide-react";

import api from "../services/api";
import "./Settings.css";

function Settings({ shopId }) {
  const [settings, setSettings] = useState({
    monthly_interest_rate: "",
    charge_full_month_for_partial: true,
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const fetchSettings = useCallback(async () => {
    if (!shopId) {
      setLoading(false);
      return;
    }

    try {
      const response = await api.get(
        `shops/${shopId}/settings/`
      );

      setSettings({
        monthly_interest_rate:
          response.data.monthly_interest_rate ?? "",
        charge_full_month_for_partial:
          Boolean(response.data.charge_full_month_for_partial),
      });

      setError("");
    } catch (err) {
      console.error("Settings loading error:", err);
      setError(
        err.response?.data?.detail ||
          "Unable to load shop settings."
      );
    } finally {
      setLoading(false);
    }
  }, [shopId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchSettings();
  }, [fetchSettings]);

  const handleChange = (event) => {
    const { name, value, type, checked } = event.target;

    setSettings((previous) => ({
      ...previous,
      [name]: type === "checkbox" ? checked : value,
    }));

    setSuccess("");
    setError("");
  };

  const handleReload = () => {
    setLoading(true);
    fetchSettings();
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    const rate = Number(settings.monthly_interest_rate);

    if (
      settings.monthly_interest_rate === "" ||
      !Number.isFinite(rate) ||
      rate <= 0
    ) {
      setError("Please enter a valid monthly interest rate.");
      return;
    }

    try {
      setSaving(true);
      setError("");
      setSuccess("");

      const payload = {
        monthly_interest_rate: String(
          settings.monthly_interest_rate
        ),
        charge_full_month_for_partial:
          settings.charge_full_month_for_partial,
      };

      const response = await api.patch(
        `shops/${shopId}/settings/`,
        payload
      );

      setSettings({
        monthly_interest_rate:
          response.data.monthly_interest_rate ??
          payload.monthly_interest_rate,
        charge_full_month_for_partial:
          response.data.charge_full_month_for_partial ??
          payload.charge_full_month_for_partial,
      });

      setSuccess("Shop settings updated successfully.");
    } catch (err) {
      console.error("Settings update error:", err);

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
          : "Unable to update settings. Please try again.";

      setError(message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="settings-loading">
        <RefreshCw size={20} className="settings-spin" />
        <span>Loading shop settings...</span>
      </div>
    );
  }

  return (
    <div className="settings-page">
      <div className="settings-heading">
        <div>
          <span className="settings-eyebrow">
            BUSINESS CONFIGURATION
          </span>
          <h1>Settings</h1>
          <p>Manage your shop interest rules and preferences.</p>
        </div>

        <div className="settings-heading-icon">
          <SettingsIcon size={24} />
        </div>
      </div>

      {error && (
        <div className="settings-message settings-error">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="settings-message settings-success">
          <CheckCircle size={18} />
          <span>{success}</span>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <section className="settings-card">
          <div className="settings-card-heading">
            <div className="settings-card-icon">
              <Percent size={21} />
            </div>
            <div>
              <h2>Interest Configuration</h2>
              <p>Set the monthly interest rate for this shop.</p>
            </div>
          </div>

          <div className="settings-form-field">
            <label htmlFor="monthly_interest_rate">
              Monthly Interest Rate (%)
            </label>

            <div className="settings-input-wrapper">
              <input
                id="monthly_interest_rate"
                type="number"
                name="monthly_interest_rate"
                min="0.01"
                max="100"
                step="0.01"
                value={settings.monthly_interest_rate}
                onChange={handleChange}
                placeholder="Enter monthly interest rate"
                required
              />
              <span>% / month</span>
            </div>

            <small>
              Used by the backend interest calculation logic.
            </small>
          </div>
        </section>

        <section className="settings-card">
          <div className="settings-card-heading">
            <div className="settings-card-icon calendar-icon">
              <CalendarDays size={21} />
            </div>
            <div>
              <h2>Partial Month Interest Rule</h2>
              <p>Configure how incomplete months are handled.</p>
            </div>
          </div>

          <label className="settings-toggle-row">
            <div>
              <strong>
                Charge full month for partial months
              </strong>
              <p>
                When enabled, an incomplete month is charged as
                a full month according to the backend rule.
              </p>
            </div>

            <input
              type="checkbox"
              name="charge_full_month_for_partial"
              checked={settings.charge_full_month_for_partial}
              onChange={handleChange}
            />

            <span className="settings-toggle" />
          </label>

          <div className="settings-rule-status">
            <span
              className={
                settings.charge_full_month_for_partial
                  ? "rule-enabled"
                  : "rule-disabled"
              }
            >
              {settings.charge_full_month_for_partial
                ? "Full month charging enabled"
                : "Full month charging disabled"}
            </span>
          </div>
        </section>

        <div className="settings-footer">
          <button
            type="button"
            className="settings-reset-button"
            onClick={handleReload}
            disabled={saving}
          >
            <RefreshCw size={16} />
            Reload Settings
          </button>

          <button
            type="submit"
            className="settings-save-button"
            disabled={saving}
          >
            <Save size={17} />
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </form>
    </div>
  );
}

export default Settings;
