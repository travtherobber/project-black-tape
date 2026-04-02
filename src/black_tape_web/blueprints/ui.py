from hmac import compare_digest

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for


ui_bp = Blueprint("ui", __name__)


@ui_bp.before_request
def protect_ui_post_actions():
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return None
    if request.endpoint in {"ui.login_submit"}:
        return None
    if request.form.get("csrf_token") != session.get("_csrf_token"):
        return redirect(url_for("ui.login"))
    return None


@ui_bp.get("/login")
def login():
    if not current_app.config.get("BLACKTAPE_PASSWORD"):
        return redirect(url_for("ui.dashboard"))
    if session.get("authenticated"):
        return redirect(url_for("ui.dashboard"))
    return render_template("pages/login.html", page_name="login", next_path=request.args.get("next", "/dashboard"))


@ui_bp.post("/login")
def login_submit():
    if not current_app.config.get("BLACKTAPE_PASSWORD"):
        return redirect(url_for("ui.dashboard"))

    submitted = request.form.get("password", "")
    expected = current_app.config.get("BLACKTAPE_PASSWORD", "")
    if compare_digest(submitted, expected):
        session["authenticated"] = True
        next_path = request.form.get("next", "/dashboard")
        if not next_path.startswith("/"):
            next_path = "/dashboard"
        return redirect(next_path)

    return render_template(
        "pages/login.html",
        page_name="login",
        next_path=request.form.get("next", "/dashboard"),
        login_error="Invalid password",
    ), 401


@ui_bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("ui.login"))


@ui_bp.get("/")
def welcome():
    return render_template("pages/home.html", page_name="dashboard")


@ui_bp.get("/dashboard")
def dashboard():
    return render_template("pages/home.html", page_name="dashboard")


@ui_bp.get("/chats")
def chats():
    return render_template("pages/chat.html", page_name="chat")


@ui_bp.get("/map")
def map_view():
    return render_template("pages/map.html", page_name="map")


@ui_bp.get("/friends")
def friends():
    return render_template("pages/friends.html", page_name="friends")


@ui_bp.get("/timeline")
def timeline():
    return render_template("pages/timeline.html", page_name="timeline")


@ui_bp.get("/analytics")
def analytics():
    return render_template("pages/analytics.html", page_name="analytics")


@ui_bp.get("/explore")
def explore():
    return render_template("pages/explore.html", page_name="explore")
