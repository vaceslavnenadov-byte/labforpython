def test_api_crud_and_errors(client):
    assert client.get("/trains").status_code == 200
    assert client.get("/trains/999").status_code == 404
    created = client.post("/trains", json={"number": "888Н", "base_price": 900})
    assert created.status_code == 201
    train_id = created.get_json()["id"]
    assert client.patch(f"/trains/{train_id}", json={"status": "boarding"}).get_json()["status"] == "boarding"
    assert client.delete(f"/trains/{train_id}").status_code == 204
    assert client.get("/trains?sort=color").status_code == 400


def test_api_ticket_and_scheme_urls(client):
    response = client.post("/tickets", json={"train_id": 3, "wagon": 2, "seat": 5,
                                             "full_name": "А", "passport": "1234 000000"})
    assert response.status_code == 201
    wagons = client.get("/trains/3").get_json()["wagons"]
    assert wagons[0]["scheme_url"].endswith("/static/images/seated.svg")
