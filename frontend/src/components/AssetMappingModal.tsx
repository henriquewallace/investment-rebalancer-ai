import React, { useEffect, useState } from "react";

export interface AssetRule {
  ticker: string;
  name: string;
  category: string;
  asset_type: string;
  is_fractional: boolean;
  min_order_value: number;
  lot_step: number;
  price_source: string;
  aliases: string[];
  active: boolean;
}

interface AssetMappingModalProps {
  isOpen: boolean;
  onClose: () => void;
  unmappedAssets: string[];
  onMappingUpdated: () => void;
}

export const AssetMappingModal: React.FC<AssetMappingModalProps> = ({
  isOpen,
  onClose,
  unmappedAssets,
  onMappingUpdated,
}) => {
  const [rules, setRules] = useState<AssetRule[]>([]);
  const [source, setSource] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("TODAS");
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Editing / New Rule State
  const [editingRule, setEditingRule] = useState<AssetRule | null>(null);
  const [aliasesInput, setAliasesInput] = useState<string>("");

  // Quick link alias state for unmapped items
  const [selectedTargetTicker, setSelectedTargetTicker] = useState<Record<string, string>>({});

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchMapping = async (refresh = false) => {
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/assets/mapping?refresh=${refresh}`);
      const data = await res.json();
      if (res.ok) {
        setRules(data.items || []);
        setSource(data.source || "");
      }
    } catch (err: any) {
      setFeedback({ type: "error", text: "Erro ao carregar catálogo de ativos." });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchMapping(true);
      setFeedback(null);
      setEditingRule(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleLinkAlias = async (rawName: string) => {
    const target = selectedTargetTicker[rawName];
    if (!target) {
      setFeedback({ type: "error", text: "Selecione um ticker existente para vincular." });
      return;
    }
    setFeedback(null);
    try {
      const res = await fetch(`${apiUrl}/api/v1/assets/alias`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker: target, alias: rawName }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Falha ao vincular alias");
      setFeedback({
        type: "success",
        text: `'${rawName}' vinculado como sinônimo de ${target} na planilha!`,
      });
      await fetchMapping(true);
      onMappingUpdated();
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message });
    }
  };

  const handleStartNewFromUnmapped = (rawName: string) => {
    setEditingRule({
      ticker: rawName.trim().toUpperCase(),
      name: rawName.trim(),
      category: "Ações",
      asset_type: "STOCK",
      is_fractional: false,
      min_order_value: 0,
      lot_step: 1,
      price_source: "brapi",
      aliases: [rawName.trim()],
      active: true,
    });
    setAliasesInput(rawName.trim());
  };

  const handleStartEdit = (rule: AssetRule) => {
    setEditingRule({ ...rule });
    setAliasesInput(rule.aliases.join(" | "));
    setFeedback(null);
  };

  const handleSaveRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingRule) return;
    setFeedback(null);

    const parsedAliases = aliasesInput
      .split("|")
      .map((a) => a.trim())
      .filter(Boolean);

    const payload: AssetRule = {
      ...editingRule,
      ticker: editingRule.ticker.trim().toUpperCase(),
      aliases: parsedAliases,
    };

    try {
      const res = await fetch(`${apiUrl}/api/v1/assets/mapping`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Erro ao salvar ativo");
      setFeedback({
        type: "success",
        text: `Regra do ativo '${data.ticker}' salva na aba Mapeamento_Ativos!`,
      });
      setEditingRule(null);
      await fetchMapping(true);
      onMappingUpdated();
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message });
    }
  };

  const filteredRules = rules.filter((r) => {
    const matchesCat = selectedCategory === "TODAS" || r.category === selectedCategory;
    const q = searchTerm.toLowerCase();
    const matchesSearch =
      !q ||
      r.ticker.toLowerCase().includes(q) ||
      r.name.toLowerCase().includes(q) ||
      r.aliases.some((a) => a.toLowerCase().includes(q));
    return matchesCat && matchesSearch;
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
      <div className="bg-white w-full max-w-5xl rounded-2xl shadow-xl border border-slate-200 flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex justify-between items-center px-6 py-4 border-b border-slate-200">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-slate-900">
                Mapeamento e Regras de Ativos (Google Sheets)
              </h2>
              <span className="px-2 py-0.5 text-xs rounded-full bg-emerald-100 text-emerald-800 font-medium">
                Fonte: {source === "sheets" ? "Aba Mapeamento_Ativos" : "Seed Local"}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Ajuste aportes mínimos, fracionamento e sinônimos ("OU"). Alterações salvam direto na planilha.
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 text-sm font-medium px-2.5 py-1 rounded-lg border border-slate-200"
          >
            Fechar
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {feedback && (
            <div
              className={`p-3 rounded-lg text-xs font-medium border ${
                feedback.type === "success"
                  ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                  : "bg-red-50 text-red-700 border-red-200"
              }`}
            >
              {feedback.text}
            </div>
          )}

          {/* Unmapped Pending Section */}
          {unmappedAssets.length > 0 && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-amber-900">
                  Ativos Não Mapeados ({unmappedAssets.length}) — Simulação Bloqueada
                </h3>
                <span className="text-xs text-amber-700">
                  Vincule a um ativo existente ou cadastre como novo para liberar a simulação
                </span>
              </div>

              <div className="space-y-2">
                {unmappedAssets.map((rawName) => (
                  <div
                    key={rawName}
                    className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 bg-white p-3 rounded-lg border border-amber-200"
                  >
                    <div>
                      <span className="text-xs font-mono font-bold text-slate-900 bg-slate-100 px-2 py-1 rounded">
                        {rawName}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      <select
                        value={selectedTargetTicker[rawName] || ""}
                        onChange={(e) =>
                          setSelectedTargetTicker((prev) => ({
                            ...prev,
                            [rawName]: e.target.value,
                          }))
                        }
                        className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white"
                      >
                        <option value="">Selecionar ativo existente...</option>
                        {rules.map((r) => (
                          <option key={r.ticker} value={r.ticker}>
                            {r.ticker} - {r.name}
                          </option>
                        ))}
                      </select>

                      <button
                        type="button"
                        onClick={() => handleLinkAlias(rawName)}
                        className="px-3 py-1.5 text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
                      >
                        Vincular como Alias
                      </button>

                      <button
                        type="button"
                        onClick={() => handleStartNewFromUnmapped(rawName)}
                        className="px-3 py-1.5 text-xs font-medium bg-slate-800 hover:bg-slate-900 text-white rounded-lg"
                      >
                        + Criar Novo Ativo
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Edit / Create Form */}
          {editingRule && (
            <form
              onSubmit={handleSaveRule}
              className="p-4 bg-slate-50 border border-slate-300 rounded-xl space-y-4"
            >
              <div className="flex justify-between items-center">
                <h3 className="text-sm font-bold text-slate-800">
                  Configurar Regra do Ativo: {editingRule.ticker || "Novo Ativo"}
                </h3>
                <button
                  type="button"
                  onClick={() => setEditingRule(null)}
                  className="text-xs text-slate-500 hover:text-slate-800"
                >
                  Cancelar
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
                <div>
                  <label className="block font-medium text-slate-700 mb-1">Ticker Canônico</label>
                  <input
                    type="text"
                    required
                    value={editingRule.ticker}
                    onChange={(e) => setEditingRule({ ...editingRule, ticker: e.target.value })}
                    className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="block font-medium text-slate-700 mb-1">Nome do Ativo</label>
                  <input
                    type="text"
                    required
                    value={editingRule.name}
                    onChange={(e) => setEditingRule({ ...editingRule, name: e.target.value })}
                    className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg"
                  />
                </div>

                <div>
                  <label className="block font-medium text-slate-700 mb-1">Categoria</label>
                  <select
                    value={editingRule.category}
                    onChange={(e) => setEditingRule({ ...editingRule, category: e.target.value })}
                    className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg bg-white"
                  >
                    <option value="Ações">Ações</option>
                    <option value="FIIs">FIIs</option>
                    <option value="Renda Fixa">Renda Fixa</option>
                    <option value="Alternativos">Alternativos</option>
                  </select>
                </div>

                <div>
                  <label className="block font-medium text-slate-700 mb-1">Tipo</label>
                  <select
                    value={editingRule.asset_type}
                    onChange={(e) => setEditingRule({ ...editingRule, asset_type: e.target.value })}
                    className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg bg-white"
                  >
                    <option value="STOCK">STOCK (Ação)</option>
                    <option value="FII">FII</option>
                    <option value="ETF">ETF</option>
                    <option value="CDB">CDB</option>
                    <option value="TREASURY">TREASURY (Tesouro)</option>
                    <option value="FUND">FUND (Fundo)</option>
                    <option value="CRYPTO">CRYPTO</option>
                  </select>
                </div>

                <div>
                  <label className="block font-medium text-slate-700 mb-1">
                    Aporte Mínimo (R$)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={editingRule.min_order_value}
                    onChange={(e) =>
                      setEditingRule({ ...editingRule, min_order_value: Number(e.target.value) })
                    }
                    className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg"
                  />
                </div>

                <div>
                  <label className="block font-medium text-slate-700 mb-1">Passo do Lote</label>
                  <input
                    type="number"
                    step="0.0001"
                    min="0.0001"
                    value={editingRule.lot_step}
                    onChange={(e) =>
                      setEditingRule({ ...editingRule, lot_step: Number(e.target.value) })
                    }
                    className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg"
                  />
                </div>

                <div className="flex items-center pt-5">
                  <label className="inline-flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={editingRule.is_fractional}
                      onChange={(e) =>
                        setEditingRule({ ...editingRule, is_fractional: e.target.checked })
                      }
                      className="rounded border-slate-300"
                    />
                    <span className="font-medium text-slate-700">Aceita Fração</span>
                  </label>
                </div>

                <div className="sm:col-span-4">
                  <label className="block font-medium text-slate-700 mb-1">
                    Sinônimos / Aliases (separados por |)
                  </label>
                  <input
                    type="text"
                    value={aliasesInput}
                    onChange={(e) => setAliasesInput(e.target.value)}
                    placeholder="Ex: CDB DO DAYCOVAL | CDB DO DAYCOVAL, CDB DO BMG OU TESOURO RESERVA"
                    className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg font-mono"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2">
                <button
                  type="submit"
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium rounded-lg"
                >
                  Salvar na Planilha (Mapeamento_Ativos)
                </button>
              </div>
            </form>
          )}

          {/* Filter & Search Bar */}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
            <div className="flex flex-wrap gap-1.5">
              {["TODAS", "Ações", "FIIs", "Renda Fixa", "Alternativos"].map((cat) => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={`px-3 py-1 text-xs font-medium rounded-lg transition ${
                    selectedCategory === cat
                      ? "bg-slate-900 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <input
                type="text"
                placeholder="Buscar ticker, nome ou alias..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full sm:w-64 px-3 py-1.5 text-xs border border-slate-300 rounded-lg"
              />
              <button
                type="button"
                onClick={() =>
                  handleStartEdit({
                    ticker: "",
                    name: "",
                    category: "Ações",
                    asset_type: "STOCK",
                    is_fractional: false,
                    min_order_value: 0,
                    lot_step: 1,
                    price_source: "brapi",
                    aliases: [],
                    active: true,
                  })
                }
                className="px-3 py-1.5 text-xs font-medium bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg whitespace-nowrap"
              >
                + Novo Ativo
              </button>
            </div>
          </div>

          {/* Rules Table */}
          <div className="border border-slate-200 rounded-xl overflow-hidden">
            <table className="min-w-full divide-y divide-slate-200 text-xs">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-slate-600">Ticker</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-600">Categoria</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-600">Tipo</th>
                  <th className="px-3 py-2 text-right font-medium text-slate-600">Aporte Mín.</th>
                  <th className="px-3 py-2 text-center font-medium text-slate-600">Fracionável</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-600">Aliases / "OU"</th>
                  <th className="px-3 py-2 text-right font-medium text-slate-600">Ação</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-6 text-center text-slate-400">
                      Carregando mapeamento da planilha...
                    </td>
                  </tr>
                ) : filteredRules.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-6 text-center text-slate-400">
                      Nenhum ativo encontrado.
                    </td>
                  </tr>
                ) : (
                  filteredRules.map((rule) => (
                    <tr key={rule.ticker} className="hover:bg-slate-50">
                      <td className="px-3 py-2">
                        <div className="font-bold text-slate-900">{rule.ticker}</div>
                        <div className="text-[11px] text-slate-400">{rule.name}</div>
                      </td>
                      <td className="px-3 py-2 text-slate-600">{rule.category}</td>
                      <td className="px-3 py-2">
                        <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-mono text-[11px]">
                          {rule.asset_type}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right font-medium text-slate-900">
                        R$ {rule.min_order_value.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                      </td>
                      <td className="px-3 py-2 text-center">
                        {rule.is_fractional ? (
                          <span className="text-emerald-600 font-medium">Sim</span>
                        ) : (
                          <span className="text-slate-400">Lote Inteiro</span>
                        )}
                      </td>
                      <td className="px-3 py-2 max-w-xs truncate text-slate-500 font-mono text-[11px]">
                        {rule.aliases.join(" | ")}
                      </td>
                      <td className="px-3 py-2 text-right">
                        <button
                          onClick={() => handleStartEdit(rule)}
                          className="text-blue-600 hover:text-blue-800 font-medium"
                        >
                          Editar
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

