/**
 * Application sidebar — main navigation.
 * Provides navigation between Dashboard, Patients, and Analysis views.
 */

"use client";

interface SidebarProps {
  currentPage: string;
  onNavigate: (page: string) => void;
  collapsed: boolean;
  onToggle: () => void;
}

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: "📊" },
  { id: "patients", label: "Patients", icon: "👤" },
  { id: "analyze", label: "New Analysis", icon: "🔬" },
];

export default function Sidebar({ currentPage, onNavigate, collapsed, onToggle }: SidebarProps) {
  return (
    <aside className={`fixed left-0 top-0 h-full bg-surface-card border-r border-surface-border
                       transition-all duration-300 z-30 flex flex-col
                       ${collapsed ? "w-16" : "w-60"}`}>
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 h-16 border-b border-surface-border">
        <div className="w-8 h-8 rounded-lg bg-brand-500 flex items-center justify-center
                        text-white font-bold text-sm flex-shrink-0">
          S
        </div>
        {!collapsed && (
          <div>
            <div className="text-white font-bold text-sm">Synapse-D</div>
            <div className="text-gray-500 text-[10px]">Brain Digital Twin</div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-2 space-y-1">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            onClick={() => onNavigate(item.id)}
            className={`w-full sidebar-link ${currentPage === item.id ? "sidebar-link-active" : ""}`}
          >
            <span className="text-lg">{item.icon}</span>
            {!collapsed && <span>{item.label}</span>}
          </button>
        ))}
      </nav>

      {/* Collapse toggle */}
      <button
        onClick={onToggle}
        className="p-4 text-gray-500 hover:text-white transition-colors border-t border-surface-border"
      >
        {collapsed ? "→" : "← 접기"}
      </button>

      {/* Version */}
      {!collapsed && (
        <div className="px-4 py-3 text-[10px] text-gray-600 border-t border-surface-border">
          Research Use Only (RUO) v0.1.0
        </div>
      )}
    </aside>
  );
}
