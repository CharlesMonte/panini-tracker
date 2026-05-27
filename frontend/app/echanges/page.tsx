"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ArrowLeftRight, CheckCheck, Repeat2 } from "lucide-react";
import { ErrorBox, Loading, PageHeader } from "@/components/async-state";
import {
  Button,
  Card,
  DataTable,
  Input,
  MetricCard,
  SearchInput,
  Select,
  StatusBadge,
  StickerTile,
  SuccessBanner,
  Textarea,
} from "@/components/ui";
import { apiGet, apiPost, qs } from "@/lib/api";
import { stickerContext, stickerTitle } from "@/lib/format";
import type { Person, TradeableSticker } from "@/lib/types";

export default function EchangesPage() {
  return (
    <Suspense fallback={<Loading />}>
      <EchangesContent />
    </Suspense>
  );
}

function EchangesContent() {
  const params = useSearchParams();
  const [people, setPeople] = useState<Person[]>([]);
  const [personA, setPersonA] = useState(0);
  const [personB, setPersonB] = useState(0);
  const [options, setOptions] = useState<{ a_to_b: TradeableSticker[]; b_to_a: TradeableSticker[] }>({ a_to_b: [], b_to_a: [] });
  const [pickA, setPickA] = useState(0);
  const [pickB, setPickB] = useState(0);
  const [rawA, setRawA] = useState("");
  const [rawB, setRawB] = useState("");
  const [search, setSearch] = useState("");
  const [preview, setPreview] = useState<any>(null);
  const [actor, setActor] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet<Person[]>("/people").then((data) => {
      setPeople(data);
      const a = Number(params.get("person_a_id")) || data[0]?.id || 0;
      const b = Number(params.get("person_b_id")) || data.find((person) => person.id !== a)?.id || 0;
      setPersonA(a);
      setPersonB(b);
    }).catch((err) => setError(err.message));
  }, [params]);

  useEffect(() => {
    if (!personA || !personB || personA === personB) return;
    apiGet<{ a_to_b: TradeableSticker[]; b_to_a: TradeableSticker[] }>(`/trades/options${qs({ person_a_id: personA, person_b_id: personB })}`)
      .then((data) => {
        setOptions(data);
        setPickA(data.a_to_b[0]?.sticker_id || 0);
        setPickB(data.b_to_a[0]?.sticker_id || 0);
      })
      .catch((err) => setError(err.message));
  }, [personA, personB]);

  const nameA = people.find((person) => person.id === personA)?.name || "Personne 1";
  const nameB = people.find((person) => person.id === personB)?.name || "Personne 2";
  const filteredA = useMemo(() => filterTradeables(options.a_to_b, search), [options.a_to_b, search]);
  const filteredB = useMemo(() => filterTradeables(options.b_to_a, search), [options.b_to_a, search]);
  const stickerA = useMemo(() => options.a_to_b.find((item) => item.sticker_id === pickA), [options, pickA]);
  const stickerB = useMemo(() => options.b_to_a.find((item) => item.sticker_id === pickB), [options, pickB]);
  const realizable = Math.min(options.a_to_b.length, options.b_to_a.length);
  const combinations = options.a_to_b.length * options.b_to_a.length;

  if (error) return <ErrorBox message={error} />;
  if (!people.length) return <Loading />;

  async function refreshOptions() {
    const data = await apiGet<{ a_to_b: TradeableSticker[]; b_to_a: TradeableSticker[] }>(`/trades/options${qs({ person_a_id: personA, person_b_id: personB })}`);
    setOptions(data);
    setPickA(data.a_to_b[0]?.sticker_id || 0);
    setPickB(data.b_to_a[0]?.sticker_id || 0);
  }

  async function applyOne() {
    await apiPost("/trades/apply", {
      person_a_id: personA,
      person_b_id: personB,
      sticker_from_a_id: pickA,
      sticker_from_b_id: pickB,
      actor_name: actor,
    });
    setMessage(`${nameA} et ${nameB} ont échangé 1 sticker chacun.`);
    refreshOptions();
  }

  async function previewBatch() {
    const result = await apiPost("/trades/preview-batch", {
      person_a_id: personA,
      person_b_id: personB,
      raw_codes_from_a: rawA,
      raw_codes_from_b: rawB,
    });
    setPreview(result);
  }

  async function applyBatch() {
    const result: any = await apiPost("/trades/apply-batch", {
      person_a_id: personA,
      person_b_id: personB,
      pairs: preview.pairs,
      actor_name: actor,
    });
    setMessage(`Session appliquée : ${result.trade_count} échange(s) entre ${nameA} et ${nameB}.`);
    setPreview(null);
    setRawA("");
    setRawB("");
    refreshOptions();
  }

  return (
    <>
      <PageHeader title="Échanges" caption="Un écran pour préparer un vrai binôme : ce que chacun peut donner, combien d’échanges réels sont possibles, puis application unitaire ou en session." />
      {message && <SuccessBanner>{message}</SuccessBanner>}

      <Card className="bg-gradient-to-br from-panel/95 via-panel/80 to-usa/10">
        <div className="grid gap-4 lg:grid-cols-[1fr_auto_1fr_auto]">
          <Select value={personA} onChange={(event) => setPersonA(Number(event.target.value))}>
            {people.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}
          </Select>
          <Button variant="secondary" onClick={() => { setPersonA(personB); setPersonB(personA); }}>
            <ArrowLeftRight className="h-4 w-4" />
            Inverser
          </Button>
          <Select value={personB} onChange={(event) => setPersonB(Number(event.target.value))}>
            {people.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}
          </Select>
          <Input value={actor} onChange={(event) => setActor(event.target.value)} placeholder="Appliqué par, optionnel" className="lg:w-56" />
        </div>
        {personA === personB && <div className="mt-4 rounded-2xl border border-canada/35 bg-canada/10 p-4 text-sm font-black text-red-100">Choisis deux personnes différentes.</div>}
        <div className="mt-5 grid gap-3 md:grid-cols-3">
          <MetricCard label={`${nameA} peut donner`} value={options.a_to_b.length} detail={`cartes manquantes à ${nameB}`} tone="blue" />
          <MetricCard label="Échanges applicables" value={realizable} detail={`${combinations} combinaison(s) de choix`} tone="gold" />
          <MetricCard label={`${nameB} peut donner`} value={options.b_to_a.length} detail={`cartes manquantes à ${nameA}`} tone="green" />
        </div>
        <SearchInput className="mt-5" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Filtrer par code, joueur, équipe ou catégorie..." />
      </Card>

      <div className="mt-6 grid gap-5 xl:grid-cols-[1fr_.86fr_1fr]">
        <TradeColumn title={`${nameA} donne à ${nameB}`} rows={filteredA} selected={pickA} onPick={setPickA} tone="blue" />
        <Card className="order-first xl:order-none" foil>
          <div className="flex items-center gap-3">
            <div className="grid h-12 w-12 place-items-center rounded-2xl bg-gold text-pitch">
              <Repeat2 className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-2xl font-black">Échange sélectionné</h2>
              <p className="text-sm font-semibold text-muted">1 sticker contre 1 sticker, revérifié en base.</p>
            </div>
          </div>
          <div className="mt-5 grid gap-3">
            {stickerA ? <StickerTile sticker={stickerA} caption={`${nameA} donne à ${nameB}`} selected compact /> : <EmptyPick name={nameA} />}
            <div className="grid place-items-center text-gold"><ArrowLeftRight className="h-6 w-6" /></div>
            {stickerB ? <StickerTile sticker={stickerB} caption={`${nameB} donne à ${nameA}`} selected compact /> : <EmptyPick name={nameB} />}
          </div>
          <Button className="mt-5 w-full" onClick={applyOne} disabled={!pickA || !pickB || personA === personB}>
            <CheckCheck className="h-4 w-4" />
            Appliquer cet échange
          </Button>
        </Card>
        <TradeColumn title={`${nameB} donne à ${nameA}`} rows={filteredB} selected={pickB} onPick={setPickB} tone="green" />
      </div>

      <Card className="mt-6">
        <div className="mb-4 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="text-2xl font-black">Session multi-échanges</h2>
            <p className="text-sm font-semibold text-muted">Colle d’un côté les cartes données par {nameA}, de l’autre celles données par {nameB}. Les lignes sont appairées.</p>
          </div>
          <StatusBadge tone="gold">Batch</StatusBadge>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <Textarea value={rawA} onChange={(event) => setRawA(event.target.value)} placeholder={`${nameA} donne...\nMEX1\nBRA14`} />
          <Textarea value={rawB} onChange={(event) => setRawB(event.target.value)} placeholder={`${nameB} donne...\nFRA20\nARG7`} />
        </div>
        <div className="mt-4 flex flex-wrap gap-3">
          <Button onClick={previewBatch}>Prévisualiser</Button>
          <Button variant="success" onClick={applyBatch} disabled={!preview?.can_apply}>Appliquer la session</Button>
        </div>
        {preview && (
          <div className="mt-5 space-y-4">
            {!!preview.errors.length && <div className="rounded-2xl border border-canada/30 bg-canada/10 p-3 text-sm font-bold text-red-100">{preview.errors.join(" · ")}</div>}
            <DataTable
              columns={[`${nameA} donne`, `${nameB} donne`]}
              rows={preview.pairs.map((pair: any) => ({
                [`${nameA} donne`]: `${pair.from_a.display_code} - ${pair.from_a.label}`,
                [`${nameB} donne`]: `${pair.from_b.display_code} - ${pair.from_b.label}`,
              }))}
            />
          </div>
        )}
      </Card>
    </>
  );
}

