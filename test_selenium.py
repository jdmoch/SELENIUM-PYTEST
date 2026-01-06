import threading
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from werkzeug.serving import make_server
from app import create_app, db
from app.models import User
from config import Config


# konfiguracja
class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    TESTING = True
    SERVER_NAME = None


# FIXTURES
# app testowa
@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


# flask odpalenie
@pytest.fixture(scope="function")
def flask(app):
    server = make_server("127.0.0.1", 5000, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield app
    finally:
        server.shutdown()
        thread.join(timeout=2)


# odpalenie storny
@pytest.fixture(scope="function")
def driver():
    options = Options()
    options.add_argument("--window-size=1280,800")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()


# rejestracja uzytkownikow
@pytest.fixture
def registered(flask):
    with flask.app_context():
        user1 = User(username='nowyuser1234', email='nowyuser1234@test.com')
        user1.set_password('haslo1234')
        user2 = User(username='drugitestuser999', email='drugitestuser999@test.com')
        user2.set_password('haslo1234')
        db.session.add(user1)
        db.session.add(user2)
        db.session.commit()


# helper dla logowania
def login_user(driver, wait, username, password):
    driver.get("http://127.0.0.1:5000/auth/login")

    wait.until(EC.presence_of_element_located((By.ID, "username")))
    driver.find_element(By.ID, "username").send_keys(username)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.ID, "submit").click()

    wait.until(lambda d: username in d.page_source)


# !!!!!!!!!!!!!!!!!!TESTY!!!!!!!!!!!!!!!

# rejestracja poprawna
def test_register(flask, driver):
    wait = WebDriverWait(driver, timeout=10)

    driver.get("http://127.0.0.1:5000/auth/register")

    wait.until(EC.presence_of_element_located((By.ID, "username")))
    driver.find_element(By.ID, "username").send_keys("nowyuser123")
    driver.find_element(By.ID, "email").send_keys("nowyuser123@test.com")
    driver.find_element(By.ID, "password").send_keys("haslo1234")
    driver.find_element(By.ID, "password2").send_keys("haslo1234")
    driver.find_element(By.ID, "submit").click()

    wait.until(lambda d: "login" in d.current_url)
    assert "login" in driver.current_url


# rejestracja niepoprawna (duplikacja bo juz jest taki uzytkownik zarejestrowany chodzi o login)
def test_register_error(registered, flask, driver):
    wait = WebDriverWait(driver, timeout=10)

    driver.get("http://127.0.0.1:5000/auth/register")

    wait.until(EC.presence_of_element_located((By.ID, "username")))
    driver.find_element(By.ID, "username").send_keys("nowyuser1234")
    driver.find_element(By.ID, "email").send_keys("innyemail@test.com")
    driver.find_element(By.ID, "password").send_keys("haslo1234")
    driver.find_element(By.ID, "password2").send_keys("haslo1234")
    driver.find_element(By.ID, "submit").click()

    wait.until(lambda d: "register" in d.current_url)
    assert "register" in driver.current_url

    page_text = driver.find_element(By.TAG_NAME, 'body').text
    assert "already" in page_text.lower() or "use a different username" in page_text.lower()


# dzialajcy test logowania
def test_login(registered, flask, driver):
    wait = WebDriverWait(driver, timeout=10)

    driver.get("http://127.0.0.1:5000/auth/login")

    wait.until(EC.presence_of_element_located((By.ID, "username")))
    driver.find_element(By.ID, "username").send_keys("nowyuser1234")
    driver.find_element(By.ID, "password").send_keys("haslo1234")
    driver.find_element(By.ID, "submit").click()

    wait.until(lambda d: "nowyuser1234" in d.page_source)
    assert "nowyuser1234" in driver.page_source


# nie dzialajacy test logowania zle haslo
def test_login_error(registered, flask, driver):
    wait = WebDriverWait(driver, timeout=10)

    driver.get("http://127.0.0.1:5000/auth/login")

    wait.until(EC.presence_of_element_located((By.ID, "username")))
    driver.find_element(By.ID, "username").send_keys("nowyuser1234")
    driver.find_element(By.ID, "password").send_keys("wrongpassword123")
    driver.find_element(By.ID, "submit").click()

    wait.until(lambda d: "login" in d.current_url)
    assert "login" in driver.current_url

    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    page_text = driver.find_element(By.TAG_NAME, 'body').text
    assert "invalid" in page_text.lower() or "incorrect" in page_text.lower()


# dzialajace dodawanie posta
def test_post(registered, flask, driver):
    wait = WebDriverWait(driver, timeout=10)

    login_user(driver, wait, "nowyuser1234", "haslo1234")

    driver.get("http://127.0.0.1:5000")

    wait.until(EC.presence_of_element_located((By.ID, "post")))
    driver.find_element(By.ID, "post").send_keys("testtest")
    driver.find_element(By.ID, "submit").click()

    wait.until(lambda d: "Your post is now live" in d.page_source or "testtest" in d.page_source)
    assert "Your post is now live" in driver.page_source or "testtest" in driver.page_source


