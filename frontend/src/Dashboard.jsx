
import { useEffect, useState } from "react";

import {
  LayoutDashboard,
  Store,
  Users,
  HandCoins,
  Gem,
  Receipt,
  Settings,
  Bell,
  Search,
  Wallet,
  CircleDollarSign,
  LogOut,
  Plus,
  CalendarDays,
  Moon,
  Sun,
} from "lucide-react";

import api from "./services/api";

import Shops from "./pages/Shops";
import Customers from "./pages/Customers";
import Loans from "./pages/Loans";
import GoldItems from "./pages/GoldItems";
import Payments from "./pages/Payments";
import SettingsPage from "./pages/Settings";

import "./Dashboard.css";

function Dashboard({ onLogout }) {
  const [activePage, setActivePage] = useState("Dashboard");

  // Theme preference
  const [theme, setTheme] = useState(
    () => localStorage.getItem("loaner-theme") || "light"
  );

  useEffect(() => {
    localStorage.setItem("loaner-theme", theme);
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const [shops, setShops] = useState([]);
  const [loadingShops, setLoadingShops] = useState(true);
  const [shopError, setShopError] = useState("");

  const [customers, setCustomers] = useState([]);
  const [loadingCustomers, setLoadingCustomers] = useState(true);

  const [loans, setLoans] = useState([]);
  const [loadingLoans, setLoadingLoans] = useState(true);
  const [loanError, setLoanError] = useState("");

  const [interestCollected, setInterestCollected] = useState(0);
  const [loadingPayments, setLoadingPayments] = useState(true);
  const [paymentError, setPaymentError] = useState("");

  const getList = (data) => {
    if (Array.isArray(data)) return data;
    if (Array.isArray(data?.results)) return data.results;
    if (Array.isArray(data?.payments)) return data.payments;
    return [];
  };

  // Load shops
  useEffect(() => {
    let cancelled = false;

    const fetchShops = async () => {
      try {
        const response = await api.get("shops/");

        if (!cancelled) {
          setShops(getList(response.data));
          setShopError("");
        }
      } catch (error) {
        console.error("Shop API error:", error);

        if (!cancelled) {
          setShopError("Unable to load shop details.");
        }
      } finally {
        if (!cancelled) {
          setLoadingShops(false);
        }
      }
    };

    fetchShops();

    return () => {
      cancelled = true;
    };
  }, []);

  // Load customers
  useEffect(() => {
    if (loadingShops || shops.length === 0) return;

    let cancelled = false;

    const fetchCustomers = async () => {
      try {
        const response = await api.get(
          `shops/${shops[0].id}/customers/`
        );

        if (!cancelled) {
          setCustomers(getList(response.data));
        }
      } catch (error) {
        console.error("Customer API error:", error);
      } finally {
        if (!cancelled) {
          setLoadingCustomers(false);
        }
      }
    };

    fetchCustomers();

    return () => {
      cancelled = true;
    };
  }, [shops, loadingShops]);

  // Load loans
  useEffect(() => {
    if (loadingShops || shops.length === 0) return;

    let cancelled = false;

    const fetchLoans = async () => {
      try {
        const response = await api.get(
          `shops/${shops[0].id}/loans/`
        );

        if (!cancelled) {
          setLoans(getList(response.data));
          setLoanError("");
        }
      } catch (error) {
        console.error("Loan API error:", error);

        if (!cancelled) {
          setLoanError("Unable to load loan details.");
        }
      } finally {
        if (!cancelled) {
          setLoadingLoans(false);
        }
      }
    };

    fetchLoans();

    return () => {
      cancelled = true;
    };
  }, [shops, loadingShops]);

  // Load payment history for dashboard statistics
  useEffect(() => {
    if (
      loadingShops ||
      loadingLoans ||
      shops.length === 0 ||
      loanError
    ) {
      return;
    }

    if (loans.length === 0) {
      return;
    }

    let cancelled = false;

    const fetchPayments = async () => {
      try {
        const responses = await Promise.all(
          loans.map((loan) =>
            api.get(
              `shops/${shops[0].id}/loans/${loan.id}/payments/history/`
            )
          )
        );

        const totalInterest = responses.reduce(
          (total, response) => {
            const data = response.data;

            const payments = Array.isArray(data)
              ? data
              : Array.isArray(data?.results)
                ? data.results
                : Array.isArray(data?.payments)
                  ? data.payments
                  : [];

            return (
              total +
              payments.reduce(
                (sum, payment) =>
                  sum + Number(payment.interest_amount || 0),
                0
              )
            );
          },
          0
        );

        if (!cancelled) {
          setInterestCollected(totalInterest);
          setPaymentError("");
        }
      } catch (error) {
        console.error("Payment history API error:", error);

        if (!cancelled) {
          setPaymentError("Unable to load payment details.");
        }
      } finally {
        if (!cancelled) {
          setLoadingPayments(false);
        }
      }
    };

    fetchPayments();

    return () => {
      cancelled = true;
    };
  }, [shops, loans, loadingShops, loadingLoans, loanError]);

  const customersAreLoading =
    loadingShops || (shops.length > 0 && loadingCustomers);

  const loansAreLoading =
    loadingShops || (shops.length > 0 && loadingLoans);

  const paymentsAreLoading =
    loadingShops ||
    loadingLoans ||
    (!loanError && loans.length > 0 && loadingPayments);

  const formatCurrency = (amount) =>
    new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(Number(amount || 0));

  const currentYear = new Date().getFullYear();

  const monthlyLoanData = Array.from({ length: 12 }, (_, index) => {
    const monthlyLoans = loans.filter((loan) => {
      if (!loan.loan_date) return false;

      const date = new Date(loan.loan_date);

      return (
        !Number.isNaN(date.getTime()) &&
        date.getFullYear() === currentYear &&
        date.getMonth() === index
      );
    });

    return {
      month: new Date(currentYear, index).toLocaleString("en-IN", {
        month: "short",
      }),
      amount: monthlyLoans.reduce(
        (total, loan) =>
          total + Number(loan.principal_amount || 0),
        0
      ),
    };
  });

  const yearlyLoanAmount = monthlyLoanData.reduce(
    (total, month) => total + month.amount,
    0
  );

  const maxMonthlyAmount = Math.max(
    ...monthlyLoanData.map((month) => month.amount),
    1
  );

  const totalLoanPrincipal = loans.reduce(
    (total, loan) =>
      total + Number(loan.principal_amount || 0),
    0
  );

  const activeLoans = loans.filter(
    (loan) => String(loan.status).toUpperCase() === "ACTIVE"
  ).length;

  const menuItems = [
    { name: "Dashboard", icon: LayoutDashboard },
    { name: "Shops", icon: Store },
    { name: "Customers", icon: Users },
    { name: "Loans", icon: HandCoins },
    { name: "Gold Items", icon: Gem },
    { name: "Payments", icon: Receipt },
    { name: "Settings", icon: Settings },
  ];

  const stats = [
    {
      title: "Total Loan Principal",
      value: loansAreLoading
        ? "..."
        : loanError
          ? "—"
          : formatCurrency(totalLoanPrincipal),
      icon: Wallet,
      description: "Live data from Django API",
    },
    {
      title: "Active Loans",
      value: loansAreLoading
        ? "..."
        : loanError
          ? "—"
          : activeLoans,
      icon: HandCoins,
      description: "Live data from Django API",
    },
    {
      title: "Interest Collected",
      value: paymentsAreLoading
        ? "..."
        : paymentError || loanError
          ? "—"
          : formatCurrency(interestCollected),
      icon: CircleDollarSign,
      description: "Live data from payment history",
    },
    {
      title: "Total Customers",
      value: customersAreLoading
        ? "..."
        : customers.length,
      icon: Users,
      description: "Live data from Django API",
    },
  ];

  return (
    <div className="dashboard-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-logo">L</div>
          <div>
            <h2>LOANER</h2>
            <span>PAWN MANAGEMENT</span>
          </div>
        </div>

        <p className="menu-label">MAIN MENU</p>

        <nav className="sidebar-menu">
          {menuItems.map((item) => {
            const Icon = item.icon;

            return (
              <button
                key={item.name}
                type="button"
                className={`menu-item ${
                  activePage === item.name ? "active" : ""
                }`}
                onClick={() => setActivePage(item.name)}
              >
                <Icon size={19} />
                <span>{item.name}</span>
              </button>
            );
          })}
        </nav>

        <button
          className="sidebar-logout"
          type="button"
          onClick={onLogout}
        >
          <LogOut size={18} />
          <span>Logout</span>
        </button>
      </aside>

      <main className="dashboard-main">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace / <strong>{activePage}</strong>
          </div>

          <div className="topbar-actions">
            <div className="search-box">
              <Search size={17} />
              <input placeholder="Search anything..." />
            </div>

            <button
              className="notification-button"
              type="button"
              aria-label="Notifications"
            >
              <Bell size={20} />
            </button>

            <button
              className="theme-toggle"
              type="button"
              onClick={() =>
                setTheme((current) =>
                  current === "light" ? "dark" : "light"
                )
              }
              aria-label={`Switch to ${
                theme === "light" ? "dark" : "light"
              } mode`}
              title={`Switch to ${
                theme === "light" ? "dark" : "light"
              } mode`}
            >
              {theme === "light" ? (
                <Moon size={19} />
              ) : (
                <Sun size={19} />
              )}
            </button>

            <div className="profile-avatar">K</div>
          </div>
        </header>

        {activePage === "Shops" ? (
          <section className="dashboard-content">
            <Shops />
          </section>
        ) : activePage === "Customers" ? (
          <section className="dashboard-content">
            {loadingShops ? (
              <p>Loading shop details...</p>
            ) : shopError ? (
              <p>{shopError}</p>
            ) : shops.length > 0 ? (
              <Customers shopId={shops[0].id} />
            ) : (
              <p>Please create a shop before adding customers.</p>
            )}
          </section>
        ) : activePage === "Loans" ? (
          <section className="dashboard-content">
            {loadingShops ? (
              <p>Loading shop details...</p>
            ) : shopError ? (
              <p>{shopError}</p>
            ) : shops.length > 0 ? (
              <Loans shopId={shops[0].id} />
            ) : (
              <p>Please create a shop before creating loans.</p>
            )}
          </section>
        ) : activePage === "Gold Items" ? (
          <section className="dashboard-content">
            {loadingShops ? (
              <p>Loading shop details...</p>
            ) : shopError ? (
              <p>{shopError}</p>
            ) : shops.length > 0 ? (
              <GoldItems shopId={shops[0].id} />
            ) : (
              <p>Please create a shop before managing gold items.</p>
            )}
          </section>
        ) : activePage === "Payments" ? (
          <section className="dashboard-content">
            {loadingShops ? (
              <p>Loading shop details...</p>
            ) : shopError ? (
              <p>{shopError}</p>
            ) : shops.length > 0 ? (
              <Payments shopId={shops[0].id} />
            ) : (
              <p>Please create a shop before managing payments.</p>
            )}
          </section>
        ) : activePage === "Settings" ? (
          <section className="dashboard-content">
            {loadingShops ? (
              <p>Loading shop details...</p>
            ) : shopError ? (
              <p>{shopError}</p>
            ) : shops.length > 0 ? (
              <SettingsPage shopId={shops[0].id} />
            ) : (
              <p>Please create a shop before managing settings.</p>
            )}
          </section>
        ) : activePage === "Dashboard" ? (
          <section className="dashboard-content">
            <div className="page-heading">
              <div>
                <span className="section-eyebrow">OVERVIEW</span>
                <h1>Dashboard</h1>
                <p>
                  Welcome back! Here's what's happening with your business.
                </p>
              </div>

              <button
                className="new-loan-button"
                type="button"
                onClick={() => setActivePage("Loans")}
              >
                <Plus size={18} />
                New Loan
              </button>
            </div>

            <div className="stats-grid">
              {stats.map((stat) => {
                const Icon = stat.icon;

                return (
                  <div className="stat-card" key={stat.title}>
                    <div className="stat-top">
                      <span>{stat.title}</span>
                      <div className="stat-icon">
                        <Icon size={21} />
                      </div>
                    </div>

                    <h2>{stat.value}</h2>

                    <div className="stat-change">
                      <span>{stat.description}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="dashboard-grid">
              <section className="overview-card">
                <div className="card-heading">
                  <div>
                    <h3>Business Overview</h3>
                    <p>
                      Monthly loan activity and business performance
                    </p>
                  </div>

                  <button className="month-button" type="button">
                    <CalendarDays size={15} />
                    {currentYear}
                  </button>
                </div>

                <div className="chart-summary">
                  <span>Total Loan Amount - {currentYear}</span>
                  <h2>
                    {loansAreLoading
                      ? "Loading..."
                      : loanError
                        ? "—"
                        : formatCurrency(yearlyLoanAmount)}
                  </h2>
                </div>

                <div className="bar-chart">
                  {monthlyLoanData.map((month) => (
                    <div className="bar-column" key={month.month}>
                      <div
                        className="chart-bar"
                        title={`${month.month}: ${formatCurrency(month.amount)}`}
                        style={{
                          height:
                            month.amount > 0
                              ? `${Math.max(
                                  (month.amount / maxMonthlyAmount) * 100,
                                  4
                                )}%`
                              : "0%",
                        }}
                      />
                    </div>
                  ))}
                </div>

                <div className="chart-months">
                  {monthlyLoanData.map((month) => (
                    <span key={month.month}>{month.month}</span>
                  ))}
                </div>
              </section>

              <section className="shop-summary-card">
                <div className="card-heading">
                  <div>
                    <h3>Shop Summary</h3>
                    <p>Your business locations</p>
                  </div>
                  <Store size={19} />
                </div>

                {loadingShops ? (
                  <p>Loading shop details...</p>
                ) : shopError ? (
                  <p>{shopError}</p>
                ) : shops.length === 0 ? (
                  <p>No shops found.</p>
                ) : (
                  shops.map((shop) => (
                    <div key={shop.id}>
                      <div className="shop-icon">
                        <Store size={29} />
                      </div>

                      <h3 className="shop-name">{shop.name}</h3>
                      <p className="shop-location">{shop.address}</p>

                      <div className="shop-divider" />

                      <div className="shop-stats">
                        <div>
                          <span>Shop Code</span>
                          <strong>{shop.shop_code}</strong>
                        </div>

                        <div>
                          <span>Status</span>
                          <strong>
                            {shop.is_active ? "Active" : "Inactive"}
                          </strong>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </section>
            </div>

            <div className="demo-notice">
              Dashboard statistics, shop details and monthly loan activity
              are loaded from Django API.
            </div>
          </section>
        ) : (
          <section className="dashboard-content">
            <div className="page-heading">
              <div>
                <span className="section-eyebrow">COMING NEXT</span>
                <h1>{activePage}</h1>
                <p>This module will be available soon.</p>
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default Dashboard;
