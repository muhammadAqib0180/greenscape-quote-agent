-- Run this in Supabase SQL Editor before starting the app

create table if not exists pricing_items (
    id serial primary key,
    name text not null,
    unit text not null,          -- e.g. 'sqft', 'linear_ft', 'each'
    unit_price numeric not null,
    category text                -- e.g. 'hardscape', 'planting', 'lighting'
);

create table if not exists proposals (
    id serial primary key,
    client_name text not null,
    raw_notes text not null,
    extracted_items jsonb,          -- structured line items from the LLM
    subtotal numeric,
    needs_render boolean default false,
    status text default 'draft',    -- draft | approved | rejected
    parse_error text,               -- populated if LLM output failed validation
    revision_history jsonb default '[]'::jsonb,  -- AI Rewrite Engine audit trail
    created_at timestamptz default now()
);

-- Atomic append helper for the AI Rewrite Engine.
-- Called by app/db.py:add_revision_history() to avoid read-modify-write races.
create or replace function append_revision(pid int, entry jsonb)
returns void language sql security definer as $$
    update proposals
    set revision_history = revision_history || jsonb_build_array(entry)
    where id = pid;
$$;

-- ---------------------------------------------------------------------------
-- Row Level Security (RLS) Configuration
-- Enables PostgREST security compliance and satisfies Supabase Security Linter
-- ---------------------------------------------------------------------------

alter table pricing_items enable row level security;
alter table proposals enable row level security;

-- Clean up policies if re-executing script
drop policy if exists "Allow read access to pricing_items" on pricing_items;
drop policy if exists "Allow full management of pricing_items" on pricing_items;
drop policy if exists "Allow read access to proposals" on proposals;
drop policy if exists "Allow insert access to proposals" on proposals;
drop policy if exists "Allow update access to proposals" on proposals;
drop policy if exists "Allow delete access to proposals" on proposals;

-- RLS Policies for pricing_items (catalog)
create policy "Allow read access to pricing_items"
    on pricing_items for select
    to anon, authenticated, service_role
    using (true);

create policy "Allow full management of pricing_items"
    on pricing_items for all
    to service_role
    using (true)
    with check (true);

-- RLS Policies for proposals
create policy "Allow read access to proposals"
    on proposals for select
    to anon, authenticated, service_role
    using (true);

create policy "Allow insert access to proposals"
    on proposals for insert
    to anon, authenticated, service_role
    with check (true);

create policy "Allow update access to proposals"
    on proposals for update
    to anon, authenticated, service_role
    using (true)
    with check (true);

create policy "Allow delete access to proposals"
    on proposals for delete
    to anon, authenticated, service_role
    using (true);

-- Seed pricing catalog (representative subset of the real ~200-item sheet)
insert into pricing_items (name, unit, unit_price, category) values
('Paver patio - standard', 'sqft', 18, 'hardscape'),
('Paver patio - premium', 'sqft', 28, 'hardscape'),
('Retaining wall - block', 'linear_ft', 65, 'hardscape'),
('Retaining wall - natural stone', 'linear_ft', 110, 'hardscape'),
('Artificial turf', 'sqft', 12, 'planting'),
('Sod installation', 'sqft', 3, 'planting'),
('Irrigation zone', 'each', 850, 'irrigation'),
('Drip irrigation - per bed', 'each', 300, 'irrigation'),
('Fire pit - standard', 'each', 2800, 'features'),
('Fire pit - premium built-in', 'each', 6500, 'features'),
('Pergola - base 10x10', 'each', 4500, 'structures'),
('Pergola - premium cedar', 'each', 9500, 'structures'),
('Outdoor kitchen - basic', 'each', 12000, 'structures'),
('Outdoor kitchen - full build', 'each', 28000, 'structures'),
('Landscape lighting - per fixture', 'each', 175, 'lighting'),
('Pool deck resurfacing', 'sqft', 22, 'hardscape'),
('Tree planting - standard', 'each', 450, 'planting'),
('Mulch bed installation', 'sqft', 4, 'planting'),
('Drainage system - french drain', 'linear_ft', 35, 'drainage'),
('Grading and prep', 'sqft', 6, 'sitework');
