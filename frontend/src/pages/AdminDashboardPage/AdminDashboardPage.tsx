import Navbar from "../../components/Navbar/Navbar";

// Placeholder - the admin dashboard (GP-62) is built out in later steps.
export default function AdminDashboardPage() {
  return (
    <div className="min-h-screen bg-canvas font-sans text-ink">
      <Navbar />

      <main className="mx-auto max-w-6xl px-8 pt-2 pb-12">
        <h1 className="text-4xl font-medium text-ink">Admin dashboard</h1>
      </main>
    </div>
  );
}
