from app import create_app

app = create_app()
paths = ['/dashboard', '/products', '/suppliers', '/warehouses', '/returns', '/operations/reconciliation']

with app.test_client() as c:
    for p in paths:
        resp = c.get(p, follow_redirects=True)
        print(f"{p} -> {resp.status_code} ({len(resp.data)} bytes)")
