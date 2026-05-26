"use client"

import { useState } from "react"
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { api } from "@/lib/api"
import { toast } from "sonner"

export function UpgradeDialog() {
  const [plan, setPlan] = useState<"pro" | "team">("pro")
  const [seats, setSeats] = useState(1)
  const [loading, setLoading] = useState(false)

  async function handleCheckout() {
    setLoading(true)
    try {
      const { checkout_url } = await api.billing.checkout(plan, seats)
      window.location.href = checkout_url
    } catch {
      toast.error("Failed to start checkout")
      setLoading(false)
    }
  }

  return (
    <Dialog>
      <DialogTrigger>
        <Button>Upgrade Plan</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Upgrade to a paid plan</DialogTitle>
          <DialogDescription>
            Choose a plan and seat count. You&apos;ll be redirected to Stripe.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="flex gap-2">
            {(["pro", "team"] as const).map((p) => (
              <Button
                key={p}
                variant={plan === p ? "default" : "outline"}
                className="flex-1 capitalize"
                onClick={() => setPlan(p)}
              >
                {p}
              </Button>
            ))}
          </div>
          <div>
            <Label htmlFor="seats">Seats</Label>
            <Input
              id="seats"
              type="number"
              min={1}
              max={500}
              value={seats}
              onChange={(e) => setSeats(Number(e.target.value))}
              className="mt-1"
            />
          </div>
        </div>
        <DialogFooter>
          <Button onClick={handleCheckout} disabled={loading} className="w-full">
            {loading ? "Redirecting…" : `Checkout — ${plan} × ${seats} seats`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
