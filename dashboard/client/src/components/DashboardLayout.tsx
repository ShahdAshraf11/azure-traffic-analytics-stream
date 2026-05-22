import { AppSidebar } from "@/components/AppSidebar";
import { TopBar } from "@/components/TopBar";
import { SystemPipelineBar } from "@/components/SystemPipelineBar";
import { RecentAlertsBar } from "@/components/RecentAlertsBar";

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col min-h-screen w-full bg-background">
      {/* Top: Sidebar + Main content */}
      <div className="flex flex-1 min-h-0">
        <AppSidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <TopBar />
          <RecentAlertsBar />
          <main className="flex-1 overflow-auto">
            {children}
          </main>
        </div>
      </div>

      {/* Full-width footer: System Pipeline + Stats */}
      <div className="border-t border-border p-3">
        <SystemPipelineBar />
      </div>
    </div>
  );
}