function TradeColumn({
  title,
  rows,
  selected,
  onPick,
  tone,
}: {
  title: string;
  rows: TradeableSticker[];
  selected: number;
  onPick: (id: number) => void;
  tone: "blue" | "green";
}) {
  return (
    <Card>
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-xl font-black">{title}</h2>
        <StatusBadge tone={tone}>{rows.length}</StatusBadge>
      </div>
      <div className="max-h-[720px] space-y-3 overflow-y-auto pr-1">
        {rows.map((row) => (
          <StickerTile
            key={row.sticker_id}
            sticker={row}
            compact
            selected={selected === row.sticker_id}
            onClick={() => onPick(row.sticker_id)}
            caption={<span>{stickerContext(row)} · quantité donneur : {row.giver_quantity}</span>}
          />
        ))}
      </div>
    </Card>
  );
}

function EmptyPick({ name }: { name: string }) {
  return <div className="rounded-2xl border border-dashed border-white/12 p-4 text-sm font-semibold text-muted">Choisis une carte donnée par {name}.</div>;
}

function filterTradeables(rows: TradeableSticker[], query: string) {
  const needle = query.trim().toLowerCase();
  if (!needle) return rows;
  return rows.filter((row) => [row.display_code, row.sticker_code, stickerTitle(row), stickerContext(row)].join(" ").toLowerCase().includes(needle));
}
