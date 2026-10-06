-- ЛР №11. Вариант 10. Железная дорога. Схема БД (SQLite).
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS passengers;
DROP TABLE IF EXISTS wagons;
DROP TABLE IF EXISTS route_stops;
DROP TABLE IF EXISTS trains;
DROP TABLE IF EXISTS stations;

CREATE TABLE stations (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE,
    city    TEXT NOT NULL
);

CREATE TABLE trains (
    id          INTEGER PRIMARY KEY,
    number      TEXT NOT NULL UNIQUE,
    name        TEXT,
    base_price  REAL NOT NULL CHECK (base_price > 0),
    status      TEXT NOT NULL DEFAULT 'scheduled'
                CHECK (status IN ('scheduled', 'boarding', 'departed', 'cancelled'))
);

-- Связь N:M «поезд — станция» через промежуточную таблицу маршрута
CREATE TABLE route_stops (
    train_id        INTEGER NOT NULL REFERENCES trains(id) ON DELETE CASCADE,
    station_id      INTEGER NOT NULL REFERENCES stations(id),
    stop_order      INTEGER NOT NULL CHECK (stop_order >= 1),
    arrival_time    TEXT,               -- NULL для начальной станции
    departure_time  TEXT,               -- NULL для конечной станции
    PRIMARY KEY (train_id, stop_order),
    UNIQUE (train_id, station_id)
);

-- Связь 1:N «поезд — вагоны»
CREATE TABLE wagons (
    id          INTEGER PRIMARY KEY,
    train_id    INTEGER NOT NULL REFERENCES trains(id) ON DELETE CASCADE,
    number      INTEGER NOT NULL CHECK (number >= 1),
    wagon_type  TEXT NOT NULL CHECK (wagon_type IN ('seated', 'coupe', 'sv')),
    seats       INTEGER NOT NULL CHECK (seats > 0),
    UNIQUE (train_id, number)
);

CREATE TABLE passengers (
    id          INTEGER PRIMARY KEY,
    full_name   TEXT NOT NULL,
    passport    TEXT NOT NULL UNIQUE,
    email       TEXT
);

-- Связь 1:N «вагон — билеты» и «пассажир — билеты»
CREATE TABLE tickets (
    id            INTEGER PRIMARY KEY,
    wagon_id      INTEGER NOT NULL REFERENCES wagons(id),
    passenger_id  INTEGER NOT NULL REFERENCES passengers(id),
    seat          INTEGER NOT NULL CHECK (seat >= 1),
    price         REAL NOT NULL CHECK (price >= 0),
    status        TEXT NOT NULL DEFAULT 'paid' CHECK (status IN ('paid', 'returned')),
    purchased_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Индексы
-- 1) Одно место в вагоне может быть занято только одним действующим билетом (частичный уникальный индекс)
CREATE UNIQUE INDEX idx_tickets_active_seat ON tickets(wagon_id, seat) WHERE status = 'paid';
-- 2) Быстрый поиск поездов по станции (поиск маршрута «откуда — куда»)
CREATE INDEX idx_route_stops_station ON route_stops(station_id);
-- 3) История поездок пассажира
CREATE INDEX idx_tickets_passenger ON tickets(passenger_id);
