import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import {
  PageHeader,
  LoadingSpinner,
  ErrorState,
  Modal,
  DetailView,
  FilterChips,
  Toast,
} from "@/components/ui";
import { formatCurrency } from "@/lib/format";
import { useDebounce } from "@/hooks/useDebounce";

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
  category_id: number;
  unit: string;
  last_price: number | null;
  reorder_point: number;
}

/* ------------------------------------------------------------------ */
/* Main Component                                                      */
/* ------------------------------------------------------------------ */

export default function Inventory() {
  const queryClient = useQueryClient();
  const [activeCategoryId, setActiveCategoryId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search, 300);
  const [selectedItem, setSelectedItem] = useState<SkuItem | null>(null);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editForm, setEditForm] = useState({ qty: 0, target_price: 0, notes: "" });
  const [toastMessage, setToastMessage] = useState<string | null>(null);

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

  /* Build category filter options and lookup map */
  const categoryFilterOptions = useMemo(
    () => [
      { label: "All", value: "all" },
      ...categories.map((cat) => ({ label: cat.name, value: String(cat.id) })),
    ],
    [categories],
  );

  const categoryMap = useMemo(() => {
    const map = new Map<number, string>();
    for (const cat of categories) map.set(cat.id, cat.name);
    return map;
  }, [categories]);

  function getCategoryName(categoryId: number): string {
    return categoryMap.get(categoryId) ?? `Category ${categoryId}`;
  }

  /* Local search filter (debounced) */
  const filtered = useMemo(() => {
    if (!debouncedSearch.trim()) return inventory;
    const q = debouncedSearch.toLowerCase();
    return inventory.filter(
      (item) =>
        item.code.toLowerCase().includes(q) ||
        item.name.toLowerCase().includes(q) ||
        getCategoryName(item.category_id).toLowerCase().includes(q),
    );
  }, [inventory, debouncedSearch, categoryMap]);

  function openEditModal() {
    if (selectedItem) {
      setEditForm({ qty: selectedItem.reorder_point, target_price: selectedItem.last_price ?? 0, notes: "" });
    }
    setEditModalOpen(true);
  }

  const editMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { reorder_point: number; last_price: number } }) =>
      api.put(`/api/buyer/inventory/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["buyer", "inventory"] });
      setEditModalOpen(false);
      setSelectedItem(null);
      setToastMessage("Item updated successfully");
    },
    onError: () => setToastMessage("Failed to update item"),
  });

  function handleEditSave() {
    if (!selectedItem) return;
    editMutation.mutate({
      id: selectedItem.id,
      data: { reorder_point: editForm.qty, last_price: editForm.target_price },
    });
  }

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Inventory"
        subtitle="SKU catalog and stock management."
      />

      {/* Category Tabs */}
      <FilterChips
        options={categoryFilterOptions}
        active={activeCategoryId != null ? String(activeCategoryId) : "all"}
        onChange={(val) => setActiveCategoryId(val === "all" ? null : Number(val))}
      />

      {/* Search */}
      <div className="relative max-w-md">
        <svg
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
        </svg>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by code, name, or category..."
          className="w-full rounded-lg border border-zinc-700 bg-zinc-800 py-2 pl-9 pr-4 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        />
      </div>

      {/* Loading */}
      {isLoading && <LoadingSpinner message="Loading inventory..." />}

      {/* Error */}
      {error && !isLoading && (
        <ErrorState message="Failed to load inventory. Please try again." />
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
                    {debouncedSearch.trim()
                      ? "No items match your search."
                      : "No inventory items found."}
                  </td>
                </tr>
              ) : (
                filtered.map((item) => (
                  <tr
                    key={item.id}
                    className="cursor-pointer border-b border-zinc-800/50 hover:bg-zinc-800/30"
                    onClick={() => setSelectedItem(item)}
                  >
                    <td className="px-4 py-3 font-mono text-xs text-indigo-400">
                      {item.code}
                    </td>
                    <td className="px-4 py-3 text-zinc-200">{item.name}</td>
                    <td className="px-4 py-3">
                      <span className="rounded-full bg-zinc-800 px-2.5 py-0.5 text-xs text-zinc-400">
                        {getCategoryName(item.category_id)}
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

      {/* Item Detail Modal */}
      <Modal
        open={!!selectedItem && !editModalOpen}
        onClose={() => setSelectedItem(null)}
        title={selectedItem?.name ?? "Item Details"}
        size="md"
      >
        {selectedItem && (
          <>
            <DetailView
              items={[
                { label: "Code", value: selectedItem.code },
                { label: "Name", value: selectedItem.name },
                { label: "Category", value: getCategoryName(selectedItem.category_id) },
                { label: "Unit", value: selectedItem.unit },
                { label: "Last Price", value: formatCurrency(selectedItem.last_price) },
                { label: "Reorder Point", value: String(selectedItem.reorder_point) },
              ]}
              columns={2}
            />
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={openEditModal}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500"
              >
                Edit Item
              </button>
            </div>
          </>
        )}
      </Modal>

      {/* Edit Item Modal */}
      <Modal
        open={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        title="Edit Item"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-zinc-500">Quantity</label>
            <input
              type="number"
              value={editForm.qty}
              onChange={(e) => setEditForm((f) => ({ ...f, qty: Number(e.target.value) }))}
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-500">Target Price</label>
            <input
              type="number"
              step="0.01"
              value={editForm.target_price}
              onChange={(e) => setEditForm((f) => ({ ...f, target_price: Number(e.target.value) }))}
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-500">Notes</label>
            <textarea
              value={editForm.notes}
              onChange={(e) => setEditForm((f) => ({ ...f, notes: e.target.value }))}
              rows={3}
              className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => setEditModalOpen(false)}
              className="rounded-lg border border-zinc-700 px-4 py-2 text-sm font-medium text-zinc-300 transition hover:bg-zinc-800"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleEditSave}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500"
            >
              Save
            </button>
          </div>
        </div>
      </Modal>

      {/* Toast */}
      {toastMessage && (
        <Toast message={toastMessage} onClose={() => setToastMessage(null)} />
      )}
    </div>
  );
}
