"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ErrorBox, Loading, PageHeader } from "@/components/async-state";
import { Button, Card, MetricCard, ProgressBar, SearchInput, Select, StatusBadge, StickerTile } from "@/components/ui";
import { apiGet, qs } from "@/lib/api";
import { pct, stickerContext, stickerTitle } from "@/lib/format";
import type { Person, PersonStats, SaleCandidate, Sticker } from "@/lib/types";

const modes = ["À compléter", "Manquants", "Possédés", "Doubles", "Tous"];

export default function CollectionPage() {
  return (
    <Suspense fallback={<Loading />}>
      <CollectionContent />
    </Suspense>
  );
}

function CollectionContent() {
  const params = useSearchParams();
  const [people, setPeople] = useState<Person[]>([]);
  const [personId, setPersonId] = useState<number>(0);
  const [mode, setMode] = useState("À compléter");
  const [category, setCategory] = useState("");
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState<Sticker[]>([]);
  const [stats, setStats] = useState<PersonStats | null>(null);
  const [sales, setSales] = useState<SaleCandidate[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet<Person[]>("/people").then((data) => {
      setPeople(data);
      setPersonId(Number(params.get("person_id")) || data[0]?.id || 0);
    }).catch((err) => setError(err.message));
  }, [params]);

  useEffect(() => {
    if (!personId) return;
    const status = mode === "À compléter" ? "Manquants" : mode;
    Promise.all([
      apiGet<Sticker[]>(`/collection/${personId}${qs({ status, category })}`),
      apiGet<PersonStats>(`/collection/${personId}/stats`),
      apiGet<SaleCandidate[]>(`/sales/options${qs({ buyer_id: personId })}`),
    ]).then(([collectionRows, statsRow, salesRows]) => {
      setRows(collectionRows);
      setStats(statsRow);
      setSales(salesRows);
    }).catch((err) => setError(err.message));
  }, [personId, mode, category]);

  const person = people.find((row) => row.id === personId);
  const categories = Array.from(new Set(rows.map((row) => row.category_name || row.category_code).filter(Boolean))).sort();
  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return rows;
    return rows.filter((row) => [row.display_code, row.sticker_code, stickerTitle(row), stickerContext(row)].join(" ").toLowerCase().includes(needle));
  }, [rows, query]);
  const saleCounts = useMemo(() => {
    const counts = new Map<number, number>();
    sales.forEach((sale) => counts.set(sale.sticker_id, (counts.get(sale.sticker_id) || 0) + 1));
    return counts;
  }, [sales]);

  if (error) return <ErrorBox message={error} />;
  if (!people.length || !stats) return <Loading />;

  return (
    <>
      <PageHeader title="Collection" caption="Un album par personne : état simple, filtres utiles et pistes pour compléter les manquants." />

      <Card className="bg-gradient-to-br from-panel/95 via-panel/80 to-gold/10">
        <div className="grid gap-4 lg:grid-cols-[1fr_1fr_1fr]">
          <Select value={personId} onChange={(event) => setPersonId(Number(event.target.value))}>
            {people.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}
          </Select>
          <SearchInput value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Code, joueur, équipe..." />
          <Select value={category} onChange={(event) => setCategory(event.target.value)}>
            <option value="">Toutes les catégories</option>
            {categories.map((item) => <option key={item} value={item}>{item}</option>)}
          </Select>
        </div>
        <div className="mt-5 flex flex-wrap gap-2">
          {modes.map((item) => (
            <Button key={item} variant={mode === item ? "primary" : "secondary"} onClick={() => setMode(item)}>{item}</Button>
          ))}
        </div>
      </Card>

      <div className="mt-6 grid gap-4 md:grid-cols-5">
        <MetricCard label="Possédés" value={stats.owned_distinct} tone="blue" />
        <MetricCard label="Exemplaires" value={stats.total_copies} />
        <MetricCard label="Doubles" value={stats.duplicates} detail={pct(stats.duplicate_rate)} tone="gold" />
        <MetricCard label="Manquants" value={stats.missing} tone="red" />
        <MetricCard label="Complétion" value={pct(stats.completion)} detail={<ProgressBar value={stats.completion} />} tone="green" />
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {visible.map((row) => {
          const salesAvailable = saleCounts.get(row.sticker_id || row.id || 0) || 0;
          return (
            <StickerTile
              key={row.sticker_id || row.id}
              sticker={row}
              caption={
                <div className="space-y-3">
                  <div className="flex flex-wrap gap-2">
                    <StatusBadge tone={row.quantity ? row.quantity > 1 ? "gold" : "green" : "red"}>
                      {row.quantity ? `${row.quantity} exemplaire(s)` : "Manquant"}
                    </StatusBadge>
                    {row.duplicate_count ? <StatusBadge tone="gold">{row.duplicate_count} double(s)</StatusBadge> : null}
                    {mode === "À compléter" && <StatusBadge tone={salesAvailable ? "green" : "neutral"}>{salesAvailable ? `${salesAvailable} vente(s)` : "Aucune vente"}</StatusBadge>}
                  </div>
                  {mode === "À compléter" && (
                    <div className="flex flex-wrap gap-2">
                      <Link href={`/achats-ventes?buyer_id=${personId}`}><Button variant="secondary">Voir ventes</Button></Link>
                      <Link href={`/echanges?person_b_id=${personId}`}><Button variant="secondary">Voir échanges</Button></Link>
                    </div>
                  )}
                </div>
              }
            />
          );
        })}
      </div>

      {!visible.length && (
        <Card className="mt-6 text-center text-sm font-semibold text-muted">Aucun sticker pour ce filtre dans la collection de {person?.name}.</Card>
      )}
    </>
  );
}

