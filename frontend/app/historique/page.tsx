"use client";

import { useEffect, useState } from "react";
import { RotateCcw } from "lucide-react";
import { ErrorBox, Loading, PageHeader } from "@/components/async-state";
import { Button, Card, Input, SearchInput, Select, StatusBadge, SuccessBanner } from "@/components/ui";
import { apiGet, apiPost } from "@/lib/api";
import type { ActionRow } from "@/lib/types";

export default function HistoriquePage() {
  const [rows, setRows] = useState<ActionRow[]>([]);
  const [action, setAction] = useState("Tous");
  const [search, setSearch] = useState("");
  const [actor, setActor] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = () => apiGet<ActionRow[]>("/history?limit=300").then(setRows).catch((err) => setError(err.message));
  useEffect(() => { load(); }, []);

  if (error) return <ErrorBox message={error} />;
  if (!rows) return <Loading />;

  const actions = Array.from(new Set(rows.map((row) => row.action_label)));
  const filtered = rows.filter((row) => {
    const actionOk = action === "Tous" || row.action_label === action;
    const haystack = `${row.action_label} ${row.personne || ""} ${row.sticker || ""} ${row.nom || ""}`.toLowerCase();
    return actionOk && haystack.includes(search.toLowerCase());
  });

  async function undo(row: ActionRow) {
    await apiPost("/history/undo", { action_id: row.id, actor_name: actor });
    setMessage("Action annulée.");
    load();
  }

  async function undoBatch(batchId: string) {
    await apiPost("/history/undo-batch", { batch_id: batchId, actor_name: actor });
    setMessage("Session annulée.");
    load();
  }

  return (
    <>
      <PageHeader title="Historique" caption="Une timeline lisible des ajouts, retraits, échanges, ventes et annulations." />
      {message && <SuccessBanner>{message}</SuccessBanner>}
      <Card>
        <div className="grid gap-3 md:grid-cols-3">
          <Select value={action} onChange={(event) => setAction(event.target.value)}>
            <option>Tous</option>
            {actions.map((value) => <option key={value}>{value}</option>)}
          </Select>
          <SearchInput value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Personne, sticker, action..." />
          <Input value={actor} onChange={(event) => setActor(event.target.value)} placeholder="Annulé par, optionnel" />
        </div>
      </Card>

      <div className="mt-6 space-y-3">
        {filtered.map((row) => (
          <Card key={row.id} className="p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <div className="text-lg font-black">{row.action_label}</div>
                  {row.batch_id && <StatusBadge tone="gold">Session</StatusBadge>}
                  {row.annulable && <StatusBadge tone="green">Annulable</StatusBadge>}
                </div>
                <div className="mt-1 text-sm font-semibold text-muted">
                  {new Date(row.date).toLocaleString("fr-FR")} · {row.personne || "Groupe"} · {row.sticker || ""} {row.nom || ""}
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <StatusBadge tone="blue">{row.avant ?? ""} → {row.après ?? ""}</StatusBadge>
                {row.batch_id ? (
                  <Button variant="secondary" onClick={() => undoBatch(row.batch_id!)}>
                    <RotateCcw className="h-4 w-4" />
                    Annuler session
                  </Button>
                ) : row.annulable ? (
                  <Button variant="secondary" onClick={() => undo(row)}>
                    <RotateCcw className="h-4 w-4" />
                    Annuler
                  </Button>
                ) : null}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </>
  );
}

