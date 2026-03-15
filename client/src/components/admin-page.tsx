import { useCallback, useEffect, useState } from "react"
import { api } from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

interface AdminBoat {
  boat_id: string
  name: string
  weight_class: string
  created_at: number
  last_reported_at: number | null
}

interface AdminPageProps {
  onDataChanged?: () => void | Promise<void>
}

export function AdminPage({ onDataChanged }: AdminPageProps) {
  const [boats, setBoats] = useState<AdminBoat[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const [newBoatId, setNewBoatId] = useState("")
  const [newName, setNewName] = useState("")
  const [newWeightClass, setNewWeightClass] = useState("light")

  const [editingBoatId, setEditingBoatId] = useState<string | null>(null)
  const [editingName, setEditingName] = useState("")
  const [editingWeightClass, setEditingWeightClass] = useState("light")

  const loadBoats = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getAdminBoats()
      setBoats(data.boats)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load boats")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadBoats()
  }, [loadBoats])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!newName.trim()) return

    setSubmitting(true)
    setError(null)
    setMessage(null)

    try {
      await api.createAdminBoat({
        boat_id: newBoatId.trim() || undefined,
        name: newName.trim(),
        weight_class: newWeightClass,
      })
      setNewBoatId("")
      setNewName("")
      setNewWeightClass("light")
      setMessage("Boat created")
      await loadBoats()
      if (onDataChanged) await onDataChanged()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create boat")
    } finally {
      setSubmitting(false)
    }
  }

  function startEdit(boat: AdminBoat) {
    setEditingBoatId(boat.boat_id)
    setEditingName(boat.name)
    setEditingWeightClass(boat.weight_class)
    setMessage(null)
    setError(null)
  }

  async function handleSaveEdit() {
    if (!editingBoatId || !editingName.trim()) return

    setSubmitting(true)
    setError(null)
    setMessage(null)

    try {
      await api.updateAdminBoat(editingBoatId, {
        name: editingName.trim(),
        weight_class: editingWeightClass,
      })
      setEditingBoatId(null)
      setMessage("Boat updated")
      await loadBoats()
      if (onDataChanged) await onDataChanged()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update boat")
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete(boatId: string) {
    const confirmed = window.confirm(
      "Delete this boat and all associated state/history/detections? This cannot be undone."
    )
    if (!confirmed) return

    setSubmitting(true)
    setError(null)
    setMessage(null)

    try {
      await api.deleteAdminBoat(boatId, true)
      setMessage("Boat deleted")
      if (editingBoatId === boatId) setEditingBoatId(null)
      await loadBoats()
      if (onDataChanged) await onDataChanged()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete boat")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex-1 overflow-auto p-4 md:p-6 space-y-6 bg-background">
      <Card>
        <CardHeader>
          <CardTitle>Admin Panel</CardTitle>
          <CardDescription>Manage boats stored in the backend database.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreate} className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <Input
              placeholder="Boat ID (optional)"
              value={newBoatId}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewBoatId(e.target.value)}
            />
            <Input
              placeholder="Boat name"
              value={newName}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewName(e.target.value)}
              required
            />
            <Select value={newWeightClass} onValueChange={setNewWeightClass}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Weight class" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="light">Light</SelectItem>
                <SelectItem value="heavy">Heavy</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
              </SelectContent>
            </Select>
            <Button type="submit" disabled={submitting || !newName.trim()}>
              {submitting ? "Saving..." : "Create Boat"}
            </Button>
          </form>
          <div className="mt-3 flex items-center gap-2">
            <Button variant="secondary" onClick={loadBoats} disabled={loading || submitting}>
              {loading ? "Refreshing..." : "Refresh"}
            </Button>
            {message ? <span className="text-sm text-green-600">{message}</span> : null}
            {error ? <span className="text-sm text-destructive">{error}</span> : null}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Boats</CardTitle>
          <CardDescription>{boats.length} record(s)</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-muted-foreground">
                  <th className="py-2 pr-3">Boat ID</th>
                  <th className="py-2 pr-3">Name</th>
                  <th className="py-2 pr-3">Weight</th>
                  <th className="py-2 pr-3">Created</th>
                  <th className="py-2 pr-3">Last Report</th>
                  <th className="py-2 pr-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {boats.map((boat) => {
                  const isEditing = editingBoatId === boat.boat_id
                  return (
                    <tr key={boat.boat_id} className="border-b border-border/60 align-top">
                      <td className="py-2 pr-3 font-mono text-xs">{boat.boat_id}</td>
                      <td className="py-2 pr-3">
                        {isEditing ? (
                          <Input
                            value={editingName}
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditingName(e.target.value)}
                          />
                        ) : (
                          boat.name
                        )}
                      </td>
                      <td className="py-2 pr-3">
                        {isEditing ? (
                          <Select value={editingWeightClass} onValueChange={setEditingWeightClass}>
                            <SelectTrigger className="w-32">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="light">Light</SelectItem>
                              <SelectItem value="heavy">Heavy</SelectItem>
                              <SelectItem value="medium">Medium</SelectItem>
                            </SelectContent>
                          </Select>
                        ) : (
                          boat.weight_class
                        )}
                      </td>
                      <td className="py-2 pr-3 whitespace-nowrap">
                        {new Date(boat.created_at * 1000).toLocaleString()}
                      </td>
                      <td className="py-2 pr-3 whitespace-nowrap">
                        {boat.last_reported_at
                          ? new Date(boat.last_reported_at * 1000).toLocaleString()
                          : "Never"}
                      </td>
                      <td className="py-2 pr-3">
                        <div className="flex gap-2">
                          {isEditing ? (
                            <>
                              <Button size="sm" onClick={handleSaveEdit} disabled={submitting || !editingName.trim()}>
                                Save
                              </Button>
                              <Button
                                size="sm"
                                variant="secondary"
                                onClick={() => setEditingBoatId(null)}
                                disabled={submitting}
                              >
                                Cancel
                              </Button>
                            </>
                          ) : (
                            <>
                              <Button size="sm" variant="secondary" onClick={() => startEdit(boat)} disabled={submitting}>
                                Edit
                              </Button>
                              <Button size="sm" variant="destructive" onClick={() => handleDelete(boat.boat_id)} disabled={submitting}>
                                Delete
                              </Button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
                {!loading && boats.length === 0 ? (
                  <tr>
                    <td className="py-4 text-muted-foreground" colSpan={6}>
                      No boats found.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
