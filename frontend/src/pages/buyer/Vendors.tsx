import { useState, useMemo } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/api/client";
import {
  StatusBadge,
  PageHeader,
  LoadingSpinner,
  ErrorState,
  EmptyState,
  Modal,
  DetailView,
  StarRating,
  FilterChips,
  Toast,
} from "@/components/ui";
import type { Vendor, KycStatus } from "@/types";

/* ------------------------------------------------------------------ */
/* Filter options                                                       */
/* ------------------------------------------------------------------ */

const KYC_FILTER_OPTIONS = [
  { label: "All", value: "all" },
  { label: "Approved", value: "approved" },
  { label: "Pending", value: "pending" },
  { label: "Rejected", value: "rejected" },
];

/* ------------------------------------------------------------------ */
/* Main Component                                                      */
/* ------------------------------------------------------------------ */

export default function Vendors() {
  const [kycFilter, setKycFilter] = useState("all");
  const [selectedVendor, setSelectedVendor] = useState<Vendor | null>(null);
  const [contactModalOpen, setContactModalOpen] = useState(false);
  const [contactMessage, setContactMessage] = useState("");
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const {
    data: vendors = [],
    isLoading,
    error,
  } = useQuery<Vendor[]>({
    queryKey: ["buyer", "vendors"],
    queryFn: () => api.get<Vendor[]>("/api/buyer/vendors"),
  });

  /* Filtered vendors */
  const filteredVendors = useMemo(
    () =>
      kycFilter === "all"
        ? vendors
        : vendors.filter((v) => v.kyc_status === (kycFilter as KycStatus)),
    [vendors, kycFilter],
  );

  function openContactModal() {
    setContactMessage("");
    setContactModalOpen(true);
  }

  const contactMutation = useMutation({
    mutationFn: ({ vendorId, message }: { vendorId: number; message: string }) =>
      api.post(`/api/buyer/vendors/${vendorId}/contact`, { message }),
    onSuccess: () => {
      setContactModalOpen(false);
      setSelectedVendor(null);
      setToastMessage("Message sent");
    },
    onError: () => setToastMessage("Failed to send message"),
  });

  function handleSendContact() {
    if (!selectedVendor || !contactMessage.trim()) return;
    contactMutation.mutate({ vendorId: selectedVendor.id, message: contactMessage });
  }

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Vendors"
        subtitle="Vendor directory and performance tracking."
      />

      {/* Loading */}
      {isLoading && <LoadingSpinner message="Loading vendors..." />}

      {/* Error */}
      {error && !isLoading && (
        <ErrorState message="Failed to load vendors. Please try again." />
      )}

      {/* KYC Filter */}
      {!isLoading && !error && (
        <FilterChips
          options={KYC_FILTER_OPTIONS}
          active={kycFilter}
          onChange={setKycFilter}
        />
      )}

      {/* Vendor Cards Grid */}
      {!isLoading && !error && (
        <>
          {filteredVendors.length === 0 ? (
            <EmptyState
              title="No vendors found"
              description={
                kycFilter !== "all"
                  ? "No vendors match the selected KYC filter."
                  : "No vendors have been added yet."
              }
              action={
                kycFilter !== "all"
                  ? { label: "Clear filter", onClick: () => setKycFilter("all") }
                  : undefined
              }
            />
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {filteredVendors.map((vendor) => (
                <button
                  key={vendor.id}
                  type="button"
                  onClick={() => setSelectedVendor(vendor)}
                  className="rounded-xl border border-zinc-800 bg-zinc-900 p-5 text-left transition-all duration-200 hover:border-zinc-700 hover:bg-zinc-800/50 hover:shadow-lg hover:shadow-black/20"
                >
                  {/* Name + KYC */}
                  <div className="flex items-start justify-between">
                    <div className="min-w-0">
                      <h3 className="truncate text-sm font-medium text-zinc-200">
                        {vendor.name}
                      </h3>
                      <p className="mt-0.5 truncate text-xs text-zinc-500">
                        {vendor.primary_email ?? vendor.email}
                      </p>
                    </div>
                    <StatusBadge status={vendor.kyc_status} variant="kyc" />
                  </div>

                  {/* Categories */}
                  <div className="mt-3">
                    <div className="flex flex-wrap gap-1.5">
                      {(vendor.category_ids_csv ?? vendor.categories ?? "")
                        .split(",")
                        .filter(Boolean)
                        .map((catId) => (
                          <span
                            key={catId.trim()}
                            className="rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] text-zinc-400"
                          >
                            Category {catId.trim()}
                          </span>
                        ))}
                    </div>
                  </div>

                  {/* Score + Rank */}
                  <div className="mt-4 flex items-center justify-between">
                    <StarRating score={vendor.performance_score} />
                    <span className="rounded bg-zinc-800 px-2 py-0.5 text-[10px] font-medium text-zinc-500">
                      Rank #{vendor.preferred_rank}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </>
      )}

      {/* Vendor Detail Modal */}
      <Modal
        open={!!selectedVendor && !contactModalOpen}
        onClose={() => setSelectedVendor(null)}
        title={selectedVendor?.name ?? "Vendor Details"}
        size="md"
      >
        {selectedVendor && (
          <div className="space-y-4">
            <DetailView
              items={[
                { label: "Name", value: selectedVendor.name },
                { label: "Email", value: selectedVendor.primary_email ?? selectedVendor.email ?? "--" },
                { label: "KYC Status", value: selectedVendor.kyc_status },
                { label: "Performance Score", value: `${selectedVendor.performance_score.toFixed(1)} / 5` },
                { label: "Preferred Rank", value: `#${selectedVendor.preferred_rank}` },
                {
                  label: "Categories",
                  value: (selectedVendor.category_ids_csv ?? selectedVendor.categories ?? "")
                    .split(",")
                    .filter(Boolean)
                    .join(", ") || "--",
                },
              ]}
              columns={2}
            />
            <div>
              <label className="block text-xs font-medium text-zinc-500">Star Rating</label>
              <div className="mt-1">
                <StarRating score={selectedVendor.performance_score} />
              </div>
            </div>
            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={openContactModal}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500"
              >
                Contact Vendor
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Contact Vendor Modal */}
      <Modal
        open={contactModalOpen}
        onClose={() => setContactModalOpen(false)}
        title="Contact Vendor"
        size="md"
      >
        {selectedVendor && (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-zinc-500">Vendor Name</label>
              <p className="mt-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200">
                {selectedVendor.name}
              </p>
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-500">Email</label>
              <p className="mt-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200">
                {selectedVendor.primary_email ?? selectedVendor.email ?? "--"}
              </p>
            </div>
            <div>
              <label className="block text-xs font-medium text-zinc-500">Message</label>
              <textarea
                value={contactMessage}
                onChange={(e) => setContactMessage(e.target.value)}
                rows={4}
                placeholder="Type your message..."
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setContactModalOpen(false)}
                className="rounded-lg border border-zinc-700 px-4 py-2 text-sm font-medium text-zinc-300 transition hover:bg-zinc-800"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSendContact}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500"
              >
                Send
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Toast */}
      {toastMessage && (
        <Toast message={toastMessage} onClose={() => setToastMessage(null)} />
      )}
    </div>
  );
}
