-- 1. SELECT: все поезда
SELECT * FROM trains;

-- 2. WHERE: поезда, по которым идёт продажа билетов
SELECT number, name, base_price FROM trains WHERE status = 'scheduled';

-- 3. ORDER BY: поезда по убыванию базовой цены
SELECT number, name, base_price FROM trains ORDER BY base_price DESC;

-- 4. JOIN: маршрут поезда 003А с временем стоянок
SELECT t.number, rs.stop_order, s.name, rs.arrival_time, rs.departure_time
FROM route_stops rs
JOIN trains t ON t.id = rs.train_id
JOIN stations s ON s.id = rs.station_id
WHERE t.number = '003А'
ORDER BY rs.stop_order;

-- 5. LEFT JOIN: все вагоны и количество проданных мест (включая пустые вагоны)
SELECT t.number AS train, w.number AS wagon, w.wagon_type, w.seats, COUNT(tk.id) AS sold
FROM wagons w
JOIN trains t ON t.id = w.train_id
LEFT JOIN tickets tk ON tk.wagon_id = w.id AND tk.status = 'paid'
GROUP BY w.id
ORDER BY t.number, w.number;

-- 6. GROUP BY + COUNT: количество вагонов каждого типа
SELECT wagon_type, COUNT(*) AS wagons, SUM(seats) AS seats FROM wagons GROUP BY wagon_type;

-- 7. HAVING: поезда, у которых больше одного вагона
SELECT t.number, COUNT(w.id) AS wagons
FROM trains t JOIN wagons w ON w.train_id = t.id
GROUP BY t.id HAVING COUNT(w.id) > 1;

-- 8. AVG / SUM: выручка и средняя цена проданных билетов
SELECT COUNT(*) AS tickets, SUM(price) AS revenue, ROUND(AVG(price), 2) AS avg_price
FROM tickets WHERE status = 'paid';

-- 9. Подзапрос: пассажиры, купившие билет дороже средней цены
SELECT full_name FROM passengers
WHERE id IN (SELECT passenger_id FROM tickets WHERE price > (SELECT AVG(price) FROM tickets));

-- 10. Несколько условий: дешёвые поезда со статусом scheduled, номер которых оканчивается на «А»
SELECT number, name, base_price FROM trains
WHERE status = 'scheduled' AND base_price < 3500 AND number LIKE '%А';

-- 11. Связь нескольких таблиц: билеты с ФИО, поездом, вагоном и станцией отправления
SELECT p.full_name, t.number AS train, w.number AS wagon, tk.seat, tk.price, s.name AS from_station
FROM tickets tk
JOIN passengers p ON p.id = tk.passenger_id
JOIN wagons w ON w.id = tk.wagon_id
JOIN trains t ON t.id = w.train_id
JOIN route_stops rs ON rs.train_id = t.id AND rs.stop_order = 1
JOIN stations s ON s.id = rs.station_id
WHERE tk.status = 'paid';

-- 12. Поиск поездов «Москва → Владимир» (обе станции в маршруте, порядок важен)
SELECT t.number, t.name, a.departure_time, b.arrival_time
FROM trains t
JOIN route_stops a ON a.train_id = t.id
JOIN stations sa ON sa.id = a.station_id AND sa.city = 'Москва'
JOIN route_stops b ON b.train_id = t.id AND b.stop_order > a.stop_order
JOIN stations sb ON sb.id = b.station_id AND sb.city = 'Владимир';

-- 13. Загрузка поездов в процентах (подзапрос в FROM)
SELECT number, capacity, sold, ROUND(100.0 * sold / capacity, 1) AS load_percent
FROM (
    SELECT t.number,
           SUM(w.seats) AS capacity,
           (SELECT COUNT(*) FROM tickets tk JOIN wagons w2 ON w2.id = tk.wagon_id
            WHERE w2.train_id = t.id AND tk.status = 'paid') AS sold
    FROM trains t JOIN wagons w ON w.train_id = t.id
    GROUP BY t.id
)
ORDER BY load_percent DESC;

-- 14. INSERT: новый пассажир
INSERT INTO passengers (full_name, passport, email) VALUES ('Тестов Тест Тестович', '0000 000001', NULL);

-- 15. UPDATE: повышение цены поездов «Сапсан» на 5%
UPDATE trains SET base_price = ROUND(base_price * 1.05, 2) WHERE name = 'Сапсан';

-- 16. DELETE: удаление добавленного тестового пассажира
DELETE FROM passengers WHERE passport = '0000 000001';

-- 17. EXISTS: станции, через которые не проходит ни один поезд
SELECT name FROM stations s WHERE NOT EXISTS (SELECT 1 FROM route_stops rs WHERE rs.station_id = s.id);

-- 18. EXPLAIN: план запроса поиска по станции использует индекс idx_route_stops_station
EXPLAIN QUERY PLAN SELECT * FROM route_stops WHERE station_id = 6;
