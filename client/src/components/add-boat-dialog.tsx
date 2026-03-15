import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"
import type { BoatState } from "@/types"

interface AddBoatDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function AddBoatDialog({ open, onOpenChange }: AddBoatDialogProps) {
  const [name, setName] = useState("")
  const [weightClass, setWeightClass] = useState<BoatState["weight_class"] | "">("")
  const [boatId, setBoatId] = useState<string | null>(null)

  const [copied, setCopied] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name || !weightClass) return

    setSubmitting(true)
    setError(null)

    try {
      const data = await api.registerBoat(name, weightClass)

      setBoatId(data.boat_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong")
    } finally {
      setSubmitting(false)
    }
  }

  function handleClose(isOpen: boolean) {
    if (!isOpen) {
      setName("")
      setWeightClass("")
      setBoatId(null)
      setError(null)
    }
    onOpenChange(isOpen)
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{boatId ? "Boat Added!" : "Add Your Boat"}</DialogTitle>
          <DialogDescription>
            {boatId
              ? "Your boat has been registered. Save your Boat ID below."
              : "Register your boat to start collecting ocean data."}
          </DialogDescription>
        </DialogHeader>

        {boatId ? (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Your Boat ID</Label>
              <div className="flex gap-2">
                <Input readOnly value={boatId} className="font-mono text-sm" />
                <Button
                  variant="secondary"
                  onClick={() => {
                    navigator.clipboard.writeText(boatId)
                    setCopied(true)
                    setTimeout(() => setCopied(false), 2000)
                  }}
                >
                  {copied ? "Copied!" : "Copy"}
                </Button>
              </div>
              <p className="text-sm text-muted-foreground">
                Keep this ID safe — you'll need it to send data from your boat.
              </p>
            </div>
            <Button className="w-full" onClick={() => handleClose(false)}>
              Done
            </Button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="boat-name">Boat Name</Label>
              <Input
                id="boat-name"
                placeholder="e.g. Sea Wanderer"
                value={name}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setName(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label>Weight Class</Label>
              <Select value={weightClass} onValueChange={(v: string) => setWeightClass(v as BoatState["weight_class"])}>
                <SelectTrigger>
                  <SelectValue placeholder="Select weight class" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="light">Light</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="heavy">Heavy</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
            <Button type="submit" className="w-full" disabled={!name || !weightClass || submitting}>
              {submitting ? "Registering..." : "Register Boat"}
            </Button>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
