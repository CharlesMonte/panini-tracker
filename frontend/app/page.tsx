"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, BookOpen, PackagePlus, Repeat2, ShoppingCart, Trophy } from "lucide-react";
import { ErrorBox, Loading } from "@/components/async-state";
import { Button, Card, MetricCard, OpportunityCard, ProgressBar, Select, StatusBadge } from "@/components/ui";
import { apiGet } from "@/lib/api";
import { pct } from "@/lib/format";
import type { Person, PersonStats } from "@/lib/types";

type Dashboard = {
  people: Person[];
  stickers_total: number;
  stats: PersonStats[];
  exchange_summaries: Array<{
    person_a_id: number;
    person_b_id: number;
    person_a: string;
    person_b: string;
    a_can_give: number;
    b_can_give: number;
    count: number;
    choice_count: number;
  }>;
  sale_summaries: Array<{ from_id: number; to_id: number; from: string; to: string; count: number }>;
};

export default function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [tracked, setTracked] = useState<number | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet<Dashboard>("/dashboard").then(setData).catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!tracked && data?.people[0]) setTracked(data.people[0].id);
  }, [data, tracked]);

  const trackedStats = useMemo(() => data?.stats.find((row) => row.person_id === tracked), [data, tracked]);

  if (error) return <ErrorBox message={error} />;
  if (!data) return <Loading />;

  const totalTrades = data.exchange_summaries.reduce((sum, row) => sum + row.count, 0);
  const totalSales = data.sale_summaries.reduce((sum, row) => sum + row.count, 0);

  return (
    <>
      <section className="grid gap-6 xl:grid-cols-[1.2fr_.8fr]">
        <Card className="relative overflow-hidden bg-gradient-to-br from-canada/20 via-panel to-usa/15" foil>
          <div className="absolute right-8 top-8 hidden h-44 w-32 rotate-6 rounded-sticker border border-gold/25 bg-gradient-to-br from-foil/20 to-white/5 shadow-foil md:block" />
          <div className="relative max-w-3xl">
            <div className="mb-4 inline-flex rounded-full border border-gold/25 bg-gold/10 px-3 py-1 text-xs font-black uppercase tracking-[.22em] text-gold">
              Collection partagée
            </div>
            <h1 className="text-5xl font-black leading-[.95] tracking-tight md:text-7xl">Panini Tracker 2026</h1>
            <p className="mt-5 max-w-2xl text-lg font-semibold leading-relaxed text-slate-300">
              Saisie de pochettes, doubles, manquants, échanges équivalents et ventes entre amis dans une interface pensée album.
            </p>
            <div className="mt-7 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <ActionLink href="/saisie" icon={<PackagePlus className="h-5 w-5" />} label="Ajouter" />
              <ActionLink href="/echanges" icon={<Repeat2 className="h-5 w-5" />} label="Échanger" />
              <ActionLink href="/achats-ventes" icon={<ShoppingCart className="h-5 w-5" />} label="Vendre" />
              <ActionLink href="/collection" icon={<BookOpen className="h-5 w-5" />} label="Collection" />
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-3">
            <div className="grid h-12 w-12 place-items-center rounded-2xl bg-gold text-pitch">
              <Trophy className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-2xl font-black">Personne à suivre</h2>
              <p className="text-sm font-semibold text-muted">Un résumé immédiat pour décider quoi faire.</p>
            </div>
          </div>
          <Select value={tracked || ""} onChange={(event) => setTracked(Number(event.target.value))} className="mt-5">
            {data.people.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}
          </Select>
          {trackedStats && (
            <div className="mt-5 space-y-5">
              <ProgressBar label="Complétion" value={trackedStats.completion} />
              <div className="grid grid-cols-3 gap-3">
                <MiniStat label="Manquants" value={trackedStats.missing} />
                <MiniStat label="Doubles" value={trackedStats.duplicates} />
                <MiniStat label="% doubles" value={pct(trackedStats.duplicate_rate)} />
              </div>
              <Link href={`/collection?person_id=${trackedStats.person_id}`}><Button className="w-full">Voir sa collection</Button></Link>
            </div>
          )}
        </Card>
      </section>

      <div className="mt-6 grid gap-4 md:grid-cols-4">
        <MetricCard label="Stickers album" value={data.stickers_total} tone="gold" />
        <MetricCard label="Collectionneurs" value={data.people.length} tone="blue" />
        <MetricCard label="Échanges réels" value={totalTrades} detail="max par binôme, pas les combinaisons" tone="green" />
        <MetricCard label="Ventes possibles" value={totalSales} tone="red" />
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-[1.1fr_.9fr]">
        <Card>
          <div className="mb-5 flex items-center justify-between">
            <h2 className="text-2xl font-black">Progression du groupe</h2>
            <StatusBadge>{data.stats.length} personnes</StatusBadge>
          </div>
          <div className="space-y-4">
            {data.stats.map((row) => (
              <div key={row.person_id} className="rounded-2xl border border-white/10 bg-night/55 p-4">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div>
                    <div className="text-lg font-black text-white">{row.person_name}</div>
                    <div className="text-sm font-semibold text-muted">{row.owned_distinct} possédés · {row.missing} manquants · {row.duplicates} doubles</div>
                  </div>
                  <StatusBadge tone="gold">{pct(row.completion)}</StatusBadge>
                </div>
                <ProgressBar value={row.completion} />
              </div>
            ))}
          </div>
        </Card>

        <div className="space-y-6">
          <Card>
            <h2 className="mb-4 text-2xl font-black">Échanges à regarder</h2>
            <div className="grid gap-3">
              {data.exchange_summaries.slice(0, 4).map((row) => (
                <OpportunityCard
                  key={`${row.person_a_id}-${row.person_b_id}`}
                  href={`/echanges?person_a_id=${row.person_a_id}&person_b_id=${row.person_b_id}`}
                  title={`${row.person_a} ↔ ${row.person_b}`}
                  detail={`Jusqu’à ${row.count} échange(s) réels. ${row.person_a} peut donner ${row.a_can_give}, ${row.person_b} peut donner ${row.b_can_give}.`}
                  meta={`${row.choice_count} combinaisons de choix`}
                  tone="gold"
                />
              ))}
            </div>
          </Card>
          <Card>
            <h2 className="mb-4 text-2xl font-black">Ventes possibles</h2>
            <div className="grid gap-3">
              {data.sale_summaries.slice(0, 4).map((row) => (
                <OpportunityCard
                  key={`${row.from_id}-${row.to_id}`}
                  href={`/achats-ventes?seller_id=${row.from_id}&buyer_id=${row.to_id}`}
                  title={`${row.from} → ${row.to}`}
                  detail={`${row.count} sticker(s) vendables à 0,22 €.`}
                  tone="green"
                />
              ))}
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}

function ActionLink({ href, icon, label }: { href: string; icon: React.ReactNode; label: string }) {
  return (
    <Link href={href} className="group flex items-center justify-between rounded-2xl border border-white/10 bg-white/7 px-4 py-3 font-black text-white transition hover:border-gold/50 hover:bg-gold/12">
      <span className="flex items-center gap-2">{icon}{label}</span>
      <ArrowRight className="h-4 w-4 text-gold transition group-hover:translate-x-1" />
    </Link>
  );
}

function MiniStat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-night/55 p-3">
      <div className="text-xs font-black uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-1 text-xl font-black text-white">{value}</div>
    </div>
  );
}

