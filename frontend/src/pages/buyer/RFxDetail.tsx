import { useParams } from "react-router-dom";

export default function RFxDetail() {
  const { id } = useParams<{ id: string }>();

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold text-zinc-100">RFx Detail</h1>
      <p className="mt-2 text-sm text-zinc-500">
        RFx #{id} -- line items, vendor offers, and comparison matrix.
      </p>
    </div>
  );
}
