import { Topbar } from "@/components/topbar"

export default function SettingsPage() {
  return (
    <>
      <Topbar title="Settings" />
      <div className="p-6 max-w-2xl space-y-5">
        <div className="mb-6">
          <h2 className="text-base font-semibold text-foreground">Settings</h2>
          <p className="text-[12px] text-muted-foreground mt-0.5">Manage your organization preferences</p>
        </div>

        <div className="rounded-lg border bg-card p-5">
          <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-widest mb-3">Organization</p>
          <p className="text-sm text-foreground font-medium mb-1.5">Identity provisioning</p>
          <p className="text-[13px] text-muted-foreground leading-relaxed">
            Your organization is provisioned automatically from your GitHub identity on first login.
            The org slug matches your GitHub username or organization name.
          </p>
          <div className="mt-4 pt-4 border-t border-border">
            <p className="text-[12px] text-muted-foreground">
              To rename your org or transfer ownership, contact{" "}
              <a href="mailto:support@argus.dev" className="text-foreground underline underline-offset-2">
                support@argus.dev
              </a>
            </p>
          </div>
        </div>

        <div className="rounded-lg border bg-card p-5">
          <div className="flex items-start justify-between mb-3">
            <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-widest">Team Members</p>
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full border border-violet-500/20 bg-violet-500/8 text-violet-700 dark:text-violet-400">
              Team+
            </span>
          </div>
          <p className="text-[13px] text-muted-foreground leading-relaxed">
            Invite members via your GitHub organization — they are provisioned automatically on first login.
            Member listing UI is coming in a future release.
          </p>
        </div>
      </div>
    </>
  )
}
