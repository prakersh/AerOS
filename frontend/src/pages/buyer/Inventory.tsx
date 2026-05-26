import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface Category {
  id: number;
  name: string;
}

interface SkuItem {
  id: number;
  code: string;
  name: string;
  category: string;
  category_id: number;
  unit: string;
  last_price: number | null;
  reorder_point: number;
}

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

function formatCurrency(amount: number | null): string {
  if (amount == null) return "--";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
  }).format(amount);
}

/* ------------------------------------------------------------------ */
/* Main Component                                                      */
/* ------------------------------------------------------------------ */

export default function Inventory() {
  const [activeCategoryId, setActiveCategoryId] = useState<number | null>(null);
  const [search, setSearch] = useState("");

  /* Fetch categories */
  const { data: categories = [] } = useQuery<Category[]>({
    queryKey: ["buyer", "categories"],
    queryFn: () => api.get<Category[]>("/api/buyer/categories"),
  });

  /* Fetch inventory (scoped to category when selected) */
  const { data: inventory = [], isLoading, error } = useQuery<SkuItem[]>({
    queryKey: ["buyer", "inventory", activeCategoryId],
    queryFn: () => {
      const path =
        activeCategoryId != null
          ? `/api/buyer/inventory?category_id=${activeCategoryId}`
          : "/api/buyer/inventory";
      return api.get<SkuItem[]>(path);
    },
  });

  /* Local search filter */
  const filtered = useMemo(() => {
    if (!search.trim()) return inventory;
    const q = search.toLowerCase();
    return inventory.filter(
      (item) =>
        item.code.toLowerCase().includes(q) ||
        item.name.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q),
    );
  }, [inventory, search]);

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-zinc-100">Inventory</h1>
        <p className="mt-1 text-sm text-zinc-500">
          SKU catalog and stock management.
        </p>
      </div>

      {/* Category Tabs */}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setActiveCategoryId(null)}
          className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
            activeCategoryId === null
              ? "bg-indigo-600 text-white"
              : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200"
          }`}
        >
          All
        </button>
        {categories.map((cat) => (
          <button
            key={cat.id}
            type="button"
            onClick={() => setActiveCategoryId(cat.id)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              activeCategoryId === cat.id
                ? "bg-indigo-600 text-white"
                : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200"
            }`}
          >
            {cat.name}
          </button>
        ))}
      </div>

      {/* Search */}
      <div>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by code, name, or category..."
          className="w-full max-w-md rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        />
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-600 border-t-indigo-500" />
          <span className="ml-3 text-sm text-zinc-500">Loading inventory...</span>
        </div>
      )}

      {/* Error */}
      {error && !isLoading && (
        <div className="rounded-xl border border-red-800/50 bg-red-900/20 p-4">
          <p className="text-sm text-red-400">
            Failed to load inventory. Please try again.
          </p>
        </div>
      )}

      {/* Table */}
      {!isLoading && !error && (
        <div className="overflow-x-auto rounded-xl border border-zinc-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 bg-zinc-900">
                <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400">
                  Code
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400">
                  Name
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400">
                  Category
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400">
                  Unit
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-zinc-400">
                  Last Price
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-zinc-400">
                  Reorder Point
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-8 text-center text-sm text-zinc-500"
                  >
                    {search.trim()
                      ? "No items match your search."
                      : "No inventory items found."}
                  </td>
                </tr>
              ) : (
                filtered.map((item) => (
                  <tr
                    key={item.id}
                    className="border-b border-zinc-800/50 hover:bg-zinc-800/30"
                  >
                    <td className="px-4 py-3 font-mono text-xs text-indigo-400">
                      {item.code}
                    </td>
                    <td className="px-4 py-3 text-zinc-200">{item.name}</td>
                    <td className="px-4 py-3">
                      <span className="rounded-full bg-zinc-800 px-2.5 py-0.5 text-xs text-zinc-400">
                        {item.category}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-zinc-400">{item.unit}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-zinc-300">
                      {formatCurrency(item.last_price)}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-zinc-300">
                      {item.reorder_point}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
