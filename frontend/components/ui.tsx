"use client";

import clsx from "clsx";
import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { ArrowRight, CheckCircle2, ChevronDown, Search, Sparkles, XCircle } from "lucide-react";
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import type { Sticker } from "@/lib/types";
import { stickerContext, stickerTitle } from "@/lib/format";

export function Surface({
  children,
  className,
  interactive = false,
  foil = false,
}: {
  children?: ReactNode;
  className?: string;
  interactive?: boolean;
  foil?: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: "easeOut" }}
      whileHover={interactive ? { y: -3, scale: 1.006 } : undefined}
      className={clsx(
        "rounded-sticker border border-white/10 bg-panel/82 p-5 shadow-card backdrop-blur-xl",
        "before:pointer-events-none before:absolute before:inset-0 before:rounded-sticker before:bg-gradient-to-br before:from-white/[.055] before:to-transparent",
        "relative",
        foil && "foil-surface border-gold/35",
        className,
      )}
    >
      <div className="relative z-10">{children}</div>
    </motion.div>
  );
}

export function Card(props: { children?: ReactNode; className?: string; interactive?: boolean; foil?: boolean }) {
  return <Surface {...props} />;
}

export function Button({
  children,
  onClick,
  disabled,
  type = "button",
  variant = "primary",
  className,
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  type?: "button" | "submit";
  variant?: "primary" | "secondary" | "danger" | "ghost" | "success";
  className?: string;
}) {
  return (
    <motion.button
      whileTap={{ scale: disabled ? 1 : 0.97 }}
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        "inline-flex min-h-10 items-center justify-center gap-2 rounded-2xl px-4 py-2 text-sm font-black transition",
        "disabled:cursor-not-allowed disabled:opacity-40",
        variant === "primary" && "bg-gold text-pitch shadow-foil hover:bg-foil",
        variant === "secondary" && "border border-white/12 bg-panel2/90 text-white hover:border-gold/60 hover:bg-panel3",
        variant === "danger" && "bg-canada text-white hover:bg-red-400",
        variant === "ghost" && "text-slate-300 hover:bg-white/8 hover:text-white",
        variant === "success" && "bg-mexico text-pitch hover:bg-green-300",
        className,
      )}
    >
      {children}
    </motion.button>
  );
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={clsx(fieldClass, props.className)} />;
}

export function SearchInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="relative block">
      <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
      <input {...props} className={clsx(fieldClass, "pl-11", props.className)} />
    </label>
  );
}

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={clsx(fieldClass, "min-h-[150px] resize-y leading-relaxed", props.className)} />;
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <label className="relative block">
      <select {...props} className={clsx(fieldClass, "appearance-none pr-9", props.className)} />
      <ChevronDown className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
    </label>
  );
}

const fieldClass =
  "w-full rounded-2xl border border-white/12 bg-pitch/70 px-4 py-3 text-sm font-bold text-white outline-none placeholder:text-muted/70 shadow-inner shadow-black/20 transition focus:border-gold/70 focus:bg-night/88 focus:ring-4 focus:ring-gold/10 md:text-base";

export function MetricCard({
  label,
  value,
  detail,
  tone = "neutral",
}: {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  tone?: "neutral" | "gold" | "red" | "green" | "blue";
}) {
  const toneClass = {
    neutral: "from-white/10 to-transparent",
    gold: "from-gold/25 to-transparent",
    red: "from-canada/25 to-transparent",
    green: "from-mexico/22 to-transparent",
    blue: "from-usa/24 to-transparent",
  }[tone];
  return (
    <Surface className={clsx("min-h-[118px] overflow-hidden", `bg-gradient-to-br ${toneClass}`)} foil={tone === "gold"}>
      <div className="text-xs font-black uppercase tracking-[.17em] text-muted">{label}</div>
      <div className="mt-3 text-3xl font-black leading-none text-white md:text-4xl">{value}</div>
      {detail && <div className="mt-3 text-sm font-semibold text-slate-300">{detail}</div>}
    </Surface>
  );
}

