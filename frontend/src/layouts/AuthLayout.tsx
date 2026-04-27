import { Outlet } from "react-router-dom";

export function AuthLayout() {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(166,200,255,0.35),_transparent_35%),linear-gradient(180deg,#F8FAFF_0%,#FFFFFF_100%)]">
      <Outlet />
    </div>
  );
}
