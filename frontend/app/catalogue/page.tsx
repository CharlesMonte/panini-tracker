"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Grid2X2, List, PanelRightOpen } from "lucide-react";
import { ErrorBox, PageHeader } from "@/components/async-state";
import { Button, Card, DataTable, EmptyState, SearchInput, Select, StatusBadge, StickerTile } from "@/components/ui";
import { apiGet, qs } from "@/lib/api";
import { stickerContext, stickerTitle } from "@/lib/format";
import type { Sticker } from "@/lib/types";

const kinds = ["Tous", "Joueur", "Logo", "Photo équipe", "Foil"];

export default function CataloguePage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [kind, setKind] = useState("Tous");
  const [mode, setMode] = useState<"Grille" | "Table">("Grille");
  const [rows, setRows] = useState<Sticker[]>([]);
  const [selected, setSelected] = useState<Sticker | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet<Sticker[]>(`/catalog${qs({ query, category, kind })}`).then((data) => {
      setRows(data);
      if (!selected && data[0]) setSelected(data[0]);
    }).catch((err) => setError(err.message));
  }, [query, category, kind]);

  const categories = useMemo(() => Array.from(new Set(rows.map((row) => row.category_name || row.category_code).filter(Boolean))).sort(), [rows]);

  if (error) return <ErrorBox message={error} />;

  return (
    <>
      <PageHeader title="Catalogue" caption="Parcourir l’album comme une collection : grille de stickers, filtres simples, détail et actions rapides." />
      <Card className="bg-gradient-to-br from-panel/95 via-panel/80 to-usa/10">
        <div className="grid gap-4 lg:grid-cols-[1.3fr_.8fr_.7fr_auto]">
          <SearchInput value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Code, joueur, équipe, label..." />
          <Select value={category} onChange={(event) => setCategory(event.target.value)}>
            <option value="">Toutes catégories</option>
            {categories.map((item) => <option key={item} value={item}>{item}</option>)}
          </Select>
          <Select value={kind} onChange={(event) => setKind(event.target.value)}>
            {kinds.map((item) => <option key={item} value={item}>{item}</option>)}
          </Select>
          <Button variant="secondary" onClick={() => setMode(mode === "Grille" ? "Table" : "Grille")}>
            {mode === "Grille" ? <List className="h-4 w-4" /> : <Grid2X2 className="h-4 w-4" />}
            {mode}
          </Button>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <StatusBadge tone="gold">{rows.length} stickers</StatusBadge>
          <StatusBadge tone="blue">{rows.filter((row) => row.is_foil).length} foil</StatusBadge>
          <StatusBadge tone="green">{rows.filter((row) => row.is_team_photo).length} photos équipe</StatusBadge>
        </div>
      </Card>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1fr_360px]">
        <div>
          {mode === "Table" ? (
            <DataTable
              columns={["Code", "Sticker", "Équipe / catégorie", "Type"]}
              rows={rows.map((row) => ({
                Code: row.display_code,
                Sticker: stickerTitle(row),
                "Équipe / catégorie": stickerContext(row),
                Type: typeLabel(row),
              }))}
            />
          ) : (
            <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
              {rows.map((row) => (
                <StickerTile
                  key={row.sticker_id || row.id}
                  sticker={row}
                  selected={(selected?.sticker_id || selected?.id) === (row.sticker_id || row.id)}
                  onClick={() => setSelected(row)}
                  compact
                />
              ))}
            </div>
          )}
          {!rows.length && !error && <EmptyState>Aucun sticker ne correspond aux filtres.</EmptyState>}
        </div>

        <aside className="xl:sticky xl:top-8 xl:self-start">
          <Card foil>
            <div className="mb-4 flex items-center gap-3">
              <div className="grid h-11 w-11 place-items-center rounded-2xl bg-gold text-pitch">
                <PanelRightOpen className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-2xl font-black">Détail sticker</h2>
                <p className="text-sm font-semibold text-muted">Actions rapides depuis l’album.</p>
              </div>
            </div>
            {selected ? (
              <div className="space-y-4">
                <StickerTile sticker={selected} selected />
                <div className="grid gap-2">
                  <Link href={`/saisie`}><Button className="w-full">Ajouter à une personne</Button></Link>
                  <Link href={`/echanges`}><Button variant="secondary" className="w-full">Voir échanges</Button></Link>
                  <Link href={`/achats-ventes`}><Button variant="secondary" className="w-full">Voir ventes</Button></Link>
                </div>
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-white/12 p-5 text-sm font-semibold text-muted">Sélectionne un sticker.</div>
            )}
          </Card>
        </aside>
      </div>
    </>
  );
}

function typeLabel(row: Sticker) {
  const labels = [];
  if (row.player_name) labels.push("Joueur");
  if (row.is_emblem) labels.push("Logo");
  if (row.is_team_photo) labels.push("Photo équipe");
  if (row.is_foil) labels.push("Foil");
  return labels.join(", ") || "Spécial";
}
