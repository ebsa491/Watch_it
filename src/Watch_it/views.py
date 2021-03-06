from Watch_it import app, db
import json
import requests
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import (
    render_template,
    request,
    session,
    abort,
    redirect,
    url_for,
)
from Watch_it.models import User
from Watch_it.db_config import (
    PANEL_USERNAME,
    PANEL_PASSWORD,
)

limiter = Limiter(
    app,
    key_func=get_remote_address,
)


@app.route("/")
def home():
    """
    The home page.
    This function inserts the client information
    and renders `templates/Home/index.html`.
    """

    user_ip = request.remote_addr
    user_platform = request.user_agent.platform
    user_browser = request.user_agent.browser
    user_country = "Unknown"

    if user_ip != '127.0.0.1':  # Localhost

        try:
            info = json.loads(
                requests.get(f"http://ip-api.com/json/{user_ip}").text
            )

            user_country = info['countryCode']  # Like: AU, US, UK, etc.
        except Exception as err:
            print(f"ERROR (country code)=> {err}")

        try:
            new_user = User(user_platform, user_browser, user_ip, user_country)

            db.session.add(new_user)
            db.session.commit()
        except Exception as err:
            print(
                f"""
                Inserting failed...
                ({user_platform}, {user_browser}, {user_ip}, {user_country}).
                Error =>\n{err}
                """
            )

    return render_template(
        "Home/index.html",
        platform=user_platform,
        browser=user_browser,
        ip=user_ip,
        country=user_country,
    )


# This route is not secure. Change it.
@app.route('/login', methods=["GET", "POST"])
@limiter.limit("15 per 2 minutes")  # For brute force
def admin_login():
    """
    The admin login page.
    This function sets a new session for admin `templates/Login/index.html`
    and redirects to `dashboard`.
    Also `abort(403)` for wrong username or password.
    """

    if session.get("username", '') == PANEL_USERNAME:
        # The client logged in before
        return redirect(url_for('dashboard'))  # THE END OF THE FUNCTION

    if request.method == 'GET':
        # Show login template
        return render_template("Login/index.html")  # THE END OF THE FUNCTION

    try:
        # The client entered the username and password
        username = request.form['username']
        password = request.form['password']
    except Exception:
        return abort(400)

    if username == PANEL_USERNAME and password == PANEL_PASSWORD:
        # Username and password is correct.
        session["username"] = username
        return redirect(url_for("dashboard"))  # THE END OF THE FUNCTION

    # Unauthorized
    return abort(403)


@app.route('/dashboard')
def dashboard():
    """
    The dashboard.
    This function renders `templates/Dashboard/index.html`
    and redirects to `admin_login`(means there's no session).
    """

    if session.get("username", '') == PANEL_USERNAME:
        # The client logged in

        total_users_count = User.query.count()

        firefox_users_count = User.query.filter_by(browser='firefox').count()
        chrome_users_count = User.query.filter_by(browser='chrome').count()
        opera_users_count = User.query.filter_by(browser='opera').count()
        other_users_count = User.query.filter(
            ~User.browser.in_(['firefox', 'chrome', 'opera'])
        ).count()

        latest_users = User.query.order_by(-User.id).limit(5).all()

        return render_template(
            "Dashboard/index.html",
            username=session["username"],
            total=total_users_count,
            firefox=firefox_users_count,
            chrome=chrome_users_count,
            opera=opera_users_count,
            other=other_users_count,
            latest_users=latest_users,
        )  # THE END OF THE FUNCTION

    # Redirect to the login page
    return redirect(url_for("admin_login"))


@app.route("/logout")
def admin_logout():
    """
    This function pops the session and redirects you to `admin_login`.
    """

    if session.get('username', '') != '':
        session.pop("username")

    return redirect(url_for("admin_login"))


@app.errorhandler(404)
def error_404(err):
    """
    Renders `templates/Error/404.html` for Not found error.
    """
    return render_template("Error/404.html"), 404


@app.errorhandler(403)
def error_403(err):
    """
    Redners `templates/Error/403.html` for Forbidden error.
    """
    return render_template("Error/403.html"), 403


@app.errorhandler(429)
def error_429(err):
    """
    Renders `templates/Error/429.html` for Too many requests error.
    """
    return render_template("Error/429.html"), 429
