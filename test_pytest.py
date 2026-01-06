import pytest
from app import create_app, db
from app.models import User, Post, Message
from config import Config


# konfiguracja testowa
class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    TESTING = True
    SERVER_NAME = None

# FIXTURES

#app testowa
@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

#test client
@pytest.fixture
def client(app):
    return app.test_client()

#!!!!!!!!!TESTY!!!!!!!!!

# czy poprawne haslo przechodzi weryfikacje po zahashowaniu
def test_password():
    u = User(username="hesoyam")
    u.set_password("hesoyam123")
    assert u.check_password("hesoyam123") is True

# czy niepoprawne haslo nie przechodzi weryfikacji
def test_password_error():
    u = User(username="baguvix")
    u.set_password("baguvix123")
    assert u.check_password("aezakmi") is False

# czy uzytkownik moze zaobserwowac innego uzytkownika i czy liczba obserwujacych sie zgadza
def test_follow(app):
    with app.app_context():
        u1 = User(username="s1", email="s1@test.com")
        u2 = User(username="s2", email="s2@test.com")
        db.session.add_all([u1, u2])
        db.session.commit()

        u1.follow(u2)
        db.session.commit()

        assert u1.is_following(u2) is True
        assert u2.followers_count() == 1

# odobserwowania najpierw follow, potem unfollow i  wynik
def test_unfollow(app):
    with app.app_context():
        u1 = User(username="jumpjet", email="jumpjet@test.com")
        u2 = User(username="cj", email="cj@test.com")
        db.session.add_all([u1, u2])
        db.session.commit()

        u1.follow(u2)
        db.session.commit()
        assert u1.is_following(u2)

        u1.unfollow(u2)
        db.session.commit()
        assert u1.is_following(u2) is False

