"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ArrowLeftRight, Coins, ShoppingCart } from "lucide-react";
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
import { euros, stickerContext, stickerTitle } from "@/lib/format";
import type { Person, SaleCandidate } from "@/lib/types";

export default function AchatsVentesPage() {
  return (
    <Suspense fallback={<Loading />}>
      <SalesContent />
    </Suspense>
  );
}

function SalesContent() {
  const params = useSearchParams();
  const [people, setPeople] = useState<Person[]>([]);
  const [seller, setSeller] = useState(0);
  const [buyer, setBuyer] = useState(0);
  const [rows, setRows] = useState<SaleCandidate[]>([]);
  const [pick, setPick] = useState(0);
  const [rawCodes, setRawCodes] = useState("");
  const [search, setSearch] = useState("");
  const [preview, setPreview] = useState<any>(null);
  const [actor, setActor] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet<Person[]>("/people").then((data) => {
      setPeople(data);
      const sellerId = Number(params.get("seller_id")) || data[0]?.id || 0;
      const buyerId = Number(params.get("buyer_id")) || data.find((person) => person.id !== sellerId)?.id || 0;
      setSeller(sellerId);
      setBuyer(buyerId);
    }).catch((err) => setError(err.message));
  }, [params]);

  useEffect(() => {
    if (!seller || !buyer || seller === buyer) return;
    refreshRows();
  }, [seller, buyer]);

  const sellerName = people.find((person) => person.id === seller)?.name || "Vendeur";
  const buyerName = people.find((person) => person.id === buyer)?.name || "Acheteur";
  const selected = rows.find((row) => row.sticker_id === pick);
  const filteredRows = useMemo(() => filterSales(rows, search), [rows, search]);
  const total = filteredRows.reduce((sum, row) => sum + row.price, 0);

  if (error) return <ErrorBox message={error} />;
  if (!people.length) return <Loading />;

  async function refreshRows() {
    const result = await apiGet<SaleCandidate[]>(`/sales/options${qs({ seller_id: seller, buyer_id: buyer })}`);
    setRows(result);
    setPick(result[0]?.sticker_id || 0);
  }

  async function applyOne() {
    if (!selected) return;
    const result: any = await apiPost("/sales/apply", { seller_id: seller, buyer_id: buyer, sticker_id: selected.sticker_id, actor_name: actor });
    setMessage(`${sellerName} vend ${selected.display_code} à ${buyerName}. ${sellerName} garde ${result.seller_new_quantity} exemplaire(s), ${buyerName} en possède ${result.buyer_new_quantity}.`);
    refreshRows();
  }

  async function previewBatch() {
    const result = await apiPost("/sales/preview-batch", { seller_id: seller, buyer_id: buyer, raw_codes: rawCodes });
    setPreview(result);
  }

  async function applyBatch() {
    const result: any = await apiPost("/sales/apply-batch", { seller_id: seller, buyer_id: buyer, items: preview.items, actor_name: actor });
    setMessage(`Session appliquée : ${result.sale_count} vente(s), total indicatif ${euros(result.total_price)}.`);
    setPreview(null);
    setRawCodes("");
    refreshRows();
  }

  return (
    <>
      <PageHeader title="Achats / Ventes" caption="Un binôme, un vendeur, un acheteur : les doubles vendables sont clairs, au prix indicatif de 0,22 €." />
      {message && <SuccessBanner>{message}</SuccessBanner>}

      <Card className="bg-gradient-to-br from-panel/95 via-panel/80 to-mexico/10">
        <div className="grid gap-4 lg:grid-cols-[1fr_auto_1fr_auto]">
          <Select value={seller} onChange={(event) => setSeller(Number(event.target.value))}>
            {people.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}
          </Select>
          <Button variant="secondary" onClick={() => { setSeller(buyer); setBuyer(seller); }}>
            <ArrowLeftRight className="h-4 w-4" />
            Inverser
          </Button>
          <Select value={buyer} onChange={(event) => setBuyer(Number(event.target.value))}>
            {people.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}
          </Select>
          <Input value={actor} onChange={(event) => setActor(event.target.value)} placeholder="Appliqué par, optionnel" className="lg:w-56" />
        </div>
        {seller === buyer && <div className="mt-4 rounded-2xl border border-canada/35 bg-canada/10 p-4 text-sm font-black text-red-100">Choisis deux personnes différentes.</div>}
        <div className="mt-5 grid gap-3 md:grid-cols-3">
          <MetricCard label="Stickers vendables" value={filteredRows.length} detail={`${sellerName} possède un double, ${buyerName} ne l'a pas`} tone="green" />
          <MetricCard label="Prix unitaire" value="0,22 €" tone="gold" />
          <MetricCard label="Total affiché" value={euros(total)} detail="Indicatif, paiement hors app" tone="blue" />
        </div>
        <SearchInput className="mt-5" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Filtrer par code, joueur, équipe ou catégorie..." />
      </Card>

      <div className="mt-6 grid gap-5 xl:grid-cols-[1.15fr_.85fr]">
        <Card>
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="text-2xl font-black">{sellerName} peut vendre à {buyerName}</h2>
            <StatusBadge tone="green">{filteredRows.length}</StatusBadge>
          </div>
          <div className="grid max-h-[760px] gap-3 overflow-y-auto pr-1 md:grid-cols-2">
            {filteredRows.map((row) => (
              <StickerTile
                key={row.sticker_id}
                sticker={row}
                selected={pick === row.sticker_id}
                onClick={() => setPick(row.sticker_id)}
                compact
                caption={`${sellerName} garde ${row.seller_keeps_after_sale} · ${euros(row.price)}`}
              />
            ))}
          </div>
        </Card>

        <div className="space-y-5">
          <Card foil>
            <div className="flex items-center gap-3">
              <div className="grid h-12 w-12 place-items-center rounded-2xl bg-gold text-pitch">
                <ShoppingCart className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-2xl font-black">Vente sélectionnée</h2>
                <p className="text-sm font-semibold text-muted">Décrémente le vendeur et ajoute à l’acheteur.</p>
              </div>
            </div>
            {selected ? (
              <div className="mt-5">
                <StickerTile sticker={selected} selected caption={`${sellerName} vend à ${buyerName} pour ${euros(selected.price)}`} />
                <Button className="mt-4 w-full" onClick={applyOne}>
                  <Coins className="h-4 w-4" />
                  Acter cette vente
                </Button>
              </div>
            ) : (
              <div className="mt-5 rounded-2xl border border-dashed border-white/12 p-5 text-sm font-semibold text-muted">Sélectionne un sticker vendable.</div>
            )}
          </Card>

          <Card>
            <h2 className="text-2xl font-black">Session multi-ventes</h2>
            <p className="mt-1 text-sm font-semibold text-muted">Colle les codes vendus par {sellerName} à {buyerName}.</p>
            <Textarea className="mt-4" value={rawCodes} onChange={(event) => setRawCodes(event.target.value)} placeholder={"MEX1\nFRA20\nBRA14"} />
            <div className="mt-4 flex flex-wrap gap-3">
              <Button onClick={previewBatch}>Prévisualiser</Button>
              <Button variant="success" onClick={applyBatch} disabled={!preview?.can_apply}>Appliquer la session</Button>
            </div>
            {preview && (
              <div className="mt-5 space-y-4">
                <MetricCard label="Total indicatif" value={euros(preview.total_price)} tone="gold" />
                {!!preview.errors.length && <div className="rounded-2xl border border-canada/30 bg-canada/10 p-3 text-sm font-bold text-red-100">{preview.errors.join(" · ")}</div>}
                <DataTable
                  columns={["Code", "Sticker", "Prix"]}
                  rows={preview.items.map((item: any) => ({
                    Code: item.display_code,
                    Sticker: item.label,
                    Prix: euros(item.price),
                  }))}
                />
              </div>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}

function filterSales(rows: SaleCandidate[], query: string) {
  const needle = query.trim().toLowerCase();
  if (!needle) return rows;
  return rows.filter((row) => [row.display_code, row.sticker_code, stickerTitle(row), stickerContext(row)].join(" ").toLowerCase().includes(needle));
}
