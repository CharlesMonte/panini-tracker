import type { Sticker } from "@/lib/types";

export function stickerTitle(row: Sticker): string {
  return row.player_name || row.label || row.display_code || row.sticker_code;
}

export function stickerContext(row: Sticker): string {
  return row.team_name || row.category_name || row.category_code || "";
}

export function stickerOption(row: Sticker): string {
  const context = stickerContext(row);
  return `${row.display_code} - ${stickerTitle(row)}${context ? ` - ${context}` : ""}`;
}

export function pct(value: number | undefined): string {
  return `${(value || 0).toFixed(1)}%`;
}

export function euros(value: number | undefined): string {
  return `${(value || 0).toFixed(2)} €`;
}
