"use client";

import { useState } from "react";
import { Download, FileSpreadsheet, UploadCloud } from "lucide-react";
import { ErrorBox, PageHeader } from "@/components/async-state";
import { Button, Card, DataTable, Input, MetricCard, SuccessBanner } from "@/components/ui";
import { apiPost, downloadUrl } from "@/lib/api";

export default function ImportExportPage() {
  const [path, setPath] = useState("source_excel.xlsx");
  const [file, setFile] = useState<File | null>(null);
  const [namesPath, setNamesPath] = useState("source_names.txt");
  const [preview, setPreview] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");

  async function previewExcel() {
    setError("");
    const form = new FormData();
    if (file) form.append("file", file);
    else form.append("path", path);
    const response = await fetch("/api/backend/imports/excel/preview", { method: "POST", body: form });
    if (!response.ok) throw new Error((await response.json()).detail || response.statusText);
    setPreview(await response.json());
  }

  async function applyExcel() {
    setError("");
    setResult(await apiPost("/imports/excel/apply", { path: preview?.path || path }));
  }

  async function importNames() {
    setError("");
    setResult(await apiPost("/imports/source-names", { path: namesPath }));
  }

  if (error) return <ErrorBox message={error} />;

  return (
    <>
      <PageHeader title="Import / Export" caption="Assistant local pour importer l’Excel, enrichir les noms depuis source_names.txt et récupérer un export propre." />
      {result && <SuccessBanner>Opération terminée.</SuccessBanner>}

      <div className="grid gap-5 xl:grid-cols-[1.15fr_.85fr]">
        <Card foil>
          <div className="flex items-center gap-3">
            <div className="grid h-12 w-12 place-items-center rounded-2xl bg-gold text-pitch">
              <FileSpreadsheet className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-2xl font-black">Import Excel</h2>
              <p className="text-sm font-semibold text-muted">Prévisualise avant de remplacer les quantités.</p>
            </div>
          </div>
          <div className="mt-5 grid gap-3">
            <input
              type="file"
              accept=".xlsx,.xlsm"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
              className="w-full rounded-2xl border border-white/10 bg-night/78 px-3 py-2.5 text-sm font-semibold text-slate-300"
            />
            <Input value={path} onChange={(event) => setPath(event.target.value)} placeholder="source_excel.xlsx" />
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            <Button onClick={() => previewExcel().catch((err) => setError(err.message))}>
              <UploadCloud className="h-4 w-4" />
              Prévisualiser
            </Button>
            <Button variant="success" onClick={() => applyExcel().catch((err) => setError(err.message))} disabled={!preview}>Lancer l'import</Button>
          </div>
          {preview && (
            <div className="mt-5 grid gap-3 md:grid-cols-4">
              <MetricCard label="Feuille" value={preview.sheet_name} />
              <MetricCard label="Stickers" value={preview.sticker_count} tone="gold" />
              <MetricCard label="Personnes" value={preview.people_names.length} tone="blue" />
              <MetricCard label="Ignorées" value={preview.ignored_rows} tone={preview.ignored_rows ? "red" : "green"} />
            </div>
          )}
        </Card>

        <div className="space-y-5">
          <Card>
            <h2 className="text-2xl font-black">Noms stickers</h2>
            <p className="mt-1 text-sm font-semibold text-muted">Source locale fixe, sans scraping web.</p>
            <Input className="mt-4" value={namesPath} onChange={(event) => setNamesPath(event.target.value)} placeholder="source_names.txt" />
            <Button className="mt-4 w-full" onClick={() => importNames().catch((err) => setError(err.message))}>Importer les noms</Button>
          </Card>
          <Card>
            <h2 className="text-2xl font-black">Exports</h2>
            <p className="mt-1 text-sm font-semibold text-muted">Récupère l’état courant pour partage ou sauvegarde.</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <a href={downloadUrl("/exports/csv")}><Button className="w-full"><Download className="h-4 w-4" /> CSV</Button></a>
              <a href={downloadUrl("/exports/excel")}><Button variant="secondary" className="w-full"><Download className="h-4 w-4" /> Excel</Button></a>
            </div>
          </Card>
        </div>
      </div>

      {result && (
        <Card className="mt-6">
          <h2 className="mb-3 text-2xl font-black">Résultat technique</h2>
          <pre className="overflow-x-auto rounded-2xl bg-night p-4 text-sm text-slate-300">{JSON.stringify(result, null, 2)}</pre>
        </Card>
      )}
    </>
  );
}

