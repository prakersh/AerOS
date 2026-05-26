import { useParams } from "react-router-dom";

export default function VendorRFxReply() {
  const { id } = useParams<{ id: string }>();

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold text-zinc-100">RFx Reply</h1>
      <p className="mt-2 text-sm text-zinc-500">
        Submit your offer for RFx #{id}.
      </p>
    </div>
  );
}
