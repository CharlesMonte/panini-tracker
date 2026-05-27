"use client";

import { useEffect, useState } from "react";
import { ErrorBox, Loading, PageHeader } from "@/components/async-state";
import { Button, Card, DataTable, Input, MetricCard, SearchInput, Select, SuccessBanner } from "@/components/ui";
import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api";
import type { Sticker } from "@/lib/types";

export default function AdminPage() {
  const [data, setData] = useState<any>(null);
  const [actor, setActor] = useState("");
  const [newName, setNewName] = useState("");
  const [confirm, setConfirm] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [stickerQuery, setStickerQuery] = useState("");
  const [stickers, setStickers] = useState<Sticker[]>([]);
  const [selectedStickerId, setSelectedStickerId] = useState<number>(0);
  const [stickerForm, setStickerForm] = useState<any>(null);

  const load = () => apiGet<any>("/admin/overview").then(setData).catch((err) => setError(err.message));
  useEffect(() => { load(); }, []);
  useEffect(() => {
    apiGet<Sticker[]>(`/stickers?query=${encodeURIComponent(stickerQuery)}&limit=100`)
      .then(setStickers)
      .catch((err) => setError(err.message));
  }, [stickerQuery]);
  useEffect(() => {
    const selected = stickers.find((row) => (row.sticker_id || row.id) === selectedStickerId);
    if (selected) {
      setStickerForm({
        sticker_code: selected.sticker_code,
        album_order: (selected as any).album_order || 0,
        category_code: selected.category_code || "",
        category_name: selected.category_name || "",
        player_name: selected.player_name || "",
        team_name: selected.team_name || "",
        label: selected.label || "",
        is_foil: !!selected.is_foil,
        is_team_photo: !!selected.is_team_photo,
        is_emblem: !!selected.is_emblem,
      });
    }
  }, [selectedStickerId, stickers]);

  if (error) return <ErrorBox message={error} />;
  if (!data) return <Loading />;

  async function createPerson() {
    await apiPost("/people", { name: newName, actor_name: actor });
    setNewName("");
    setMessage("Personne créée ou réactivée.");
    load();
  }

  async function togglePerson(row: any) {
    await apiPatch(`/people/${row.id}`, { active: !row.active, actor_name: actor });
    load();
  }

  async function deletePerson(row: any) {
    await apiDelete(`/people/${row.id}`, { confirm_name: confirm, actor_name: actor });
    setConfirm("");
    setMessage("Personne supprimée.");
    load();
  }

  async function ensureHoldings() {
    const result: any = await apiPost("/admin/ensure-holdings", { include_inactive: true, actor_name: actor });
    setMessage(`${result.created_holdings} ligne(s) collection créée(s).`);
    load();
  }

  async function purgeImports() {
    const result: any = await apiDelete("/admin/imports", { confirm_text: confirm, actor_name: actor });
    setMessage(`${result.deleted} import(s) supprimé(s).`);
    setConfirm("");
    load();
  }

  async function purgeHistory() {
    const result: any = await apiDelete("/admin/history", { confirm_text: confirm, actor_name: actor });
    setMessage(`${result.deleted} action(s) supprimée(s).`);
    setConfirm("");
    load();
  }

  async function saveSticker() {
    await apiPatch(`/stickers/${selectedStickerId}`, { ...stickerForm, actor_name: actor });
    setMessage("Sticker mis à jour.");
    setStickerQuery(stickerForm.sticker_code);
  }

  async function deleteSticker() {
    await apiDelete(`/stickers/${selectedStickerId}`, { confirm_code: confirm, actor_name: actor });
    setConfirm("");
    setSelectedStickerId(0);
    setStickerForm(null);
    setMessage("Sticker supprimé.");
  }

  return (
    <>
      <PageHeader title="Admin DB" caption="Zone avancée locale pour corriger personnes, santé DB et opérations de maintenance." />
      {message && <SuccessBanner>{message}</SuccessBanner>}
      <Card>
        <div className="mb-3 text-sm font-black uppercase tracking-[.2em] text-gold">Zone avancée</div>
        <p className="mb-4 max-w-3xl text-sm font-semibold text-muted">
          Ces actions corrigent directement la base locale. Les suppressions restent protégées par confirmation explicite.
        </p>
        <Input value={actor} onChange={(event) => setActor(event.target.value)} placeholder="Qui fait l'action ? optionnel" />
      </Card>

      <div className="mt-6 grid gap-4 md:grid-cols-4">
        <MetricCard label="Personnes" value={data.overview.people_total} detail={`${data.overview.people_active} actives`} tone="blue" />
        <MetricCard label="Stickers" value={data.overview.stickers_total} tone="gold" />
        <MetricCard label="Exemplaires" value={data.overview.total_copies} tone="green" />
        <MetricCard label="Actions loggées" value={data.overview.actions} />
      </div>

      <Card className="mt-6" foil>
        <h2 className="mb-3 text-xl font-black">Personnes</h2>
        <div className="mb-4 grid gap-3 md:grid-cols-[1fr_auto]">
          <Input value={newName} onChange={(event) => setNewName(event.target.value)} placeholder="Nom" />
          <Button onClick={createPerson} disabled={!newName}>Créer / réactiver</Button>
        </div>
        <DataTable
          columns={["Nom", "Actif", "Exemplaires", "Échanges", "Action"]}
          rows={data.people.map((row: any) => ({
            Nom: row.name,
            Actif: row.active ? "Oui" : "Non",
            Exemplaires: row.total_quantity,
            Échanges: row.trades,
            Action: <Button variant="secondary" onClick={() => togglePerson(row)}>{row.active ? "Désactiver" : "Réactiver"}</Button>,
          }))}
        />
      </Card>

      <details className="mt-6 rounded-sticker border border-white/10 bg-panel/70 p-5">
        <summary className="cursor-pointer text-xl font-black">Vue DB avancée</summary>
        <div className="mt-5 grid gap-5 lg:grid-cols-2">
          <Card>
            <h2 className="mb-3 text-xl font-black">Catégories</h2>
            <DataTable
              columns={["Code", "Nom", "Stickers"]}
              rows={data.categories.map((row: any) => ({ Code: row.category_code, Nom: row.category_name, Stickers: row.stickers }))}
            />
          </Card>
          <Card>
            <h2 className="mb-3 text-xl font-black">Actions par type</h2>
            <DataTable
              columns={["Action", "Nombre"]}
              rows={data.actions.map((row: any) => ({ Action: row.action_type, Nombre: row.count }))}
            />
          </Card>
        </div>
      </details>

      <details className="mt-6 rounded-sticker border border-white/10 bg-panel/70 p-5">
        <summary className="cursor-pointer text-xl font-black">Édition stickers</summary>
        <div className="grid gap-3 md:grid-cols-2">
          <SearchInput value={stickerQuery} onChange={(event) => setStickerQuery(event.target.value)} placeholder="Rechercher code, joueur, équipe..." />
          <Select
            value={selectedStickerId}
            onChange={(event) => setSelectedStickerId(Number(event.target.value))}
          >
            <option value={0}>Choisir un sticker</option>
            {stickers.map((row) => (
              <option key={row.sticker_id || row.id} value={row.sticker_id || row.id}>
                {row.display_code} - {row.player_name || row.label || row.team_name || ""}
              </option>
            ))}
          </Select>
        </div>
        {stickerForm && (
          <div className="mt-4 grid gap-3">
            <div className="grid gap-3 md:grid-cols-3">
              <Input value={stickerForm.sticker_code} onChange={(event) => setStickerForm({ ...stickerForm, sticker_code: event.target.value })} placeholder="Code" />
              <Input type="number" value={stickerForm.album_order} onChange={(event) => setStickerForm({ ...stickerForm, album_order: Number(event.target.value) })} placeholder="Ordre album" />
              <Input value={stickerForm.category_code} onChange={(event) => setStickerForm({ ...stickerForm, category_code: event.target.value })} placeholder="Catégorie" />
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <Input value={stickerForm.player_name} onChange={(event) => setStickerForm({ ...stickerForm, player_name: event.target.value })} placeholder="Joueur" />
              <Input value={stickerForm.team_name} onChange={(event) => setStickerForm({ ...stickerForm, team_name: event.target.value })} placeholder="Équipe" />
              <Input value={stickerForm.category_name} onChange={(event) => setStickerForm({ ...stickerForm, category_name: event.target.value })} placeholder="Nom catégorie" />
            </div>
            <Input value={stickerForm.label} onChange={(event) => setStickerForm({ ...stickerForm, label: event.target.value })} placeholder="Libellé" />
            <div className="flex flex-wrap gap-4 text-sm text-slate-300">
              <label><input type="checkbox" checked={stickerForm.is_foil} onChange={(event) => setStickerForm({ ...stickerForm, is_foil: event.target.checked })} /> Foil</label>
              <label><input type="checkbox" checked={stickerForm.is_team_photo} onChange={(event) => setStickerForm({ ...stickerForm, is_team_photo: event.target.checked })} /> Photo équipe</label>
              <label><input type="checkbox" checked={stickerForm.is_emblem} onChange={(event) => setStickerForm({ ...stickerForm, is_emblem: event.target.checked })} /> Logo</label>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button onClick={saveSticker}>Enregistrer sticker</Button>
              <Button variant="danger" onClick={deleteSticker} disabled={confirm !== stickerForm.sticker_code}>
                Supprimer sticker
              </Button>
            </div>
          </div>
        )}
      </details>

      <details className="mt-6 rounded-sticker border border-canada/30 bg-canada/[.08] p-5">
        <summary className="cursor-pointer text-xl font-black text-red-100">Zone dangereuse</summary>
        <Input className="mt-4" value={confirm} onChange={(event) => setConfirm(event.target.value)} placeholder="Texte de confirmation" />
        <div className="mt-3 flex flex-wrap gap-3">
          <Button variant="secondary" onClick={ensureHoldings}>Réparer lignes collection</Button>
          <Button variant="danger" onClick={purgeImports} disabled={confirm !== "PURGE IMPORTS"}>Purger imports</Button>
          <Button variant="danger" onClick={purgeHistory} disabled={confirm !== "PURGE HISTORY"}>Purger historique</Button>
        </div>
        <div className="mt-4 text-sm text-slate-400">
          Suppression personne: tape exactement son nom, puis utilise le bouton ci-dessous.
        </div>
        <div className="mt-3 flex flex-wrap gap-3">
          {data.people.map((row: any) => (
            <Button key={row.id} variant="danger" onClick={() => deletePerson(row)} disabled={confirm !== row.name}>
              Supprimer {row.name}
            </Button>
          ))}
        </div>
      </details>
    </>
  );
}
