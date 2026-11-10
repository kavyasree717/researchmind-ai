
import { useEffect, useState } from "react";
import { Navigate, Outlet } from "react-router-dom";
import api from "../services/api";

function ProtectedRoute() {
  const [checking, setChecking] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function restoreSession() {
      try {
        const token = localStorage.getItem("access_token");

        if (token) {
          // Check whether the existing access token is valid.
          // If expired, the Axios interceptor will try refreshing it.
          await api.get("/auth/me");
        } else {
          // No access token? Try restoring the session using
          // the HttpOnly refresh cookie.
          const response = await api.post("/auth/refresh", {});

          localStorage.setItem(
            "access_token",
            response.data.access_token
          );
        }

        if (isMounted) {
          setAuthenticated(true);
        }
      } catch (error) {
        console.log("Session restoration failed:", error);

        localStorage.removeItem("access_token");

        if (isMounted) {
          setAuthenticated(false);
        }
      } finally {
        if (isMounted) {
          setChecking(false);
        }
      }
    }

    restoreSession();

    return () => {
      isMounted = false;
    };
  }, []);

  // Wait until the session check finishes.
  if (checking) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p>Restoring your session...</p>
      </div>
    );
  }

  // Redirect only when the session cannot be restored.
  if (!authenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

export default ProtectedRoute;
