import React, { useState } from "react";

interface LoginFormProps {
  onSuccess: (token: string) => void;
}

export const LoginForm: React.FC<LoginFormProps> = ({ onSuccess }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        throw new Error("Falha na autenticação");
      }

      const data = await response.json();
      sessionStorage.setItem("auth_token", data.access_token);
      onSuccess(data.access_token);
    } catch (err: any) {
      setError(err.message || "Erro ao conectar");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md p-6 bg-white rounded-xl shadow-md border border-slate-100">
      <h2 className="text-xl font-bold text-slate-800 mb-4">Autenticação Transparente</h2>
      <p className="text-sm text-slate-500 mb-6">
        Insira suas credenciais da plataforma para sincronizar sua carteira recomendada. Credenciais são efêmeras.
      </p>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">E-mail</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="usuario@email.com"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Senha</label>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="••••••••"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium rounded-lg transition"
        >
          {loading ? "Autenticando..." : "Entrar e Sincronizar"}
        </button>

        <div className="pt-2 text-center">
          <button
            type="button"
            onClick={() => {
              sessionStorage.setItem("auth_token", "dev_token_bypass");
              onSuccess("dev_token_bypass");
            }}
            className="text-xs text-slate-500 hover:text-slate-800 underline"
          >
            Acessar sem Login (Modo Teste / Google Sheets)
          </button>
        </div>
      </form>
    </div>
  );
};

