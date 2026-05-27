"use client";

import { useEffect, useMemo, useState } from "react";
import { PackageCheck, RotateCcw, WandSparkles } from "lucide-react";
import { ErrorBox, Loading, PageHeader } from "@/components/async-state";
import {
  Button,
  Card,
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
import { stickerOption } from "@/lib/format";
import type { ActionRow, Person, Sticker } from "@/lib/types";

export default function SaisiePage() {
  const [people, setPeople] = useState<Person[]>([]);
  const [personId, setPersonId] = useState<number>(0);
  const [actor, setActor] = useState("");
  const [rawCodes, setRawCodes] = useState("");
  const [preview, setPreview] = useState<any>(null);
  const [query, setQuery] = useState("");
  const [stickers, setStickers] = useState<Sticker[]>([]);
  const [selectedSticker, setSelectedSticker] = useState<number>(0);
  const [actions, setActions] = useState<ActionRow[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const person = people.find((row) => row.id === personId);
  const selected = useMemo(() => stickers.find((sticker) => (sticker.sticker_id || sticker.id) === selectedSticker), [stickers, selectedSticker]);

  const load = () => {
    Promise.all([apiGet<Person[]>("/people"), apiGet<ActionRow[]>("/history?limit=8")])
      .then(([peopleRows, actionRows]) => {
        setPeople(peopleRows);
        if (!personId && peopleRows[0]) setPersonId(peopleRows[0].id);
        setActions(actionRows);
      })
      .catch((err) => setError(err.message));
  };

  useEffect(load, []);
  useEffect(() => {
    if (!query.trim()) {
      setStickers([]);
      setSelectedSticker(0);
      return;
    }
    apiGet<Sticker[]>(`/stickers${qs({ query, limit: 60 })}`).then(setStickers).catch((err) => setError(err.message));
  }, [query]);

  if (error) return <ErrorBox message={error} />;
  if (!people.length) return <Loading />;

  async function previewBatch() {
    const result = await apiPost<any>("/collection/batch-preview", { person_id: personId, raw_codes: rawCodes });
    setPreview(result);
  }

  async function applyBatch() {
    const result = await apiPost<any>("/collection/batch-apply", { person_id: personId, raw_codes: rawCodes, items: preview.items, actor_name: actor });
    setMessage(`${result.added_count} sticker(s) ajouté(s) à ${person?.name || "la collection"}.`);
    setPreview(null);
    setRawCodes("");
    load();
  }

  async function updateQuantity(delta: number) {
    if (!selected) return;
    await apiPost("/collection/quantity", { person_id: personId, sticker_id: selected.sticker_id || selected.id, delta, actor_name: actor });
    setMessage(delta > 0 ? `${selected.display_code} ajouté à ${person?.name}.` : `${selected.display_code} retiré pour ${person?.name}.`);
    load();
  }

  async function undo(actionId: number) {
    await apiPost("/history/undo", { action_id: actionId, actor_name: actor });
    setMessage("Action annulée.");
    load();
  }

  return (
    <>
      <PageHeader title="Saisie rapide" caption="Le parcours pensé pour ouvrir des pochettes : choisis la personne, colle les codes, vérifie, applique." />
      {message && <SuccessBanner>{message}</SuccessBanner>}

      <div className="grid gap-4 lg:grid-cols-[1.4fr_.8fr]">
        <Card className="bg-gradient-to-br from-panel/90 via-panel/80 to-usa/10" foil>
          <div className="grid gap-4 md:grid-cols-[1fr_1fr]">
            <div>
              <div className="mb-2 text-xs font-black uppercase tracking-[.2em] text-gold">Pour qui ?</div>
              <Select value={personId} onChange={(event) => setPersonId(Number(event.target.value))}>
                {people.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}
              </Select>
            </div>
            <div>
              <div className="mb-2 text-xs font-black uppercase tracking-[.2em] text-muted">Qui saisit ?</div>
              <Input value={actor} onChange={(event) => setActor(event.target.value)} placeholder="Optionnel" />
            </div>
          </div>

          <div className="mt-6 grid gap-5 xl:grid-cols-[1.1fr_.9fr]">
            <div>
              <div className="flex items-center gap-3">
                <div className="grid h-11 w-11 place-items-center rounded-2xl bg-gold text-pitch">
                  <WandSparkles className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="text-2xl font-black">Coller une pochette</h2>
                  <p className="text-sm font-semibold text-muted">Un code par ligne, les doublons sont regroupés automatiquement.</p>
                </div>
              </div>
              <Textarea
                className="mt-5 min-h-[270px] text-base"
                value={rawCodes}
                onChange={(event) => setRawCodes(event.target.value)}
                placeholder={"MEX1\nMEX2\nBRA14\nFRA20\nFWC3"}
              />
              <div className="mt-4 flex flex-wrap gap-3">
                <Button onClick={previewBatch} disabled={!rawCodes.trim()}>Prévisualiser</Button>
                <Button variant="success" onClick={applyBatch} disabled={!preview?.valid_items?.length}>
                  <PackageCheck className="h-4 w-4" />
                  Appliquer la session
                </Button>
              </div>
            </div>

            <div className="space-y-4">
              <PreviewSummary preview={preview} />
              {preview && (
                <div className="max-h-[430px] overflow-y-auto rounded-2xl border border-white/10 bg-night/45 p-3">
                  <div className="space-y-2">
                    {preview.valid_items.map((item: any) => (
                      <div key={item.sticker_id} className="rounded-2xl border border-white/8 bg-panel/70 p-3">
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <div className="font-black text-white">{item.display_code} · {item.player_name || item.label}</div>
                            <div className="text-sm font-semibold text-muted">{item.team_name || item.category_name || item.category_code}</div>
                          </div>
                          <StatusBadge tone="green">{item.current_quantity} → {item.new_quantity}</StatusBadge>
                        </div>
                      </div>
                    ))}
                  </div>
                  {!!preview.unknown_items.length && (
                    <div className="mt-3 rounded-2xl border border-canada/30 bg-canada/10 p-3 text-sm font-bold text-red-100">
                      Introuvables : {preview.unknown_items.map((item: any) => item.code).join(", ")}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </Card>

        <Card>
          <h2 className="text-2xl font-black">Ajustement ponctuel</h2>
          <p className="mt-1 text-sm font-semibold text-muted">Pour corriger une carte sans lancer une session.</p>
          <SearchInput className="mt-5" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="MEX12, Mbappé, France..." />
          {!!stickers.length && (
            <Select className="mt-3" value={selectedSticker} onChange={(event) => setSelectedSticker(Number(event.target.value))}>
              <option value={0}>Choisir un sticker</option>
              {stickers.map((sticker) => <option key={sticker.sticker_id || sticker.id} value={sticker.sticker_id || sticker.id}>{stickerOption(sticker)}</option>)}
            </Select>
          )}
          {selected ? (
            <div className="mt-5 space-y-4">
              <StickerTile sticker={selected} />
              <div className="grid grid-cols-2 gap-3">
                <Button onClick={() => updateQuantity(1)}>+1</Button>
                <Button variant="secondary" onClick={() => updateQuantity(-1)}>-1</Button>
              </div>
            </div>
          ) : (
            <div className="mt-5 rounded-2xl border border-dashed border-white/12 p-5 text-sm font-semibold text-muted">
              Recherche un code, un joueur ou une équipe.
            </div>
          )}
        </Card>
      </div>

      <Card className="mt-6">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h2 className="text-2xl font-black">Dernières actions</h2>
            <p className="text-sm font-semibold text-muted">Annulation disponible uniquement sur les actions simples ou sessions autorisées.</p>
          </div>
          <StatusBadge>{actions.length} lignes</StatusBadge>
        </div>
        <div className="space-y-3">
          {actions.map((action) => (
            <div key={action.id} className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-night/55 p-4 md:flex-row md:items-center md:justify-between">
              <div>
                <div className="font-black text-white">{action.action_label} · {action.personne || "Groupe"}</div>
                <div className="text-sm font-semibold text-muted">{action.sticker || ""} {action.nom || ""}</div>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge tone="blue">{action.avant ?? ""} → {action.après ?? ""}</StatusBadge>
                {action.annulable && (
                  <Button variant="secondary" onClick={() => undo(action.id)}>
                    <RotateCcw className="h-4 w-4" />
                    Annuler
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </>
  );
}

function PreviewSummary({ preview }: { preview: any }) {
  if (!preview) {
    return (
      <div className="grid gap-3">
        <MetricCard label="Prêt" value="0" detail="Colle une liste pour voir le résultat avant/après." tone="blue" />
      </div>
    );
  }
  return (
    <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
      <MetricCard label="Valides" value={preview.valid_count} tone="green" />
      <MetricCard label="Inconnus" value={preview.unknown_count} tone={preview.unknown_count ? "red" : "neutral"} />
      <MetricCard label="Doublons saisis" value={preview.duplicate_codes.length} tone={preview.duplicate_codes.length ? "gold" : "neutral"} />
    </div>
  );
}
