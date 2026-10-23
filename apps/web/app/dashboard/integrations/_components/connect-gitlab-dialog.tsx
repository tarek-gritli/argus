"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { errorDetail } from "@/lib/api";
import { useConnectGitlab } from "@/lib/queries";
import type { GitlabWebhookDetails } from "@/lib/types";
import { WebhookDetails } from "./webhook-details";

const GITLAB_COM = "https://gitlab.com";

export function ConnectGitlabDialog({ orgId }: { orgId: string }) {
  const connect = useConnectGitlab(orgId);
  const [open, setOpen] = useState(false);
  const [selfHosted, setSelfHosted] = useState(false);
  const [baseUrl, setBaseUrl] = useState("");
  const [token, setToken] = useState("");
  const [details, setDetails] = useState<GitlabWebhookDetails | null>(null);

  function reset(next: boolean) {
    setOpen(next);
    if (!next) {
      setSelfHosted(false);
      setBaseUrl("");
      setToken("");
      setDetails(null);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    connect.mutate(
      {
        base_url: selfHosted ? baseUrl.trim() : GITLAB_COM,
        access_token: token.trim(),
      },
      {
        onSuccess: (res) =>
          setDetails({
            webhook_url: res.webhook_url,
            webhook_secret: res.webhook_secret,
          }),
        onError: (err) =>
          toast.error(errorDetail(err, "Could not connect to GitLab")),
      },
    );
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium border border-white/10 text-[#c6c6c7] hover:bg-white/5 transition-colors"
      >
        <Plus className="h-3.5 w-3.5" /> Connect GitLab
      </button>
      <Dialog open={open} onOpenChange={reset}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {details ? "Add the webhook in GitLab" : "Connect GitLab"}
            </DialogTitle>
            <DialogDescription>
              {details
                ? "Argus is connected. Finish by creating the webhook."
                : "Argus reviews merge requests and posts comments using an access token you provide."}
            </DialogDescription>
          </DialogHeader>

          {details ? (
            <WebhookDetails details={details} />
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <label className="flex items-center gap-2 text-[13px] text-[#c6c6c7]">
                <input
                  type="checkbox"
                  checked={selfHosted}
                  onChange={(e) => setSelfHosted(e.target.checked)}
                />
                Self-hosted GitLab instance
              </label>
              {selfHosted && (
                <div className="space-y-1.5">
                  <Label htmlFor="gitlab-url">Instance URL</Label>
                  <Input
                    id="gitlab-url"
                    type="url"
                    placeholder="https://gitlab.example.com"
                    value={baseUrl}
                    onChange={(e) => setBaseUrl(e.target.value)}
                    required
                  />
                </div>
              )}
              <div className="space-y-1.5">
                <Label htmlFor="gitlab-token">Access token</Label>
                <Input
                  id="gitlab-token"
                  type="password"
                  autoComplete="off"
                  placeholder="glpat-…"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  required
                />
                <p className="text-[12px] text-[#8e9192]">
                  A project or group access token with the <code>api</code>{" "}
                  scope and Developer role.
                </p>
              </div>
              <Button
                type="submit"
                disabled={connect.isPending}
                className="w-full"
              >
                {connect.isPending ? "Connecting…" : "Connect"}
              </Button>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
