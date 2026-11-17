import { redirect } from "next/navigation";

import { ProfileForms } from "@/modules/forms";
import { apiGet, loadViewer } from "@/shared/server-api";
import { ErrorState, PageTitle } from "@/shared/ui";

type Profile = { username: string; email: string; id: string };
type Interests = { sport_ids: string[]; team_ids: string[] };
type SessionItem = { id: string; started_at: string; last_access_at: string; ip_address: string | null; is_current: boolean };

export default async function ProfilePage() {
  const viewer = await loadViewer();
  if (!viewer) redirect("/login?next=/profile");
  if (viewer.demo) {
    return (
      <div className="stack">
        <PageTitle title="Профиль">
          <p className="lead">Имя и почта — ваша учётная запись. Интересы подбирают новости, сессии показывают, где вы уже вошли.</p>
        </PageTitle>
        <ProfileForms
          current={false}
          profile={{ username: viewer.username, email: "student@example.edu" }}
          interests={{ sport_ids: ["football"], team_ids: [] }}
          sessions={[{ id: "demo", started_at: "2026-11-15T12:00:00Z", last_access_at: "2026-11-15T12:00:00Z", ip_address: null, is_current: true }]}
        />
      </div>
    );
  }
  const [profile, sessions] = await Promise.all([
    apiGet<Profile>("user", "/user", { auth: true }),
    apiGet<SessionItem[]>("user", "/user/sessions", { auth: true }),
  ]);
  if (!profile.ok) return <ErrorState message={profile.message} href="/profile" />;
  const interests = await apiGet<Interests>("user", `/users/${encodeURIComponent(profile.data.id)}/interests`);
  return (
    <div className="stack">
      <PageTitle title="Профиль">
        <p className="lead">Имя и почта — ваша учётная запись. Интересы подбирают новости, сессии показывают, где вы уже вошли.</p>
      </PageTitle>
      {!sessions.ok ? <ErrorState message={sessions.message} href="/profile" /> : null}
      {!interests.ok ? <ErrorState message={interests.message} href="/profile" /> : (
        <ProfileForms
          current
          profile={{ username: profile.data.username, email: profile.data.email }}
          interests={interests.data}
          sessions={sessions.ok ? sessions.data : []}
        />
      )}
    </div>
  );
}
