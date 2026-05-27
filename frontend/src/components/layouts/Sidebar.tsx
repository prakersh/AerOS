import { type ReactNode, createContext, useContext, useState } from "react";
import { NavLink } from "react-router-dom";

/* ------------------------------------------------------------------ */
/* Sidebar collapse context                                            */
/* ------------------------------------------------------------------ */

interface SidebarContextValue {
  collapsed: boolean;
  toggle: () => void;
}

const SidebarContext = createContext<SidebarContextValue>({
  collapsed: false,
  toggle: () => {},
});

export function useSidebar() {
  return useContext(SidebarContext);
}

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

export interface NavItem {
  label: string;
  to: string;
  icon: ReactNode;
  disabled?: boolean;
  badge?: string;
}

export interface NavSection {
  title?: string;
  items: NavItem[];
}

/* ------------------------------------------------------------------ */
/* Sidebar component                                                   */
/* ------------------------------------------------------------------ */

interface SidebarProps {
  sections: NavSection[];
  header: ReactNode;
  children: ReactNode; // main content (Outlet wrapper)
  topBar: ReactNode;
}

export function SidebarLayout({
  sections,
  header,
  children,
  topBar,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <SidebarContext.Provider
      value={{ collapsed, toggle: () => setCollapsed((c) => !c) }}
    >
      <div className="flex h-screen overflow-hidden bg-zinc-950">
        {/* Sidebar */}
        <aside
          className={`flex flex-col border-r border-zinc-800 bg-zinc-900 transition-[width] duration-200 ${
            collapsed ? "w-16" : "w-56"
          }`}
        >
          {/* Logo / header */}
          <div className="flex h-14 shrink-0 items-center border-b border-zinc-800 px-4">
            {header}
          </div>

          {/* Navigation */}
          <nav className="flex-1 overflow-y-auto px-2 py-3">
            {sections.map((section, si) => (
              <div key={si} className={si > 0 ? "mt-4" : ""}>
                {section.title && !collapsed && (
                  <p className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-widest text-zinc-600">
                    {section.title}
                  </p>
                )}
                {section.items.map((item) => (
                  <NavLink
                    key={item.label}
                    to={item.disabled ? "#" : item.to}
                    onClick={(e) => item.disabled && e.preventDefault()}
                    className={({ isActive }) =>
                      `group flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition ${
                        item.disabled
                          ? "cursor-not-allowed text-zinc-700"
                          : isActive
                            ? "bg-zinc-800 text-zinc-100"
                            : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200"
                      }`
                    }
                  >
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center">
                      {item.icon}
                    </span>
                    {!collapsed && (
                      <>
                        <span className="truncate">{item.label}</span>
                        {item.badge && (
                          <span className="ml-auto rounded-full bg-indigo-600/20 px-1.5 py-0.5 text-[10px] font-medium text-indigo-400">
                            {item.badge}
                          </span>
                        )}
                      </>
                    )}
                  </NavLink>
                ))}
              </div>
            ))}
          </nav>

          {/* Collapse toggle */}
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="flex h-10 shrink-0 items-center justify-center border-t border-zinc-800 text-zinc-500 transition hover:text-zinc-300"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <svg
              className={`h-4 w-4 transition-transform ${collapsed ? "rotate-180" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15 19l-7-7 7-7"
              />
            </svg>
          </button>
        </aside>

        {/* Main area */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {topBar}
          <main className="flex-1 overflow-y-auto">{children}</main>
        </div>
      </div>
    </SidebarContext.Provider>
  );
}
