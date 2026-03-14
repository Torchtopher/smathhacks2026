import type { TrashPoint } from "@/types"

type TrashClass = TrashPoint["class_name"]

export const TRASH_BG: Record<TrashClass, string> = {
  bottle: "bg-blue-500",
  "plastic bag": "bg-red-500",
  cup: "bg-yellow-500",
  "fishing line": "bg-green-500",
  styrofoam: "bg-purple-500",
}

export const TRASH_CSS_VAR: Record<TrashClass, string> = {
  bottle: "var(--color-blue-500)",
  "plastic bag": "var(--color-red-500)",
  cup: "var(--color-yellow-500)",
  "fishing line": "var(--color-green-500)",
  styrofoam: "var(--color-purple-500)",
}
