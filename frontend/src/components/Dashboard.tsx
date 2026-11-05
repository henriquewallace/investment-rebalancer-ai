import React, { useState } from "react";
import { SimulationTable, SimulationRow } from "./SimulationTable";

interface DashboardProps {
  onLogout: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onLogout }) => {
  const [investment, setInvestment] = useState<number>(5000);
  const [rebalanceMode, setRebalanceMode] = useState<"sabonete" | "cirurgico">("sabonete");
  const [rows, setRows] = useState<SimulationRow[]>([]);
  const [isSimulating, setIsSimulating] = useState(false);

  const handleSimulate = async () => {
    setIsSimulating(true);
    try {
      // Endpoint will be wired up with backend in subsequent phases
      setRows([]);
    } finally {
      setIsSimulating(false);
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto p-6 space-y-6">
      <header className="flex justify-between items-center pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Investment Rebalancer AI</h1>
          <p className="text-sm text-slate-500">Otimização determinística de alocação de aportes</p>
        </div>
        <button
          onClick={onLogout}
          className="px-3 py-1.5 text-sm font-medium text-slate-600 hover:text-slate-900 border border-slate-200 rounded-lg"
        >
          Sair
        </button>
      </header>

      {/* Controls Bar */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Valor do Aporte (R$)
          </label>
          <input
            type="number"
            min="0"
            step="100"
            value={investment}
            onChange={(e) => setInvestment(Number(e.target.value))}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Modo de Rebalanceamento
          </label>
          <select
            value={rebalanceMode}
            onChange={(e) => setRebalanceMode(e.target.value as "sabonete" | "cirurgico")}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="sabonete">Sabonete (Apenas Compras e Vendas Zeradas)</option>
            <option value="cirurgico">Cirúrgico (Vendas Parciais Permitidas)</option>
          </select>
        </div>

        <div className="flex items-end">
          <button
            onClick={handleSimulate}
            disabled={isSimulating}
            className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-medium rounded-lg transition"
          >
            {isSimulating ? "Calculando..." : "Simular Rebalanceamento"}
          </button>
        </div>
      </div>

      {/* Table Section */}
      <section className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-bold text-slate-800">Resultado da Alocação</h2>
          <button
            disabled={rows.length === 0}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white font-medium text-sm rounded-lg transition"
          >
            Confirmar e Salvar no Google Sheets
          </button>
        </div>

        <SimulationTable rows={rows} />
      </section>
    </div>
  );
};

