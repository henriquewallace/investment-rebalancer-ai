import React from "react";

export interface SimulationRow {
  ticker: string;
  asset_name: string;
  category: string;
  current_qty: number;
  target_qty_change: number;
  new_qty: number;
  unit_price: number;
  current_value: number;
  allocated_value: number;
  new_value: number;
  target_weight: number;
  new_weight: number;
  action: string;
  is_under_review?: boolean;
  ceiling_price_exceeded?: boolean;
}

interface SimulationTableProps {
  rows: SimulationRow[];
}

export const SimulationTable: React.FC<SimulationTableProps> = ({ rows }) => {
  return (
    <div className="overflow-x-auto border border-slate-200 rounded-lg">
      <table className="w-full text-left text-sm text-slate-600">
        <thead className="bg-slate-50 text-slate-700 text-xs uppercase font-semibold border-b border-slate-200">
          <tr>
            <th className="px-4 py-3">Ativo</th>
            <th className="px-4 py-3">Categoria</th>
            <th className="px-4 py-3 text-right">Qtd Atual</th>
            <th className="px-4 py-3 text-right">Preço Unit.</th>
            <th className="px-4 py-3 text-center">Ação</th>
            <th className="px-4 py-3 text-right">Qtd Delta</th>
            <th className="px-4 py-3 text-right">Aporte R$</th>
            <th className="px-4 py-3 text-right">Alvo %</th>
            <th className="px-4 py-3 text-right">Novo %</th>
            <th className="px-4 py-3 text-center">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.length === 0 ? (
            <tr>
              <td colSpan={10} className="px-4 py-8 text-center text-slate-400">
                Nenhum dado de simulação disponível.
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr key={row.ticker} className="hover:bg-slate-50/80 transition">
                <td className="px-4 py-3 font-medium text-slate-900">
                  <div>{row.ticker}</div>
                  <div className="text-xs text-slate-400">{row.asset_name}</div>
                </td>
                <td className="px-4 py-3">{row.category}</td>
                <td className="px-4 py-3 text-right">{row.current_qty}</td>
                <td className="px-4 py-3 text-right">
                  {row.unit_price.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
                </td>
                <td className="px-4 py-3 text-center">
                  <span
                    className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${
                      row.action === "BUY"
                        ? "bg-green-100 text-green-700"
                        : row.action === "SELL"
                        ? "bg-red-100 text-red-700"
                        : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {row.action}
                  </span>
                </td>
                <td className="px-4 py-3 text-right font-medium">
                  {row.target_qty_change > 0 ? `+${row.target_qty_change}` : row.target_qty_change}
                </td>
                <td className="px-4 py-3 text-right font-semibold text-slate-900">
                  {row.allocated_value.toLocaleString("pt-BR", {
                    style: "currency",
                    currency: "BRL",
                  })}
                </td>
                <td className="px-4 py-3 text-right">{(row.target_weight * 100).toFixed(1)}%</td>
                <td className="px-4 py-3 text-right">{(row.new_weight * 100).toFixed(1)}%</td>
                <td className="px-4 py-3 text-center">
                  {row.is_under_review && (
                    <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded">
                      Revisão
                    </span>
                  )}
                  {row.ceiling_price_exceeded && (
                    <span className="text-xs bg-rose-100 text-rose-700 px-2 py-0.5 rounded">
                      Preço Teto
                    </span>
                  )}
                  {!row.is_under_review && !row.ceiling_price_exceeded && (
                    <span className="text-xs text-slate-400">OK</span>
                  )}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
};