#  rejestracja nowego uzytkownika (pozytywny)
def test_register(client):
    res = client.post("/auth/register", data={
        "username": "nowy",
        "email": "nowy@test.com",
        "password": "abc5",
        "password2": "abc5"
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b"registered user" in res.data

# proba rejestracji z istniejaca juz nazwa uzytkownika
def test_register_error(client):
    client.post("/auth/register", data={
        "username": "user123",
        "email": "user123@test.com",
        "password": "test123",
        "password2": "test123"
    })

    res = client.post("/auth/register", data={
        "username": "user123",
        "email": "user123@test.com",
        "password": "test123",
        "password2": "test123"
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b"different username" in res.data or b"already" in res.data

# test niepoprawnego hasla (aplikacja odrzuca logowanie)
def test_login_error(client, app):
    with app.app_context():
        u = User(username="user321", email="test123@test.com")
        u.set_password("ok")
        db.session.add(u)
        db.session.commit()

    res = client.post("/auth/login", data={
        "username": "user321",
        "password": "nieok"
    }, follow_redirects=True)

    assert b"Invalid" in res.data

# czy zalogowany uzytkownik moze dodac nowy post
def test_create_post(client, app):
    with app.app_context():
        u = User(username="malysz", email="malysz@test.com")
        u.set_password("x")
        db.session.add(u)
        db.session.commit()

    client.post("/auth/login", data={"username": "malysz", "password": "x"})
    res = client.post("/index", data={"post": "Hello"}, follow_redirects=True)

    assert b"post is now live" in res.data

# test czy aplikacja blokuje dodanie pustego posta
def test_create_empty(client, app):
    with app.app_context():
        u = User(username="pusty", email="pusty@test.com")
        u.set_password("x")
        db.session.add(u)
        db.session.commit()

    client.post("/auth/login", data={"username": "pusty", "password": "x"})
    res = client.post("/index", data={"post": ""}, follow_redirects=True)

    assert b"required" in res.data or b"live" not in res.data

# czy zalogowany uzytkownik moze wyswietlic profil innej osoby
def test_view_profile(client, app):
    with app.app_context():
        u = User(username="aezakmi", email="aezakmi@test.com")
        db.session.add(u)
        db.session.commit()

        viewer = User(username="aaaa", email="aaaa@test.com")
        viewer.set_password("abcd123")
        db.session.add(viewer)
        db.session.commit()

    client.post("/auth/login", data={"username": "aaaa", "password": "abcd123"})
    res = client.get("/user/aezakmi")

    assert res.status_code == 200
    assert b"aezakmi" in res.data

# test wejscia na profil ktory nie istnieje
def test_profile_error(client, app):
    with app.app_context():
        u = User(username="aezakmi", email="aezakmi@test.com")
        u.set_password("p")
        db.session.add(u)
        db.session.commit()

    client.post("/auth/login", data={"username": "aezakmi", "password": "p"})
    res = client.get("/user/brakuser")

    assert res.status_code == 404

# test czy endpoint follow dziala poprawnie
def test_follow_endpoint(client, app):
    with app.app_context():
        u1 = User(username="aa", email="aa@test.com")
        u1.set_password("abc1234")
        u2 = User(username="bb", email="bb@test.com")
        db.session.add_all([u1, u2])
        db.session.commit()

    client.post("/auth/login", data={"username": "aa", "password": "abc1234"})
    res = client.post("/follow/bb", follow_redirects=True)

    assert b"You are following" in res.data

# test czy jest walidacja ze nie mozna followowac siebie
def test_follow_error(client, app):
    with app.app_context():
        u = User(username="ja", email="ja@test.com")
        u.set_password("abcd1234")
        db.session.add(u)
        db.session.commit()

    client.post("/auth/login", data={"username": "ja", "password": "abcd1234"})
    res = client.post("/follow/ja", follow_redirects=True)

    assert b"cannot follow yourself" in res.data

# test czy zalogowany uzytkownik moze wyslac prywatna wiadomosc do innej osoby
def test_send_message(client, app):
    with app.app_context():
        s = User(username="s1", email="s1@test.com")
        s.set_password("a")
        r = User(username="r1", email="r1@test.com")
        db.session.add_all([s, r])
        db.session.commit()

    client.post("/auth/login", data={"username": "s1", "password": "a"})
    res = client.post("/send_message/r1", data={"message": "hi"}, follow_redirects=True)

    assert b"message has been sent" in res.data

# test czy wiadomosc pojawia sie w skrzynce odbiorczej uzytkownika
def test_inbox(client, app):
    with app.app_context():
        u = User(username="abc", email="abc@test.com")
        u.set_password("aaa")
        s = User(username="cba", email="cba@test.com")
        db.session.add_all([u, s])
        db.session.commit()

        msg = Message(body="hello!", author=s, recipient=u)
        db.session.add(msg)
        db.session.commit()

    client.post("/auth/login", data={"username": "abc", "password": "aaa"})
    res = client.get("/messages")

    assert b"hello!" in res.data

# czy blokuje wyslanie pustej wiadomosci
def test_message_error(client, app):
    with app.app_context():
        s = User(username="empty", email="emptysende@test.com")
        s.set_password("pass")
        r = User(username="emptyrecive", email="emptyrecive@test.com")
        db.session.add_all([s, r])
        db.session.commit()

    client.post("/auth/login", data={"username": "empty", "password": "pass"})
    res = client.post("/send_message/emptyrecive", data={"message": ""}, follow_redirects=True)

    assert b"required" in res.data or b"Field is required" in res.data

#kilka dodatkowych

# test pobierania listy uzytkownikow przez API
def test_api_users(client, app):
    with app.app_context():
        # stworz uzytkownika i token w jednym
        u = User(username='api', email='api@test.com')
        u.set_password('pass')
        db.session.add(u)
        db.session.commit()

        token = u.get_token()
        db.session.commit()

        headers = {'Authorization': f'Bearer {token}'}

        res = client.get('/api/users', headers=headers)
        assert res.status_code == 200

# pobieranie konkretnego uzytkownika przez API
def test_api_id(client, app):
    with app.app_context():
        u = User(username='tenuser', email='tenuser@test.com')
        u.set_password('pass')
        db.session.add(u)
        db.session.commit()

        user_id = u.id
        token = u.get_token()
        db.session.commit()

        headers = {'Authorization': f'Bearer {token}'}

        res = client.get(f'/api/users/{user_id}', headers=headers)
        assert res.status_code == 200
        assert b"tenuser" in res.data

# proba api bez tokena
def test_api_error(client, app):
    with app.app_context():
        u = User(username="testuser", email="test@test.com")
        db.session.add(u)
        db.session.commit()

        # proba dostepu bez tokena
        res = client.get('/api/users')

        assert res.status_code == 401