export function ProgressBar({ value, label }: { value: number; label?: string }) {
  const width = Math.max(0, Math.min(100, value));
  return (
    <div>
      {label && (
        <div className="mb-2 flex justify-between text-xs font-bold uppercase tracking-wide text-muted">
          <span>{label}</span>
          <span>{width.toFixed(1)}%</span>
        </div>
      )}
      <div className="h-2.5 overflow-hidden rounded-full bg-night ring-1 ring-white/8">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${width}%` }}
          transition={{ duration: 0.65, ease: "easeOut" }}
          className="h-full rounded-full bg-gradient-to-r from-canada via-gold to-mexico"
        />
      </div>
    </div>
  );
}

export function StickerTile({
  sticker,
  caption,
  selected = false,
  compact = false,
  onClick,
}: {
  sticker: Sticker;
  caption?: ReactNode;
  selected?: boolean;
  compact?: boolean;
  onClick?: () => void;
}) {
  const Component = onClick ? motion.button : motion.div;
  return (
    <Component
      {...(onClick ? { type: "button", onClick } : {})}
      whileHover={{ y: -4, rotate: compact ? 0 : -0.4 }}
      whileTap={{ scale: 0.985 }}
      className={clsx(
        "group relative w-full overflow-hidden rounded-sticker border p-4 text-left shadow-card transition",
        selected ? "border-gold bg-gold/12" : "border-white/10 bg-gradient-to-br from-panel2 to-night hover:border-gold/45",
        !onClick && "cursor-default",
      )}
    >
      <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(255,255,255,.10),transparent_38%,rgba(242,201,93,.08)_58%,transparent)] opacity-70" />
      <div className="absolute -right-8 -top-8 h-24 w-24 rounded-full bg-usa/15 blur-2xl" />
      {sticker.is_foil && <div className="absolute inset-0 opacity-40 foil-surface" />}
      <div className="relative">
        <div className="flex items-start justify-between gap-3">
          <div className="rounded-xl bg-pitch/75 px-2.5 py-1 text-sm font-black text-gold ring-1 ring-gold/25">
            {sticker.display_code}
          </div>
          <StickerBadges sticker={sticker} />
        </div>
        <div className={clsx("mt-4 font-black text-white", compact ? "text-base" : "text-xl")}>{stickerTitle(sticker)}</div>
        <div className="mt-1 text-sm font-semibold text-muted">{stickerContext(sticker) || "Album 2026"}</div>
        {caption && <div className="mt-4 text-sm font-semibold text-slate-300">{caption}</div>}
      </div>
    </Component>
  );
}

export function StickerCard(props: { sticker: Sticker; caption?: ReactNode }) {
  return <StickerTile {...props} />;
}

export function StickerBadges({ sticker }: { sticker: Sticker }) {
  return (
    <div className="flex flex-wrap justify-end gap-1.5">
      {sticker.is_foil && <StatusBadge tone="gold">Foil</StatusBadge>}
      {sticker.is_emblem && <StatusBadge tone="blue">Logo</StatusBadge>}
      {sticker.is_team_photo && <StatusBadge tone="green">Photo</StatusBadge>}
    </div>
  );
}

export function StatusBadge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "gold" | "red" | "green" | "blue";
}) {
  const toneClass = {
    neutral: "bg-white/8 text-slate-200 ring-white/10",
    gold: "bg-gold/15 text-gold ring-gold/25",
    red: "bg-canada/14 text-red-100 ring-canada/25",
    green: "bg-mexico/13 text-green-100 ring-mexico/25",
    blue: "bg-usa/14 text-blue-100 ring-usa/25",
  }[tone];
  return <span className={clsx("rounded-full px-2 py-1 text-[11px] font-black uppercase tracking-wide ring-1", toneClass)}>{children}</span>;
}

export function PersonCard({
  name,
  detail,
  active = false,
  onClick,
}: {
  name: string;
  detail?: ReactNode;
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <motion.button
      type="button"
      onClick={onClick}
      whileTap={{ scale: 0.98 }}
      className={clsx(
        "w-full rounded-2xl border p-4 text-left transition",
        active ? "border-gold bg-gold/12" : "border-white/10 bg-panel/70 hover:border-gold/40",
      )}
    >
      <div className="text-lg font-black text-white">{name}</div>
      {detail && <div className="mt-1 text-sm font-semibold text-muted">{detail}</div>}
    </motion.button>
  );
}

export function OpportunityCard({
  title,
  detail,
  meta,
  href,
  tone = "gold",
}: {
  title: ReactNode;
  detail: ReactNode;
  meta?: ReactNode;
  href?: string;
  tone?: "gold" | "green" | "blue" | "red";
}) {
  const accent = { gold: "text-gold", green: "text-mexico", blue: "text-usa", red: "text-canada" }[tone];
  const content = (
    <Surface interactive className="h-full">
      <div className={clsx("mb-3 inline-flex rounded-full bg-white/7 px-2.5 py-1 text-xs font-black uppercase tracking-wide", accent)}>
        À regarder
      </div>
      <div className="text-xl font-black text-white">{title}</div>
      <div className="mt-2 text-sm font-semibold text-slate-300">{detail}</div>
      {meta && <div className="mt-2 text-xs font-bold uppercase tracking-wide text-muted">{meta}</div>}
      {href && (
        <div className="mt-4 inline-flex items-center gap-2 text-sm font-black text-gold">
          Ouvrir <ArrowRight className="h-4 w-4" />
        </div>
      )}
    </Surface>
  );
  if (!href) return content;
  return <a href={href}>{content}</a>;
}

export function DataTable({ columns, rows }: { columns: string[]; rows: Array<Record<string, ReactNode>> }) {
  const columnHelper = createColumnHelper<Record<string, ReactNode>>();
  const table = useReactTable({
    data: rows,
    columns: columns.map((column) => columnHelper.accessor((row) => row[column], { id: column, header: column })),
    getCoreRowModel: getCoreRowModel(),
  });
  if (!rows.length) return <EmptyState>Aucun résultat.</EmptyState>;
  return (
    <>
      <div className="hidden overflow-hidden rounded-2xl border border-white/10 md:block">
        <table className="min-w-full divide-y divide-white/10 text-sm">
          <thead className="bg-panel2/90">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th key={header.id} className="whitespace-nowrap px-4 py-3 text-left text-xs font-black uppercase tracking-wide text-muted">
                    {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y divide-white/8 bg-night/50">
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="transition hover:bg-white/[.035]">
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="whitespace-nowrap px-4 py-3 font-semibold text-slate-100">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="space-y-3 md:hidden">
        {rows.map((row, index) => (
          <div key={index} className="rounded-2xl border border-white/10 bg-night/60 p-4">
            {columns.map((column) => (
              <div key={column} className="flex justify-between gap-4 border-b border-white/7 py-2 last:border-0">
                <span className="text-xs font-black uppercase tracking-wide text-muted">{column}</span>
                <span className="text-right text-sm font-semibold text-white">{row[column]}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </>
  );
}

export function EmptyState({ children, icon = true }: { children: ReactNode; icon?: boolean }) {
  return (
    <Surface className="grid min-h-32 place-items-center text-center">
      {icon && <Sparkles className="mb-3 h-6 w-6 text-gold" />}
      <div className="max-w-md text-sm font-semibold text-slate-300">{children}</div>
    </Surface>
  );
}

export function SuccessBanner({ children }: { children: ReactNode }) {
  return (
    <Surface className="mb-5 border-mexico/35 bg-mexico/10">
      <div className="flex items-center gap-3 text-sm font-black text-green-100">
        <CheckCircle2 className="h-5 w-5 text-mexico" />
        {children}
      </div>
    </Surface>
  );
}

export function ErrorBanner({ children }: { children: ReactNode }) {
  return (
    <Surface className="mb-5 border-canada/40 bg-canada/10">
      <div className="flex items-center gap-3 text-sm font-black text-red-100">
        <XCircle className="h-5 w-5 text-canada" />
        {children}
      </div>
    </Surface>
  );
}
