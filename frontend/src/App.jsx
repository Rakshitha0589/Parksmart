
import React, { useState, useEffect, useMemo, useRef } from "react";
import { QRCodeSVG } from "qrcode.react";
import { Html5Qrcode } from "html5-qrcode";

const API_URL = "http://127.0.0.1:8000";
const areas = ["Parking A", "Parking B", "Parking C"];

const initialSlots = Array.from({ length: 300 }, (_, i) => ({
  id: `S${String(i + 1).padStart(3, "0")}`,
  area: areas[Math.floor(i / 100)],
  status: "available",
  vehicle: "",
  bookingId: "",
  owner: "",
}));

const readStorage = (key, fallback) => {
  try {
    const value = localStorage.getItem(key);
    return value ? JSON.parse(value) : fallback;
  } catch {
    return fallback;
  }
};

const styles = {
  app: {
    minHeight: "100vh",
    background: "#0b1120",
    color: "#e7edf8",
    fontFamily: "Inter, Arial, sans-serif",
  },
  card: {
    background: "#151e30",
    border: "1px solid #25334a",
    borderRadius: 16,
    padding: 20,
  },
};

function App() {
  const [user, setUser] = useState(() => readStorage("parksmart_user", null));
  const [page, setPage] = useState("Dashboard");

  const [users, setUsers] = useState(() =>
    readStorage("parksmart_users", [])
  );

  const [slots, setSlots] = useState(() =>
    readStorage("parksmart_slots_v5", initialSlots)
  );

  const [history, setHistory] = useState(() =>
    readStorage("parking_history", [])
  );

  const [backendStatus, setBackendStatus] = useState("Checking");

  const [selectedArea, setSelectedArea] = useState("Parking A");
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [vehicleNumber, setVehicleNumber] = useState("");
  const [message, setMessage] = useState("");

  // LOGIN
  const [loginRole, setLoginRole] = useState("user");
  const [loginMode, setLoginMode] = useState("login");
  const [loginName, setLoginName] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  // OPERATOR QR SCANNER
  const [scannedBooking, setScannedBooking] = useState(null);
  const [scanMessage, setScanMessage] = useState("");
  const [cameraError, setCameraError] = useState("");
  const [manualBookingId, setManualBookingId] = useState("");
  const [cameraActive, setCameraActive] = useState(false);

  const scannerRef = useRef(null);
  const scannerRunningRef = useRef(false);
  const scanHandledRef = useRef(false);

  // SAVE DATA
  useEffect(() => {
    localStorage.setItem("parksmart_slots_v5", JSON.stringify(slots));
  }, [slots]);

  useEffect(() => {
    localStorage.setItem("parking_history", JSON.stringify(history));
  }, [history]);

  useEffect(() => {
    localStorage.setItem("parksmart_users", JSON.stringify(users));
  }, [users]);

  useEffect(() => {
    localStorage.setItem("parksmart_user", JSON.stringify(user));
  }, [user]);

  // BACKEND CONNECTION
  useEffect(() => {
    const checkBackend = async () => {
      try {
        const response = await fetch(`${API_URL}/`);
        if (!response.ok) throw new Error();

        const data = await response.json();
        setBackendStatus(data.status === "success" ? "Connected" : "Offline");
      } catch {
        setBackendStatus("Offline");
      }
    };

    checkBackend();
    const timer = setInterval(checkBackend, 5000);
    return () => clearInterval(timer);
  }, []);

  // PARKING STATISTICS
  const stats = useMemo(() => {
    const total = slots.length;
    const occupied = slots.filter((s) => s.status === "occupied").length;
    const booked = slots.filter((s) => s.status === "booked").length;
    const available = slots.filter((s) => s.status === "available").length;
    const rate = total ? Math.round(((occupied + booked) / total) * 100) : 0;

    return { total, occupied, booked, available, rate };
  }, [slots]);

  const areaStats = useMemo(
    () =>
      areas.map((area) => {
        const areaSlots = slots.filter((s) => s.area === area);
        const occupied = areaSlots.filter((s) => s.status === "occupied").length;
        const booked = areaSlots.filter((s) => s.status === "booked").length;
        const available = areaSlots.filter(
          (s) => s.status === "available"
        ).length;

        return {
          area,
          total: areaSlots.length,
          occupied,
          booked,
          available,
          rate: Math.round(
            ((occupied + booked) / (areaSlots.length || 1)) * 100
          ),
        };
      }),
    [slots]
  );

  // PREDICTIONS
  const demand =
    stats.rate >= 80 ? "HIGH" : stats.rate >= 50 ? "MEDIUM" : "LOW";

  const congestion =
    stats.rate >= 85 ? "Heavy" : stats.rate >= 60 ? "Moderate" : "Light";

  const waitingTime =
    stats.rate >= 90
      ? "15–25 min"
      : stats.rate >= 70
      ? "8–15 min"
      : stats.rate >= 40
      ? "3–8 min"
      : "0–3 min";

  const bestArea = [...areaStats].sort(
    (a, b) => b.available - a.available
  )[0];

  const peakHour = useMemo(() => {
    const hourCounts = {};

    history.forEach((item) => {
      if (!item.timestamp) return;
      const hour = new Date(item.timestamp).getHours();
      hourCounts[hour] = (hourCounts[hour] || 0) + 1;
    });

    const entries = Object.entries(hourCounts);
    if (!entries.length) return "5 PM – 8 PM (estimated)";

    const peak = entries.sort((a, b) => b[1] - a[1])[0][0];
    const h = Number(peak);
    const next = (h + 1) % 24;
    return `${h}:00 – ${next}:00`;
  }, [history]);

  const alerts = useMemo(() => {
    const list = [];

    if (stats.rate >= 85)
      list.push("Parking occupancy is high. Consider directing vehicles to other areas.");

    if (stats.available === 0)
      list.push("All parking slots are currently full.");

    if (bestArea && bestArea.available > 0)
      list.push(`${bestArea.area} has the most available slots.`);

    if (!list.length)
      list.push("Parking conditions are normal. No major alerts.");

    return list;
  }, [stats, bestArea]);

  // USER'S BOOKINGS
  const myBookings = slots.filter(
    (s) => s.bookingId && s.owner === user?.username
  );

  const filteredSlots = slots.filter((s) => s.area === selectedArea);

  // LOGIN / REGISTER
  const handleLogin = (e) => {
    e.preventDefault();
    setMessage("");

    if (loginRole === "operator") {
      if (loginName === "operator" && loginPassword === "park123") {
        const operatorUser = {
          username: "operator",
          role: "operator",
          name: "Parking Operator",
        };

        setUser(operatorUser);
        setPage("Operator");
        setScannedBooking(null);
        setScanMessage("");
        setMessage("");
      } else {
        setMessage("Invalid operator username or password.");
      }
      return;
    }

    if (loginMode === "register") {
      if (loginName.trim().length < 3 || loginPassword.length < 4) {
        setMessage("Username must be 3 characters and password at least 4 characters.");
        return;
      }

      if (users.some((u) => u.username.toLowerCase() === loginName.toLowerCase())) {
        setMessage("Username already exists. Please log in.");
        return;
      }

      const newUser = {
        username: loginName.trim(),
        password: loginPassword,
        role: "user",
      };

      setUsers((prev) => [...prev, newUser]);
      setUser(newUser);
      setPage("Dashboard");
      setMessage("");
      return;
    }

    const foundUser = users.find(
      (u) =>
        u.username.toLowerCase() === loginName.toLowerCase() &&
        u.password === loginPassword
    );

    if (foundUser) {
      setUser(foundUser);
      setPage("Dashboard");
      setMessage("");
    } else {
      setMessage("Invalid user credentials. Register if you are new.");
    }
  };

  // STOP QR SCANNER
  const stopCamera = async () => {
    const scanner = scannerRef.current;

    scannerRunningRef.current = false;
    setCameraActive(false);

    if (!scanner) return;

    try {
      if (scanner.isScanning) {
        await scanner.stop();
      }
    } catch {
      // Scanner may already be stopped.
    }

    try {
      scanner.clear();
    } catch {
      // Scanner may already be cleared.
    }

    if (scannerRef.current === scanner) {
      scannerRef.current = null;
    }
  };

  const logout = () => {
    stopCamera();
    setUser(null);
    setPage("Dashboard");
    setScannedBooking(null);
    setScanMessage("");
    setMessage("");
    setLoginName("");
    setLoginPassword("");
  };

  // BOOKING
  const bookSlot = () => {
    if (!user || user.role !== "user") {
      setMessage("Please log in as a user to book parking.");
      return;
    }

    if (!selectedSlot) {
      setMessage("Please select a parking slot.");
      return;
    }

    if (!vehicleNumber.trim()) {
      setMessage("Please enter your vehicle number.");
      return;
    }

    const slot = slots.find((s) => s.id === selectedSlot);

    if (!slot || slot.status !== "available") {
      setMessage("This slot is no longer available.");
      setSelectedSlot(null);
      return;
    }

    const bookingId = `PK${Date.now().toString().slice(-8)}`;

    const newBooking = {
      bookingId,
      slotId: slot.id,
      area: slot.area,
      vehicle: vehicleNumber.trim().toUpperCase(),
      owner: user.username,
      status: "booked",
      timestamp: new Date().toISOString(),
    };

    setSlots((prev) =>
      prev.map((s) =>
        s.id === slot.id
          ? {
              ...s,
              status: "booked",
              vehicle: newBooking.vehicle,
              bookingId,
              owner: user.username,
            }
          : s
      )
    );

    setVehicleNumber("");
    setSelectedSlot(null);
    setMessage("Parking slot booked successfully!");
    setPage("Bookings");
  };

  // QR BOOKING LOOKUP
  const findBooking = (bookingId) => {
    const normalized = String(bookingId || "").trim();

    if (!normalized) {
      setScannedBooking(null);
      setScanMessage("Please enter a Booking ID.");
      return;
    }

    const selected = slots.find((s) => s.bookingId === normalized);

    if (!selected) {
      setScannedBooking(null);
      setScanMessage("Booking not found or already completed.");
      return;
    }

    setScannedBooking(selected);
    setScanMessage("Booking verified successfully.");
    setCameraError("");
  };

  // PROCESS QR CONTENT
  const processQRValue = (value) => {
    try {
      let bookingId = value;

      try {
        const parsed = JSON.parse(value);
        bookingId = parsed.bookingId || parsed.id || value;
      } catch {
        bookingId = value;
      }

      findBooking(bookingId);
    } catch {
      setScanMessage("Invalid QR code.");
    }
  };

  // START QR SCANNER USING HTML5-QRCODE
  const startCamera = async () => {
    setCameraError("");
    setScanMessage("");
    setScannedBooking(null);

    if (scannerRunningRef.current) {
      await stopCamera();
    }

    scanHandledRef.current = false;

    try {
      const element = document.getElementById("operator-qr-reader");

      if (!element) {
        setCameraError("Scanner area is not ready. Please try again.");
        return;
      }

      const scanner = new Html5Qrcode("operator-qr-reader");
      scannerRef.current = scanner;

      await scanner.start(
        { facingMode: "environment" },
        {
          fps: 10,
          qrbox: (viewfinderWidth, viewfinderHeight) => {
            const minEdge = Math.min(viewfinderWidth, viewfinderHeight);
            const qrSize = Math.floor(minEdge * 0.7);
            return { width: qrSize, height: qrSize };
          },
          aspectRatio: 1,
          disableFlip: false,
        },
        (decodedText) => {
          if (scanHandledRef.current) return;

          scanHandledRef.current = true;
          scannerRunningRef.current = false;

          setScanMessage("QR code detected! Verifying booking...");
          stopCamera();
          processQRValue(decodedText);
        },
        () => {
          // Ignore individual frames where no QR code is detected.
        }
      );

      scannerRunningRef.current = true;
      setCameraActive(true);
    } catch (error) {
      scannerRunningRef.current = false;
      setCameraActive(false);

      if (scannerRef.current) {
        try {
          await scannerRef.current.clear();
        } catch {
          // Ignore cleanup error.
        }
        scannerRef.current = null;
      }

      setCameraError(
        error?.name === "NotAllowedError"
          ? "Camera permission denied. Allow camera access in Chrome site settings."
          : error?.name === "NotFoundError"
          ? "No camera detected. Connect a camera and try again."
          : error?.name === "NotReadableError"
          ? "Camera is being used by another application. Close other camera apps."
          : error?.message || "Unable to start camera. Check camera permissions."
      );
    }
  };

  // AUTOMATIC SCANNER ON OPERATOR LOGIN
  useEffect(() => {
    if (user?.role === "operator" && page === "Operator") {
      const timer = setTimeout(() => startCamera(), 700);

      return () => {
        clearTimeout(timer);
        stopCamera();
      };
    }

    stopCamera();
    return undefined;
  }, [user, page]);

  // CONFIRM VEHICLE ENTRY
  const confirmEntry = () => {
    if (!user || user.role !== "operator" || !scannedBooking) {
      setScanMessage("Operator permission required.");
      return;
    }

    const selected = slots.find(
      (s) => s.bookingId === scannedBooking.bookingId
    );

    if (!selected || selected.status !== "booked") {
      setScanMessage("This booking is not eligible for entry.");
      return;
    }

    setSlots((prev) =>
      prev.map((s) =>
        s.bookingId === selected.bookingId
          ? { ...s, status: "occupied" }
          : s
      )
    );

    const entryRecord = {
      bookingId: selected.bookingId,
      slotId: selected.id,
      area: selected.area,
      vehicle: selected.vehicle,
      owner: selected.owner,
      action: "Entry",
      operator: user.username,
      timestamp: new Date().toISOString(),
    };

    setHistory((prev) => [entryRecord, ...prev]);
    setScannedBooking(null);
    setScanMessage("Entry confirmed. Vehicle is now marked occupied.");
  };

  // CONFIRM VEHICLE EXIT
  const confirmExit = () => {
    if (!user || user.role !== "operator" || !scannedBooking) {
      setScanMessage("Operator permission required.");
      return;
    }

    const selected = slots.find(
      (s) => s.bookingId === scannedBooking.bookingId
    );

    if (!selected || selected.status !== "occupied") {
      setScanMessage("This vehicle does not have an active parking session.");
      return;
    }

    const exitRecord = {
      bookingId: selected.bookingId,
      slotId: selected.id,
      area: selected.area,
      vehicle: selected.vehicle,
      owner: selected.owner,
      action: "Exit",
      operator: user.username,
      timestamp: new Date().toISOString(),
    };

    setHistory((prev) => [exitRecord, ...prev]);

    setSlots((prev) =>
      prev.map((s) =>
        s.bookingId === selected.bookingId
          ? {
              ...s,
              status: "available",
              vehicle: "",
              bookingId: "",
              owner: "",
            }
          : s
      )
    );

    setScannedBooking(null);
    setScanMessage("Exit confirmed. Parking slot has been released.");
  };

  // UI HELPERS
  const badge = (status) => {
    const colors = {
      available: "#22c55e",
      booked: "#f59e0b",
      occupied: "#ef4444",
    };

    return (
      <span
        style={{
          background: `${colors[status] || "#64748b"}20`,
          color: colors[status] || "#64748b",
          padding: "5px 10px",
          borderRadius: 20,
          fontSize: 12,
          fontWeight: 700,
        }}
      >
        {String(status).toUpperCase()}
      </span>
    );
  };

  const statCard = (title, value, subtitle, icon, color) => (
    <div
      style={{
        ...styles.card,
        borderTop: `3px solid ${color}`,
        minWidth: 0,
      }}
    >
      <div style={{ fontSize: 24 }}>{icon}</div>
      <p style={{ color: "#94a3b8", marginBottom: 8 }}>{title}</p>
      <div style={{ fontSize: 30, fontWeight: 800, color }}>{value}</div>
      <small style={{ color: "#94a3b8" }}>{subtitle}</small>
    </div>
  );

  const predictionCard = (title, value, description, icon, color) => (
    <div style={{ ...styles.card, minWidth: 0 }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <span style={{ color: "#94a3b8" }}>{title}</span>
        <span>{icon}</span>
      </div>
      <h2 style={{ color, margin: "12px 0" }}>{value}</h2>
      <small style={{ color: "#94a3b8" }}>{description}</small>
    </div>
  );

  const btn = (active = false) => ({
    background: active ? "#2563eb" : "#1b2940",
    border: "1px solid #2c3c55",
    color: "#fff",
    borderRadius: 9,
    padding: "11px 16px",
    cursor: "pointer",
    fontWeight: 600,
  });

  const navItems =
    user?.role === "operator"
      ? ["Operator", "Dashboard", "Parking", "History", "Analytics", "ML Predictions"]
      : ["Dashboard", "Parking", "Bookings", "History", "Analytics", "ML Predictions"];

  // LOGIN SCREEN
  if (!user) {
    return (
      <div style={styles.app}>
        <div
          style={{
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 20,
          }}
        >
          <div style={{ ...styles.card, width: "100%", maxWidth: 440 }}>
            <div style={{ textAlign: "center", marginBottom: 25 }}>
              <div style={{ fontSize: 45 }}>🅿️</div>
              <h1 style={{ color: "#60a5fa", marginBottom: 5 }}>ParkSmart AI</h1>
              <p style={{ color: "#94a3b8" }}>Smart Parking Management System</p>
            </div>

            <div style={{ display: "flex", gap: 10, marginBottom: 20 }}>
              <button
                style={{ ...btn(loginRole === "user"), flex: 1 }}
                onClick={() => {
                  setLoginRole("user");
                  setLoginMode("login");
                  setMessage("");
                }}
              >
                👤 User
              </button>
              <button
                style={{ ...btn(loginRole === "operator"), flex: 1 }}
                onClick={() => {
                  setLoginRole("operator");
                  setLoginMode("login");
                  setMessage("");
                }}
              >
                🛡️ Operator
              </button>
            </div>

            <h2 style={{ marginTop: 0 }}>
              {loginRole === "operator"
                ? "Operator Login"
                : loginMode === "register"
                ? "Create User Account"
                : "User Login"}
            </h2>

            <form onSubmit={handleLogin} style={{ display: "grid", gap: 14 }}>
              <input
                value={loginName}
                onChange={(e) => setLoginName(e.target.value)}
                placeholder={loginRole === "operator" ? "Operator username" : "Username"}
                autoComplete="username"
                required
                style={{
                  padding: 13,
                  borderRadius: 9,
                  background: "#0b1120",
                  color: "#fff",
                  border: "1px solid #334155",
                }}
              />

              <input
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                placeholder="Password"
                type="password"
                autoComplete="current-password"
                required
                style={{
                  padding: 13,
                  borderRadius: 9,
                  background: "#0b1120",
                  color: "#fff",
                  border: "1px solid #334155",
                }}
              />

              <button type="submit" style={btn(true)}>
                {loginRole === "operator"
                  ? "Operator Login"
                  : loginMode === "register"
                  ? "Register"
                  : "User Login"}
              </button>
            </form>

            {loginRole === "user" && (
              <p
                style={{
                  color: "#94a3b8",
                  textAlign: "center",
                  marginTop: 18,
                }}
              >
                {loginMode === "login" ? "New user? " : "Already registered? "}
                <button
                  onClick={() => {
                    setLoginMode(loginMode === "login" ? "register" : "login");
                    setMessage("");
                  }}
                  style={{
                    background: "none",
                    border: "none",
                    color: "#60a5fa",
                    cursor: "pointer",
                  }}
                >
                  {loginMode === "login" ? "Register here" : "Login here"}
                </button>
              </p>
            )}

            {loginRole === "operator" && (
              <div
                style={{
                  background: "#0b1120",
                  borderRadius: 10,
                  padding: 12,
                  marginTop: 15,
                  color: "#94a3b8",
                  fontSize: 13,
                }}
              >
                Demo operator credentials:
                <br />
                Username: <strong>operator</strong>
                <br />
                Password: <strong>park123</strong>
              </div>
            )}

            {message && (
              <p style={{ color: "#f87171", marginTop: 15 }}>{message}</p>
            )}
          </div>
        </div>
      </div>
    );
  }

  // MAIN APP
  return (
    <div style={styles.app}>
      <div style={{ display: "flex", minHeight: "100vh", flexDirection: "column" }}>
        {/* HEADER */}
        <header
          style={{
            background: "#111a2b",
            padding: "18px 24px",
            borderBottom: "1px solid #25334a",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          <div>
            <h2 style={{ margin: 0, color: "#60a5fa" }}>🅿 ParkSmart AI</h2>
            <small style={{ color: "#94a3b8" }}>
              Smart Parking Management System
            </small>
          </div>

          <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
            <div
              style={{
                display: "flex",
                gap: 8,
                alignItems: "center",
                background: "#0b1120",
                border: "1px solid #26354b",
                borderRadius: 30,
                padding: "8px 14px",
              }}
            >
              <span
                style={{
                  width: 9,
                  height: 9,
                  borderRadius: "50%",
                  background:
                    backendStatus === "Connected"
                      ? "#22c55e"
                      : backendStatus === "Checking"
                      ? "#f59e0b"
                      : "#ef4444",
                }}
              />
              <span style={{ fontSize: 13 }}>{backendStatus}</span>
            </div>

            <div style={{ color: "#cbd5e1", fontSize: 13 }}>
              {user.role === "operator" ? "🛡 Operator" : "👤 User"}: {user.username}
            </div>

            <button style={btn()} onClick={logout}>
              Logout
            </button>
          </div>
        </header>

        {/* NAVIGATION */}
        <nav
          style={{
            padding: 15,
            display: "flex",
            gap: 8,
            overflowX: "auto",
            borderBottom: "1px solid #25334a",
          }}
        >
          {navItems.map((item) => (
            <button
              key={item}
              style={btn(page === item)}
              onClick={() => {
                setPage(item);
                setMessage("");
              }}
            >
              {item}
            </button>
          ))}
        </nav>

        {/* CONTENT */}
        <main
          style={{
            padding: 24,
            maxWidth: 1500,
            margin: "0 auto",
            width: "100%",
            boxSizing: "border-box",
          }}
        >
          {/* OPERATOR QR SCANNER */}
          {page === "Operator" && user.role === "operator" && (
            <div style={{ display: "grid", gap: 20 }}>
              <div>
                <h1>🛡️ Operator Panel</h1>
                <p style={{ color: "#94a3b8" }}>
                  Scan a customer's booking QR code to verify parking entry or exit.
                </p>
              </div>

              <div style={styles.card}>
                <h2>📷 QR Scanner</h2>
                <p style={{ color: "#94a3b8" }}>
                  The camera starts automatically when the Operator Panel opens.
                </p>

                <div
                  style={{
                    background: "#050914",
                    border: "2px solid #2563eb",
                    borderRadius: 15,
                    overflow: "hidden",
                    maxWidth: 650,
                    margin: "0 auto",
                    position: "relative",
                    minHeight: 300,
                  }}
                >
                  <div
                    id="operator-qr-reader"
                    style={{
                      width: "100%",
                      minHeight: 280,
                    }}
                  />

                  {!cameraActive && (
                    <div
                      style={{
                        minHeight: 280,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexDirection: "column",
                        gap: 12,
                        padding: 20,
                        color: "#94a3b8",
                        textAlign: "center",
                      }}
                    >
                      <div style={{ fontSize: 50 }}>📷</div>
                      <h3 style={{ margin: 0 }}>Scanner Ready</h3>
                      <p style={{ margin: 0 }}>
                        Allow camera access to start scanning QR codes.
                      </p>
                      <button style={btn(true)} onClick={startCamera}>
                        Start Camera
                      </button>
                    </div>
                  )}
                </div>

                <div style={{ display: "flex", gap: 10, justifyContent: "center", marginTop: 15, flexWrap: "wrap" }}>
                  <button style={btn(true)} onClick={startCamera}>
                    Restart Scanner
                  </button>
                  <button style={btn()} onClick={stopCamera}>
                    Stop Camera
                  </button>
                </div>

                {cameraError && (
                  <p style={{ color: "#f87171", marginTop: 15 }}>{cameraError}</p>
                )}
              </div>

              {/* MANUAL BOOKING LOOKUP */}
              <div style={styles.card}>
                <h3>Manual Booking Verification</h3>
                <p style={{ color: "#94a3b8" }}>
                  If camera scanning is unavailable, enter the Booking ID from the QR code.
                </p>

                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  <input
                    value={manualBookingId}
                    onChange={(e) => setManualBookingId(e.target.value)}
                    placeholder="Enter booking ID (e.g. PK12345678)"
                    style={{
                      padding: 12,
                      background: "#0b1120",
                      color: "#fff",
                      border: "1px solid #334155",
                      borderRadius: 9,
                      flex: "1 1 240px",
                    }}
                  />
                  <button
                    style={btn(true)}
                    onClick={() => findBooking(manualBookingId)}
                  >
                    Verify Booking
                  </button>
                </div>
              </div>

              {/* SCANNED BOOKING DETAILS */}
              {scannedBooking && (
                <div style={{ ...styles.card, border: "1px solid #22c55e" }}>
                  <h2 style={{ color: "#22c55e" }}>✅ Booking Verified</h2>

                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))",
                      gap: 15,
                    }}
                  >
                    <div>
                      <small style={{ color: "#94a3b8" }}>Booking ID</small>
                      <h3>{scannedBooking.bookingId}</h3>
                    </div>
                    <div>
                      <small style={{ color: "#94a3b8" }}>Vehicle Number</small>
                      <h3>{scannedBooking.vehicle}</h3>
                    </div>
                    <div>
                      <small style={{ color: "#94a3b8" }}>Parking Area</small>
                      <h3>{scannedBooking.area}</h3>
                    </div>
                    <div>
                      <small style={{ color: "#94a3b8" }}>Slot</small>
                      <h3>{scannedBooking.id}</h3>
                    </div>
                    <div>
                      <small style={{ color: "#94a3b8" }}>User</small>
                      <h3>{scannedBooking.owner || "N/A"}</h3>
                    </div>
                    <div>
                      <small style={{ color: "#94a3b8" }}>Status</small>
                      <h3>{scannedBooking.status.toUpperCase()}</h3>
                    </div>
                  </div>

                  {scannedBooking.status === "booked" && (
                    <div style={{ marginTop: 20 }}>
                      <button
                        style={{ ...btn(true), background: "#15803d" }}
                        onClick={confirmEntry}
                      >
                        ✓ Confirm Vehicle Entry
                      </button>
                    </div>
                  )}

                  {scannedBooking.status === "occupied" && (
                    <div style={{ marginTop: 20 }}>
                      <button
                        style={{ ...btn(true), background: "#b91c1c" }}
                        onClick={confirmExit}
                      >
                        ✓ Confirm Vehicle Exit
                      </button>
                    </div>
                  )}

                  <button
                    style={{ ...btn(), marginTop: 12 }}
                    onClick={() => setScannedBooking(null)}
                  >
                    Clear Scan
                  </button>
                </div>
              )}

              {scanMessage && (
                <div
                  style={{
                    ...styles.card,
                    borderColor: scanMessage.includes("confirmed") ? "#22c55e" : "#2563eb",
                  }}
                >
                  {scanMessage}
                </div>
              )}

              {/* ACTIVE BOOKINGS */}
              <div style={styles.card}>
                <h2>Active Bookings / Vehicles</h2>

                {slots.filter((s) => s.status !== "available").length === 0 ? (
                  <p style={{ color: "#94a3b8" }}>No active bookings or vehicles.</p>
                ) : (
                  slots
                    .filter((s) => s.status !== "available")
                    .map((slot) => (
                      <div
                        key={slot.id}
                        style={{
                          borderBottom: "1px solid #26354a",
                          padding: 14,
                          display: "flex",
                          justifyContent: "space-between",
                          flexWrap: "wrap",
                          gap: 10,
                        }}
                      >
                        <div>
                          <strong>{slot.area} — {slot.id}</strong>
                          <p style={{ margin: "6px 0" }}>Vehicle: {slot.vehicle}</p>
                          <p style={{ margin: "6px 0" }}>Booking: {slot.bookingId}</p>
                          {badge(slot.status)}
                        </div>

                        <button
                          style={btn()}
                          onClick={() => findBooking(slot.bookingId)}
                        >
                          View / Verify
                        </button>
                      </div>
                    ))
                )}
              </div>
            </div>
          )}

          {/* DASHBOARD */}
          {page === "Dashboard" && (
            <div style={{ display: "grid", gap: 22 }}>
              <div>
                <h1>Dashboard Overview</h1>
                <p style={{ color: "#94a3b8" }}>
                  Monitor your parking system in real time.
                </p>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit,minmax(190px,1fr))",
                  gap: 15,
                }}
              >
                {statCard("Total Slots", stats.total, "All parking areas", "🅿️", "#60a5fa")}
                {statCard("Available", stats.available, "Ready to park", "🟢", "#22c55e")}
                {statCard("Occupied", stats.occupied, "Vehicles parked", "🚗", "#ef4444")}
                {statCard("Booked", stats.booked, "Reserved slots", "📅", "#f59e0b")}
              </div>

              <div style={styles.card}>
                <h3>Parking Occupancy</h3>
                <div style={{ background: "#26354a", height: 16, borderRadius: 20, overflow: "hidden" }}>
                  <div
                    style={{
                      width: `${stats.rate}%`,
                      background: stats.rate >= 80 ? "#ef4444" : stats.rate >= 50 ? "#f59e0b" : "#22c55e",
                      height: "100%",
                      transition: "width 0.3s",
                    }}
                  />
                </div>
                <h2>{stats.rate}%</h2>
                <p style={{ color: "#94a3b8" }}>
                  {stats.occupied + stats.booked} out of {stats.total} slots occupied or booked
                </p>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit,minmax(230px,1fr))",
                  gap: 15,
                }}
              >
                {areaStats.map((a) => (
                  <div key={a.area} style={styles.card}>
                    <h3>{a.area}</h3>
                    <h2 style={{ color: "#60a5fa" }}>{a.available} Free</h2>
                    <p>Occupied: {a.occupied}</p>
                    <p>Booked: {a.booked}</p>
                    <p>Capacity: {a.total}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* PARKING */}
          {page === "Parking" && (
            <div style={{ display: "grid", gap: 20 }}>
              <div>
                <h1>Parking Slots</h1>
                <p style={{ color: "#94a3b8" }}>Select a parking area and an available slot.</p>
              </div>

              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                {areas.map((area) => (
                  <button
                    key={area}
                    style={btn(selectedArea === area)}
                    onClick={() => {
                      setSelectedArea(area);
                      setSelectedSlot(null);
                    }}
                  >
                    {area}
                  </button>
                ))}
              </div>

              <div style={styles.card}>
                <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
                  <span style={{ color: "#22c55e" }}>🟢 Available</span>
                  <span style={{ color: "#f59e0b" }}>🟠 Booked</span>
                  <span style={{ color: "#ef4444" }}>🔴 Occupied</span>
                </div>

                <h3 style={{ marginTop: 22 }}>{selectedArea} Slot Map</h3>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fill,minmax(55px,1fr))",
                    gap: 8,
                  }}
                >
                  {filteredSlots.map((slot) => {
                    const color =
                      slot.status === "available"
                        ? "#166534"
                        : slot.status === "booked"
                        ? "#92400e"
                        : "#991b1b";

                    return (
                      <button
                        key={slot.id}
                        disabled={slot.status !== "available"}
                        onClick={() => {
                          setSelectedSlot(slot.id);
                          setMessage("");
                        }}
                        title={`${slot.id} - ${slot.status}`}
                        style={{
                          background: selectedSlot === slot.id ? "#2563eb" : color,
                          color: "#fff",
                          border: selectedSlot === slot.id ? "2px solid #60a5fa" : "1px solid #334155",
                          borderRadius: 8,
                          padding: "10px 4px",
                          fontSize: 11,
                          cursor: slot.status === "available" ? "pointer" : "not-allowed",
                          opacity: slot.status === "available" ? 1 : 0.7,
                        }}
                      >
                        {slot.id}
                      </button>
                    );
                  })}
                </div>
              </div>

              {user.role === "user" && (
                <div style={styles.card}>
                  <h3>Book Your Slot</h3>
                  <p>
                    Selected Slot:{" "}
                    <strong style={{ color: "#60a5fa" }}>{selectedSlot || "None"}</strong>
                  </p>

                  <input
                    value={vehicleNumber}
                    onChange={(e) => setVehicleNumber(e.target.value)}
                    placeholder="Vehicle number (e.g. KA01AB1234)"
                    style={{
                      width: "100%",
                      maxWidth: 400,
                      boxSizing: "border-box",
                      padding: 13,
                      borderRadius: 9,
                      background: "#0b1120",
                      color: "#fff",
                      border: "1px solid #334155",
                      marginBottom: 15,
                    }}
                  />

                  <button style={btn(true)} onClick={bookSlot}>
                    Confirm Booking
                  </button>

                  {message && <p style={{ color: "#60a5fa", marginTop: 15 }}>{message}</p>}
                </div>
              )}
            </div>
          )}

          {/* BOOKINGS - USERS ONLY */}
          {page === "Bookings" && user.role === "user" && (
            <div style={{ display: "grid", gap: 20 }}>
              <h1>My Bookings</h1>

              {myBookings.length ? (
                myBookings.map((booking) => (
                  <div key={booking.bookingId} style={styles.card}>
                    <h3>Booking Details</h3>
                    <p>Booking ID: {booking.bookingId}</p>
                    <p>Area: {booking.area}</p>
                    <p>Slot: {booking.id}</p>
                    <p>Vehicle: {booking.vehicle}</p>
                    <p>Status: {booking.status.toUpperCase()}</p>

                    <div style={{ margin: "20px 0" }}>
                      <QRCodeSVG
                        value={JSON.stringify({
                          bookingId: booking.bookingId,
                          slotId: booking.id,
                        })}
                        size={190}
                        bgColor="#ffffff"
                        fgColor="#000000"
                      />
                    </div>

                    <p style={{ color: "#22c55e" }}>Your Parking QR Code</p>
                    <p style={{ color: "#94a3b8" }}>
                      Show this QR code to the operator at the parking entrance and exit.
                    </p>
                  </div>
                ))
              ) : (
                <div style={styles.card}>
                  <h3>No active booking</h3>
                  <p style={{ color: "#94a3b8" }}>Go to Parking and book an available slot.</p>
                  <button style={btn(true)} onClick={() => setPage("Parking")}>
                    Find Parking
                  </button>
                </div>
              )}
            </div>
          )}

          {/* HISTORY */}
          {page === "History" && (
            <div style={{ display: "grid", gap: 20 }}>
              <h1>Parking History</h1>
              <div style={styles.card}>
                {history.length === 0 ? (
                  <p style={{ color: "#94a3b8" }}>No parking history available yet.</p>
                ) : (
                  history
                    .filter((item) => user.role === "operator" || item.owner === user.username)
                    .map((item, i) => (
                      <div
                        key={`${item.bookingId}-${i}`}
                        style={{ padding: 15, borderBottom: "1px solid #26354a" }}
                      >
                        <h3>{item.action}</h3>
                        <p>{item.vehicle} · {item.area} · {item.slotId}</p>
                        <small style={{ color: "#94a3b8" }}>
                          {new Date(item.timestamp).toLocaleString()}
                        </small>
                        {user.role === "operator" && item.operator && (
                          <p><small>Operator: {item.operator}</small></p>
                        )}
                      </div>
                    ))
                )}
              </div>
            </div>
          )}

          {/* ANALYTICS */}
          {page === "Analytics" && (
            <div style={{ display: "grid", gap: 20 }}>
              <h1>Parking Analytics</h1>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))",
                  gap: 15,
                }}
              >
                {statCard("Occupancy Rate", `${stats.rate}%`, "Current utilization", "📊", "#60a5fa")}
                {statCard("Vehicle Entries", history.filter((h) => h.action === "Entry").length, "Recorded entries", "🚘", "#22c55e")}
                {statCard("Vehicle Exits", history.filter((h) => h.action === "Exit").length, "Recorded exits", "🚦", "#f59e0b")}
                {statCard("Transactions", history.length, "History records", "📋", "#a78bfa")}
              </div>

              <div style={styles.card}>
                <h2>Area Comparison</h2>
                {areaStats.map((area) => (
                  <div key={area.area} style={{ marginBottom: 20 }}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span>{area.area}</span>
                      <span>{area.rate}% occupied</span>
                    </div>
                    <div style={{ height: 12, background: "#26354a", borderRadius: 20, marginTop: 8, overflow: "hidden" }}>
                      <div style={{ height: "100%", width: `${area.rate}%`, background: "#3b82f6" }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ML PREDICTIONS */}
          {page === "ML Predictions" && (
            <div style={{ display: "grid", gap: 22 }}>
              <div>
                <h1>🧠 Smart Prediction Center</h1>
                <p style={{ color: "#94a3b8" }}>
                  Automatic parking intelligence based on current occupancy, reservations, and parking activity.
                </p>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit,minmax(210px,1fr))",
                  gap: 15,
                }}
              >
                {predictionCard("Availability", stats.available, `${stats.total} total parking slots`, "🅿️", "#22c55e")}
                {predictionCard("Demand", demand, `${stats.rate}% parking utilization`, "📈", demand === "HIGH" ? "#ef4444" : demand === "MEDIUM" ? "#f59e0b" : "#22c55e")}
                {predictionCard("Congestion", congestion, "Estimated from parking occupancy", "🚦", "#f59e0b")}
                {predictionCard("Waiting Time", waitingTime, "Estimated waiting time", "⏱️", "#60a5fa")}
                {predictionCard("Peak Hours", peakHour, "Based on parking history", "🕒", "#a78bfa")}
                {predictionCard("Best Parking Area", bestArea?.area || "N/A", `${bestArea?.available || 0} slots available`, "⭐", "#22c55e")}
              </div>

              <div style={styles.card}>
                <h2>📍 Parking Area Comparison</h2>
                {areaStats.map((area) => (
                  <div key={area.area} style={{ marginBottom: 22 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
                      <strong>{area.area}</strong>
                      <span style={{ color: "#22c55e" }}>{area.available} available</span>
                    </div>
                    <div style={{ height: 12, background: "#26354a", borderRadius: 20, marginTop: 8, overflow: "hidden" }}>
                      <div
                        style={{
                          width: `${area.rate}%`,
                          height: "100%",
                          background: area.rate >= 80 ? "#ef4444" : area.rate >= 50 ? "#f59e0b" : "#22c55e",
                        }}
                      />
                    </div>
                    <small style={{ color: "#94a3b8" }}>
                      Occupied/Booked: {area.occupied + area.booked} / {area.total} · Utilization: {area.rate}%
                    </small>
                  </div>
                ))}
              </div>

              <div style={styles.card}>
                <h2>🚨 Smart Alerts</h2>
                {alerts.map((alert, i) => (
                  <div
                    key={i}
                    style={{
                      background: "#0b1120",
                      border: "1px solid #26354a",
                      borderRadius: 10,
                      padding: 14,
                      marginTop: 10,
                    }}
                  >
                    {alert}
                  </div>
                ))}
              </div>

              <div style={styles.card}>
                <h2>💡 Smart Recommendation</h2>
                <p>
                  {stats.available === 0
                    ? "All parking slots are full. Please wait or check again later."
                    : `Recommended parking area: ${bestArea?.area || "Parking A"}. Choose the area with the most available slots.`}
                </p>
                {bestArea && bestArea.available > 0 && (
                  <button
                    style={btn(true)}
                    onClick={() => {
                      setSelectedArea(bestArea.area);
                      setPage("Parking");
                    }}
                  >
                    Go to {bestArea.area}
                  </button>
                )}
              </div>

              <div style={styles.card}>
                <h2>ℹ️ About These Predictions</h2>
                <p>
                  Predictions are automatically calculated using current parking availability, occupancy, booking information, and parking history.
                </p>
                <p style={{ color: "#94a3b8" }}>
                  Demand, congestion, waiting time, peak hours, and recommended parking areas update as parking activity changes.
                </p>
              </div>
            </div>
          )}
        </main>

        <footer
          style={{
            textAlign: "center",
            padding: 20,
            color: "#64748b",
            borderTop: "1px solid #25334a",
            marginTop: "auto",
          }}
        >
          ParkSmart AI · Smart Parking Management System
        </footer>
      </div>
    </div>
  );
}

export default App;
