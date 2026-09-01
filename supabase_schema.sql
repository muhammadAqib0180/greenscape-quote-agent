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
    extracted_items jsonb,       -- structured line items from the LLM
    subtotal numeric,
    needs_render boolean default false,
    status text default 'draft', -- draft | approved | rejected
    parse_error text,            -- populated if LLM output failed validation
    created_at timestamptz default now()
);

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
