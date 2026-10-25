-- טבלת פניות מהאתר yinonz-bina.com
-- להריץ פעם אחת ב-Supabase: SQL Editor > New query > להדביק > Run

create table if not exists public.leads (
  id          uuid primary key default gen_random_uuid(),
  created_at  timestamptz not null default now(),
  name        text not null check (char_length(name) between 1 and 120),
  role        text check (char_length(role) <= 200),
  contact     text not null check (char_length(contact) between 3 and 200),
  need        text check (char_length(need) <= 3000),
  service     text check (char_length(service) <= 80),
  page        text check (char_length(page) <= 200),
  status      text not null default 'חדש'
);

-- אבטחה: הדפדפן יכול רק להוסיף פנייה. אף אחד מבחוץ לא יכול לקרוא, לשנות או למחוק.
alter table public.leads enable row level security;

drop policy if exists "website can insert leads" on public.leads;
create policy "website can insert leads"
  on public.leads for insert
  to anon
  with check (status = 'חדש');

-- אין policy של select/update/delete ל-anon, ולכן הנתונים גלויים רק לך בלוח הבקרה של Supabase.
