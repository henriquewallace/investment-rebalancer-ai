import React, { useEffect, useState } from "react";
import { SimulationTable, SimulationRow } from "./SimulationTable";
import { AssetMappingModal } from "./AssetMappingModal";

interface DashboardProps {
  onLogout: () => void;
}

interface CustodyItem {
  ticker: string;
  asset_name: string;
  category: string;
  current_qty: number;
  current_price: number;
  current_total_value: number;
}

interface SheetsHealth {
  connected: boolean;
  status: string;
  message: string;
  spreadsheet_title?: string;
  worksheets?: string[];
}

export const Dashboard: React.FC<DashboardProps> = ({ onLogout }) => {
  const [investment, setInvestment] = useState<number>(5000);
  const [rebalanceMode, setRebalanceMode] = useState<"sabonete" | "cirurgico">("sabonete");
  const [rows, setRows] = useState<SimulationRow[]>([]);
  const [isSimulating, setIsSimulating] = useState(false);

  // Sheets & Mapping state
  const [sheetsHealth, setSheetsHealth] = useState<SheetsHealth | null>(null);
  const [isCheckingSheets, setIsCheckingSheets] = useState(false);
  const [custodyData, setCustodyData] = useState<{
    tab_name: string;
    total_value: number;
    assets: CustodyItem[];
  } | null>(null);
  const [isLoadingCustody, setIsLoadingCustody] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const [isMappingModalOpen, setIsMappingModalOpen] = useState(false);
  const [unmappedAssets, setUnmappedAssets] = useState<string[]>([]);
  const [mappedCatalogCount, setMappedCatalogCount] = useState<number>(0);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const checkSheetsHealth = async () => {
    setIsCheckingSheets(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/sheets/health`);
      const data = await res.json();
      setSheetsHealth(data);
    } catch (err: any) {
      setSheetsHealth({
        connected: false,
        status: "connection_error",
        message: "Falha de rede ao conectar com backend.",
      });
    } finally {
      setIsCheckingSheets(false);
    }
  };

  const fetchCatalogCount = async () => {
    try {
      const res = await fetch(`${apiUrl}/api/v1/assets/mapping`);
      if (res.ok) {
        const data = await res.json();
        setMappedCatalogCount(data.count || 0);
      }
    } catch {
      // ignore
    }
  };

  const checkResolutionForNames = async (names: string[]) => {
    if (!names.length) {
      setUnmappedAssets([]);
      return;
    }
    try {
      const res = await fetch(`${apiUrl}/api/v1/assets/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ names }),
      });
      if (res.ok) {
        const data = await res.json();
        setUnmappedAssets(data.unmapped || []);
      }
    } catch {
      // ignore
    }
  };

  const handleInitTemplate = async () => {
    setFeedbackMsg(null);
    try {
      const res = await fetch(`${apiUrl}/api/v1/sheets/template/init`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Erro ao inicializar templates");
      setFeedbackMsg({ type: "success", text: data.message || "Templates inicializados com sucesso!" });
      checkSheetsHealth();
      fetchCatalogCount();
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: err.message });
    }
  };

  const handleLoadLatestCustody = async () => {
    setIsLoadingCustody(true);
    setFeedbackMsg(null);
    try {
      const res = await fetch(`${apiUrl}/api/v1/sheets/latest-custody`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Erro ao carregar custódia");
      setCustodyData(data);
      const tickers = (data.assets || []).map((a: CustodyItem) => a.ticker);
      await checkResolutionForNames(tickers);
      setFeedbackMsg({
        type: "success",
        text: `Custódia carregada da aba '${data.tab_name}': ${data.assets.length} ativos (Total R$ ${data.total_value.toLocaleString("pt-BR", { minimumFractionDigits: 2 })})`,
      });
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: err.message });
    } finally {
      setIsLoadingCustody(false);
    }
  };

  useEffect(() => {
    checkSheetsHealth();
    fetchCatalogCount();
  }, []);

  const handleMappingUpdated = async () => {
    await fetchCatalogCount();
    if (custodyData?.assets) {
      const tickers = custodyData.assets.map((a) => a.ticker);
      await checkResolutionForNames(tickers);
    }
  };

  const handleSimulate = async () => {
    if (unmappedAssets.length > 0) return;
    setIsSimulating(true);
    try {
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
          className="px-3 py-1.5 text-sm font-medium text-slate-600 hover:text-slate-900 border border-slate-200 rounded-lg hover:bg-slate-100 transition"
        >
          Sair
        </button>
      </header>

      {/* Google Sheets Integration Card */}
      <section className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-800">Conexão Google Sheets</span>
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  sheetsHealth?.connected
                    ? "bg-green-100 text-green-800"
                    : "bg-amber-100 text-amber-800"
                }`}
              >
                {isCheckingSheets
                  ? "Verificando..."
                  : sheetsHealth?.connected
                  ? `Conectado: ${sheetsHealth.spreadsheet_title || "Planilha OK"}`
                  : `Status: ${sheetsHealth?.status || "Desconectado"}`}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              {sheetsHealth?.message || "Verificando conexão com o Google Sheets..."}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              onClick={checkSheetsHealth}
              disabled={isCheckingSheets}
              className="px-3 py-1.5 text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition"
            >
              Testar Conexão
            </button>
            <button
              onClick={() => setIsMappingModalOpen(true)}
              className="px-3 py-1.5 text-xs font-medium bg-slate-800 hover:bg-slate-900 text-white rounded-lg transition flex items-center gap-1.5"
            >
              <span>Mapeamento e Regras ({mappedCatalogCount})</span>
              {unmappedAssets.length > 0 && (
                <span className="px-1.5 py-0.2 bg-amber-400 text-slate-950 font-bold rounded-full text-[10px]">
                  {unmappedAssets.length} pendente(s)
                </span>
              )}
            </button>
            <button
              onClick={handleInitTemplate}
              disabled={!sheetsHealth?.connected}
              className="px-3 py-1.5 text-xs font-medium bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 rounded-lg transition disabled:opacity-50"
            >
              Inicializar Templates
            </button>
            <button
              onClick={handleLoadLatestCustody}
              disabled={!sheetsHealth?.connected || isLoadingCustody}
              className="px-3 py-1.5 text-xs font-medium bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition disabled:opacity-50"
            >
              {isLoadingCustody ? "Carregando..." : "Ler Última Custódia"}
            </button>
          </div>
        </div>

        {feedbackMsg && (
          <div
            className={`p-3 rounded-lg text-xs font-medium border ${
              feedbackMsg.type === "success"
                ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                : "bg-red-50 text-red-700 border-red-200"
            }`}
          >
            {feedbackMsg.text}
          </div>
        )}

        {unmappedAssets.length > 0 && (
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
            <div className="text-xs text-amber-800">
              <strong>Atenção:</strong> Existem <strong>{unmappedAssets.length}</strong> ativo(s) sem mapeamento ({unmappedAssets.join(", ")}). A simulação está bloqueada até que sejam mapeados.
            </div>
            <button
              onClick={() => setIsMappingModalOpen(true)}
              className="px-3 py-1.5 text-xs font-semibold bg-amber-600 hover:bg-amber-700 text-white rounded-lg whitespace-nowrap"
            >
              Resolver Mapeamento
            </button>
          </div>
        )}

        {/* Display custody from sheets if loaded */}
        {custodyData && (
          <div className="mt-4 pt-4 border-t border-slate-100 space-y-3">
            <div className="flex justify-between items-center text-xs text-slate-600 font-medium">
              <span>
                Aba: <strong className="text-slate-900">{custodyData.tab_name}</strong>
              </span>
              <span>
                Total em Custódia:{" "}
                <strong className="text-slate-900">
                  R$ {custodyData.total_value.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                </strong>
              </span>
            </div>

            <div className="overflow-x-auto border border-slate-200 rounded-lg max-h-60 overflow-y-auto">
              <table className="min-w-full divide-y divide-slate-200 text-xs">
                <thead className="bg-slate-50 sticky top-0">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-slate-600">Categoria</th>
                    <th className="px-3 py-2 text-left font-medium text-slate-600">Ticker</th>
                    <th className="px-3 py-2 text-left font-medium text-slate-600">Nome</th>
                    <th className="px-3 py-2 text-right font-medium text-slate-600">Qtd</th>
                    <th className="px-3 py-2 text-right font-medium text-slate-600">Preço (R$)</th>
                    <th className="px-3 py-2 text-right font-medium text-slate-600">Total (R$)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {custodyData.assets.map((item, idx) => (
                    <tr key={idx} className="hover:bg-slate-50">
                      <td className="px-3 py-1.5 text-slate-500">{item.category}</td>
                      <td className="px-3 py-1.5 font-semibold text-slate-900">{item.ticker}</td>
                      <td className="px-3 py-1.5 text-slate-600">{item.asset_name}</td>
                      <td className="px-3 py-1.5 text-right text-slate-700">{item.current_qty}</td>
                      <td className="px-3 py-1.5 text-right text-slate-700">
                        R$ {item.current_price.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                      </td>
                      <td className="px-3 py-1.5 text-right font-medium text-slate-900">
                        R$ {item.current_total_value.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>

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
            disabled={isSimulating || unmappedAssets.length > 0}
            className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-medium rounded-lg transition"
          >
            {unmappedAssets.length > 0
              ? `Bloqueado (${unmappedAssets.length} não mapeado)`
              : isSimulating
              ? "Calculando..."
              : "Simular Rebalanceamento"}
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

      <AssetMappingModal
        isOpen={isMappingModalOpen}
        onClose={() => setIsMappingModalOpen(false)}
        unmappedAssets={unmappedAssets}
        onMappingUpdated={handleMappingUpdated}
      />
    </div>
  );
};
