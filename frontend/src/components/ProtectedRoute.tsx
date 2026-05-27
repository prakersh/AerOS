import { useEffect } from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "@/stores/auth";

interface ProtectedRouteProps {
  allowedRoles?: string[];
}

export default function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const { user, loading, initialized, fetchMe } = useAuthStore();

  useEffect(() => {
    if (!initialized) {
      fetchMe();
    }
  }, [initialized, fetchMe]);

  if (!initialized || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950">
        <div className="text-sm text-zinc-500">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    const dest =
      user.role === "vendor"
        ? "/vendor/inbox"
        : user.role === "admin"
          ? "/admin/dashboard"
          : "/buyer/dashboard";
    return <Navigate to={dest} replace />;
  }

  return <Outlet />;
}
