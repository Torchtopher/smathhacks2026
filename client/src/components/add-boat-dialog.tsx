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
import type { BoatState } from "@/types"

interface AddBoatDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onAdd: (boat: BoatState) => void
}

export function AddBoatDialog({ open, onOpenChange, onAdd }: AddBoatDialogProps) {
  const [name, setName] = useState("")
  const [weightClass, setWeightClass] = useState<BoatState["weight_class"] | "">("")
  const [apiKey, setApiKey] = useState<string | null>(null)

  function handleSubmit(e) {
    e.preventDefault()
    if (!name || !weightClass) return

    const key = crypto.randomUUID()
    const boat: BoatState = {
      boat_id: crypto.randomUUID(),
      name,
      weight_class: weightClass as BoatState["weight_class"],
      gps_lat: 44.2 + (Math.random() - 0.5) * 0.3,
      gps_lon: -68.8 + (Math.random() - 0.5) * 0.3,
      heading: Math.floor(Math.random() * 360),
      timestamp: Date.now(),
      api_key: key,
    }

    onAdd(boat)
    setApiKey(key)
  }

  function handleClose(isOpen: boolean) {
    if (!isOpen) {
      setName("")
      setWeightClass("")
      setApiKey(null)
    }
    onOpenChange(isOpen)
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{apiKey ? "Boat Added!" : "Add Your Boat"}</DialogTitle>
          <DialogDescription>
            {apiKey
              ? "Your boat has been registered. Save your API key below."
              : "Register your boat to start collecting ocean data."}
          </DialogDescription>
        </DialogHeader>

        {apiKey ? (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Your API Key</Label>
              <div className="flex gap-2">
                <Input readOnly value={apiKey} className="font-mono text-sm" />
                <Button
                  variant="secondary"
                  onClick={() => navigator.clipboard.writeText(apiKey)}
                >
                  Copy
                </Button>
              </div>
              <p className="text-sm text-muted-foreground">
                Keep this key safe — you'll need it to send data from your boat.
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
                  <SelectItem value="heavy">Heavy</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button type="submit" className="w-full" disabled={!name || !weightClass}>
              Register Boat
            </Button>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
