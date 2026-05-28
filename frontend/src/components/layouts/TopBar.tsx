import { useAuthStore } from "@/stores/auth";
import { useNavigate } from "react-router-dom";

interface TopBarProps {
  title: string;
}

export function TopBar({ title }: TopBarProps) {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-zinc-800/80 bg-zinc-950/60 px-6 backdrop-blur-sm">
      <h2 className="text-sm font-medium text-zinc-400">{title}</h2>

      <div className="flex items-center gap-3">
        {user && (
          <>
            <div className="text-right">
              <p className="text-xs font-medium text-zinc-300">
                {user.display_name}
              </p>
              <p className="text-[10px] font-medium uppercase tracking-wider text-zinc-600">{user.role}</p>
            </div>
            <div className="relative flex h-8 w-8 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white ring-2 ring-indigo-600/20">
              {user.display_name.charAt(0).toUpperCase()}
              <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-zinc-950 bg-green-500" />
            </div>
            <div className="ml-1 h-5 w-px bg-zinc-800" />
            <button
              onClick={handleLogout}
              className="rounded-md px-2.5 py-1 text-xs text-zinc-500 transition hover:bg-zinc-800 hover:text-zinc-300"
            >
              Sign out
            </button>
          </>
        )}
      </div>
    </header>
  );
}
