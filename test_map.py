from app import create_app
app = create_app()
print(app.url_map)
with app.test_client() as c:
    resp = c.get('/')
    print("Response status:", resp.status_code)
    print("Response data:", resp.data.decode('utf-8'))