# nie dzialajacy post (puste pole tekstowe)
def test_post_error(registered, flask, driver):
    wait = WebDriverWait(driver, timeout=10)

    login_user(driver, wait, "nowyuser1234", "haslo1234")

    driver.get("http://127.0.0.1:5000")

    wait.until(EC.presence_of_element_located((By.ID, "submit")))
    driver.find_element(By.ID, "submit").click()

    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    assert "Your post is now live" not in driver.page_source


# sprawdza czy pojawia sie przycisk unfollow
def test_follow(registered, flask, driver):
    wait = WebDriverWait(driver, timeout=10)

    login_user(driver, wait, "nowyuser1234", "haslo1234")

    driver.get("http://127.0.0.1:5000/user/drugitestuser999")

    wait.until(EC.presence_of_element_located((By.XPATH, "//input[@value='Follow']")))
    follow_button = driver.find_element(By.XPATH, "//input[@value='Follow']")
    follow_button.click()

    wait.until(EC.presence_of_element_located((By.XPATH, "//input[@value='Unfollow']")))
    assert "Unfollow" in driver.page_source


# odobserwowanie uzytkownika test
def test_unfollow(registered, flask, driver):
    wait = WebDriverWait(driver, timeout=10)

    login_user(driver, wait, "nowyuser1234", "haslo1234")

    driver.get("http://127.0.0.1:5000/user/drugitestuser999")

    wait.until(EC.presence_of_element_located((By.XPATH, "//input[@value='Follow']")))
    follow_button = driver.find_element(By.XPATH, "//input[@value='Follow']")
    follow_button.click()

    wait.until(EC.presence_of_element_located((By.XPATH, "//input[@value='Unfollow']")))
    unfollow_button = driver.find_element(By.XPATH, "//input[@value='Unfollow']")
    unfollow_button.click()

    wait.until(EC.presence_of_element_located((By.XPATH, "//input[@value='Follow']")))
    assert "Follow" in driver.page_source

    page_text = driver.find_element(By.TAG_NAME, 'body').text
    assert "0 followers" in page_text.lower()


# test wyswietlania informacji o followers na profilu
def test_followers(registered, flask, driver):
    wait = WebDriverWait(driver, timeout=10)

    login_user(driver, wait, "drugitestuser999", "haslo1234")

    driver.get("http://127.0.0.1:5000/user/drugitestuser999")

    wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'followers')]")))
    followers_info = driver.find_element(By.XPATH, "//*[contains(text(), 'followers')]").text
    assert "followers" in followers_info


# testowanie licznika following po zaobserwowaniu
def test_following(registered, flask, driver):
    wait = WebDriverWait(driver, timeout=10)

    login_user(driver, wait, "nowyuser1234", "haslo1234")

    driver.get("http://127.0.0.1:5000/user/drugitestuser999")

    wait.until(EC.presence_of_element_located((By.XPATH, "//input[@value='Follow']")))
    follow_button = driver.find_element(By.XPATH, "//input[@value='Follow']")
    follow_button.click()

    wait.until(EC.presence_of_element_located((By.XPATH, "//input[@value='Unfollow']")))

    driver.get("http://127.0.0.1:5000/user/nowyuser1234")

    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    page_text = driver.find_element(By.TAG_NAME, 'body').text
    assert "1 following" in page_text.lower()


# dostarcza wiadomosc do innego usera
def test_message(registered, flask, driver):
    wait = WebDriverWait(driver, timeout=10)

    login_user(driver, wait, "nowyuser1234", "haslo1234")

    driver.get("http://127.0.0.1:5000/send_message/drugitestuser999")

    wait.until(EC.presence_of_element_located((By.ID, "message")))
    driver.find_element(By.ID, "message").send_keys("Testtestttt")
    driver.find_element(By.ID, "submit").click()

    wait.until(lambda d: "drugitestuser999" in d.current_url)
    assert "drugitestuser999" in driver.current_url


# nie dostarcza wiadomosci bo wiadomosc jest pusta
def test_message_error(registered, flask, driver):
    wait = WebDriverWait(driver, timeout=10)

    login_user(driver, wait, "nowyuser1234", "haslo1234")

    driver.get("http://127.0.0.1:5000/send_message/drugitestuser999")

    wait.until(EC.presence_of_element_located((By.ID, "submit")))
    driver.find_element(By.ID, "submit").click()

    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    page_text = driver.find_element(By.TAG_NAME, 'body').text
    assert "required" in page_text.lower() or "send_message" in driver.current_url