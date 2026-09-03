"""
Self-signup + package request + owner approval flow tests.
Covers: GET/POST /auth/register, /waiting room, login redirect,
owner queue contact info.
"""
import time
import uuid


def _uniq(prefix):
    return f"{prefix}_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"


def _logout(client):
    client.post("/auth/logout")


def _monthly_id(client):
    plans = client.get("/admin/api/plans").get_json()
    for p in plans:
        if str(p.get("name", "")).lower() == "monthly":
            return p["id"]
    raise AssertionError(f"monthly plan missing: {plans}")


def _register(client, username, plan_id=None, **kw):
    payload = {
        "username": username,
        "password": kw.get("password", "password123"),
        "full_name": kw.get("full_name", f"{username} full"),
        "email": kw.get("email", f"{username}@test.com"),
        "phone": kw.get("phone", "+970500000000"),
        "whatsapp": kw.get("whatsapp", "+970599000000"),
    }
    if plan_id is not None:
        payload["plan_id"] = plan_id
    return client.post("/auth/register", json=payload)


class TestRegisterPage:
    def test_register_page_loads_logged_out(self, client):
        _logout(client)
        r = client.get("/auth/register")
        assert r.status_code == 200
        assert b"plan_id" in r.data

    def test_register_page_redirects_when_logged_in(self, client, super_admin_user):
        # autouse fixture already logged in as admin
        r = client.get("/auth/register")
        assert r.status_code == 302


class TestRegisterFlow:
    def test_full_signup_creates_user_tenant_and_pending(self, client, app, super_admin_user):
        _logout(client)
        uname = _uniq("regflow")
        # need plan id: login as admin briefly to read plans
        client.post("/auth/login", json={"username": super_admin_user["username"],
                                         "password": "admin123"})
        monthly_id = _monthly_id(client)
        _logout(client)

        r = _register(client, uname, plan_id=monthly_id, whatsapp="+970599111222")
        assert r.status_code == 200, f"register: {r.status_code} {r.data[:300]}"
        assert r.get_json()["status"] == "ok"

        from app.shared.models import User, Tenant, Subscription
        with app.app_context():
            u = User.query.filter_by(username=uname).first()
            assert u is not None
            assert u.whatsapp == "+970599111222"
            assert u.email == f"{uname}@test.com"
            t = u.owned_tenant
            assert t is not None and t.plan == "none"
            subs = Subscription.query.filter_by(tenant_id=t.id).all()
            assert len(subs) == 1 and subs[0].status == "pending"
            assert subs[0].plan_id == monthly_id

    def test_register_duplicate_username_400(self, client):
        _logout(client)
        uname = _uniq("regdup")
        r1 = _register(client, uname)
        assert r1.status_code == 200
        r2 = _register(client, uname)
        assert r2.status_code == 400
        assert "already exists" in r2.get_json()["error"]

    def test_register_bad_plan_400(self, client):
        _logout(client)
        r = _register(client, _uniq("regbad"), plan_id=999999999)
        assert r.status_code == 400

    def test_register_short_password_400(self, client):
        _logout(client)
        r = _register(client, _uniq("regshort"), password="123")
        assert r.status_code == 400


class TestWaitingRoom:
    def _signup_blocked_user(self, client, app, super_admin_user, prefix):
        _logout(client)
        uname = _uniq(prefix)
        client.post("/auth/login", json={"username": super_admin_user["username"],
                                         "password": "admin123"})
        monthly_id = _monthly_id(client)
        _logout(client)
        r = _register(client, uname, plan_id=monthly_id)
        assert r.status_code == 200
        return uname

    def test_blocked_user_login_redirects_to_waiting(self, client, app, super_admin_user):
        uname = self._signup_blocked_user(client, app, super_admin_user, "regwait")
        r = client.post("/auth/login", json={"username": uname, "password": "password123"})
        assert r.status_code == 200
        assert r.get_json()["redirect"].endswith("/waiting"), r.get_json()

    def test_waiting_page_shows_pending(self, client, app, super_admin_user):
        uname = self._signup_blocked_user(client, app, super_admin_user, "regwaitpg")
        client.post("/auth/login", json={"username": uname, "password": "password123"})
        r = client.get("/waiting")
        assert r.status_code == 200
        assert "بانتظار".encode() in r.data or b"pending" in r.data.lower()

    def test_admin_waiting_redirects_to_platform(self, client, super_admin_user):
        # Platform entry is the landing (program list), never inside one program.
        client.post("/auth/login", json={"username": super_admin_user["username"],
                                         "password": "admin123"})
        r = client.get("/waiting")
        assert r.status_code == 302
        assert r.headers["Location"] == "/", r.headers["Location"]

    def test_owner_queue_shows_contact(self, client, app, super_admin_user):
        uname = self._signup_blocked_user(client, app, super_admin_user, "regcontact")
        client.post("/auth/login", json={"username": super_admin_user["username"],
                                         "password": "admin123"})
        r = client.get("/admin/api/subscriptions?status=pending")
        assert r.status_code == 200
        mine = [s for s in r.get_json() if s.get("tenant_name") == uname]
        assert mine, "new request not in owner queue"
        contact = mine[0].get("contact") or {}
        assert contact.get("whatsapp"), f"contact missing whatsapp: {mine[0]}"
        assert contact.get("email") == f"{uname}@test.com"

    def test_approve_unblocks_login_to_platform(self, client, app, super_admin_user):
        uname = self._signup_blocked_user(client, app, super_admin_user, "regappr")
        client.post("/auth/login", json={"username": super_admin_user["username"],
                                         "password": "admin123"})
        pend = client.get("/admin/api/subscriptions?status=pending").get_json()
        sid = next(s["id"] for s in pend if s.get("tenant_name") == uname)
        r = client.post(f"/admin/api/subscriptions/{sid}/approve")
        assert r.status_code == 200
        _logout(client)
        r = client.post("/auth/login", json={"username": uname, "password": "password123"})
        assert r.status_code == 200
        # Approved users land on the platform (program list), not inside MAS.
        assert r.get_json()["redirect"] == "/", r.get_json()
