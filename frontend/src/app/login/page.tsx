export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background text-white">
      <div className="p-8 bg-panel rounded-lg shadow-xl border border-info/20">
        <h1 className="text-2xl font-bold mb-4">Login to DefiSys</h1>
        {/* Placeholder for NextAuth login form */}
        <button className="w-full py-2 bg-info text-background font-semibold rounded hover:bg-info/90 transition-colors">
          Sign In
        </button>
      </div>
    </div>
  );
}
