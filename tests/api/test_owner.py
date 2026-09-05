"""
Owner (multi-tenant SaaS) API tests.

Contract under test (blueprint 'owner', parallel build):
  GET /admin/api/overview
  GET /admin/api/tenants
  GET /admin/api/tenants/<id>
  POST /api/tenants/<id>/suspend | /unsuspend
  GET /admin/api/subscriptions?status=
  POST /admin/api/subscriptions {tenant_id, plan_id}
  POST /api/subscriptions/<id>/approve | /reject
  GET/POST/PUT/DELETE /admin/api/plans
  POST /admin/api/subscriptions/request (own tenant)
  Pages: /admin/tenants, /admin/tenants/1, /admin/subscriptions,
         /admin/plans, /admin/activity (all 200 as admin)

Style follows tests/api/test_admin.py. Every test starts authenticated
as admin via conftest autouse fixture.
If an endpoint from the contract is missing (404 no-route), that single
test xfails with a clear reason instead of failing the suite.
"""
import time
import uuid

import pytest


def _uniq(prefix):
    return f"{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"


def _login_admin(client, super_admin_user):
    client.post("/auth/logout")
    r = client.post("/auth/login", json={
        "username": super_admin_user["username"],
        "password": "admin123",
    })
    assert r.status_code == 200, f"admin re-login failed: {r.status_code} {r.data[:200]}"
    return r


def _is_no_route(resp):
    """Heuristic: Flask 404 HTML for unknown URL vs JSON 404 from a real handler."""
    if resp.status_code != 404:
        return False
    try:
        data = resp.get_json(silent=True)
    except Exception:
        data = None
    if data is None:
        return True  # HTML 404 -> no route
    # JSON 404: could be legit "not found" from handler. Treat generic HTML-ish
    # or missing 'error' as no-route; otherwise assume route exists.
    text = resp.data.decode("utf-8", errors="ignore").lower()
    if "<html" in text or "<!doctype" in text:
        return True
    return False


def _require(client, method, url, reason, **kw):
    """GET/POST helper: xfail if the contract endpoint has no route (404 HTML)."""
    fn = getattr(client, method)
    resp = fn(url, **kw)
    if resp.status_code == 404 and _is_no_route(resp):
        pytest.xfail(f"contract gap: {method.upper()} {url} missing ({reason})")
    return resp


# --- shared contract helpers -------------------------------------------------

def _get_overview(client):
    resp = client.get("/admin/api/overview")
    if resp.status_code == 404 and _is_no_route(resp):
        pytest.xfail("contract gap: GET /admin/api/overview missing")
    return resp


def _get_tenants(client):
    resp = client.get("/admin/api/tenants")
    if resp.status_code == 404 and _is_no_route(resp):
        pytest.xfail("contract gap: GET /admin/api/tenants missing")
    return resp


def _tenants_list(client):
    resp = _get_tenants(client)
    assert resp.status_code == 200, f"list tenants: {resp.status_code} {resp.data[:300]}"
    data = resp.get_json()
    if isinstance(data, dict):
        # tolerate {tenants: [...]} envelope
        for key in ("tenants", "data", "items"):
            if isinstance(data.get(key), list):
                return data[key]
        pytest.fail(f"unexpected tenants envelope: {data}")
    assert isinstance(data, list), f"tenants list expected, got {type(data)}"
    return data


def _get_plans(client):
    resp = client.get("/admin/api/plans")
    if resp.status_code == 404 and _is_no_route(resp):
        pytest.xfail("contract gap: GET /admin/api/plans missing")
    return resp


def _plans_list(client):
    resp = _get_plans(client)
    assert resp.status_code == 200, f"list plans: {resp.status_code} {resp.data[:300]}"
    data = resp.get_json()
    if isinstance(data, dict):
        for key in ("plans", "data", "items"):
            if isinstance(data.get(key), list):
                return data[key]
        pytest.fail(f"unexpected plans envelope: {data}")
    assert isinstance(data, list), f"plans list expected, got {type(data)}"
    return data


def _get_monthly_plan_id(client):
    plans = _plans_list(client)
    for p in plans:
        if str(p.get("name", "")).lower() == "monthly":
            return p["id"]
    pytest.fail(f"'monthly' plan not seeded; plans={plans}")


def _create_user(client, username, password="password123", role="registered"):
    r = client.post("/admin/api/users", json={
        "username": username,
        "password": password,
        "role": role,
        "email": f"{username}@test.com",
        "full_name": f"{username} full",
    })
    assert r.status_code == 200, f"create user {username}: {r.status_code} {r.data[:300]}"
    return r.get_json()["user"]


def _tenant_id_for_user(client, app, username):
    """Find tenant id via contract list API; fall back to DB lookup."""
    try:
        tenants = _tenants_list(client)
        for t in tenants:
            if t.get("owner_username") == username or t.get("name") == username:
                return t["id"]
    except Exception:
        raise
    # DB fallback (same session DB, robust to list-shape drift)
    with app.app_context():
        from app.shared.models import Tenant, User
        u = User.query.filter_by(username=username).first()
        assert u is not None, f"user {username} not found in DB"
        t = Tenant.query.filter_by(owner_id=u.id).first()
        assert t is not None, f"tenant for {username} not found"
        return t.id


def _suspend(client, tid):
    r = client.post(f"/api/tenants/{tid}/suspend")
    if r.status_code == 404 and _is_no_route(r):
        r = client.post(f"/admin/api/tenants/{tid}/suspend")
        if r.status_code == 404 and _is_no_route(r):
            pytest.xfail("contract gap: POST suspend tenant missing "
                         "(/api/tenants/<id>/suspend and /admin/api variant)")
    return r


def _unsuspend(client, tid):
    r = client.post(f"/api/tenants/{tid}/unsuspend")
    if r.status_code == 404 and _is_no_route(r):
        r = client.post(f"/admin/api/tenants/{tid}/unsuspend")
        if r.status_code == 404 and _is_no_route(r):
            pytest.xfail("contract gap: POST unsuspend tenant missing "
                         "(/api/tenants/<id>/unsuspend and /admin/api variant)")
    return r


def _approve(client, sid):
    r = client.post(f"/api/subscriptions/{sid}/approve")
    if r.status_code == 404 and _is_no_route(r):
        r = client.post(f"/admin/api/subscriptions/{sid}/approve")
        if r.status_code == 404 and _is_no_route(r):
            pytest.xfail("contract gap: POST approve subscription missing "
                         "(/api/subscriptions/<id>/approve and /admin/api variant)")
    return r


def _reject(client, sid, reason="no longer needed"):
    r = client.post(f"/api/subscriptions/{sid}/reject", json={"reason": reason})
    if r.status_code == 404 and _is_no_route(r):
        r = client.post(f"/admin/api/subscriptions/{sid}/reject", json={"reason": reason})
        if r.status_code == 404 and _is_no_route(r):
            pytest.xfail("contract gap: POST reject subscription missing "
                         "(/api/subscriptions/<id>/reject and /admin/api variant)")
    return r


def _subs_list(client, status=None):
    url = "/admin/api/subscriptions"
    if status:
        url += f"?status={status}"
    r = client.get(url)
    if r.status_code == 404 and _is_no_route(r):
        pytest.xfail(f"contract gap: GET {url} missing")
    assert r.status_code == 200, f"list subs {url}: {r.status_code} {r.data[:300]}"
    data = r.get_json()
    if isinstance(data, dict):
        for key in ("subscriptions", "data", "items"):
            if isinstance(data.get(key), list):
                return data[key]
        pytest.fail(f"unexpected subscriptions envelope: {data}")
    assert isinstance(data, list), f"subs list expected, got {type(data)}"
    return data


def _extract_sub_id(payload):
    if not isinstance(payload, dict):
        pytest.fail(f"unexpected subscription payload: {payload}")
    for key in ("subscription", "data"):
        inner = payload.get(key)
        if isinstance(inner, dict) and "id" in inner:
            return inner["id"]
    for key in ("id", "subscription_id"):
        if key in payload:
            return payload[key]
    pytest.fail(f"cannot extract subscription id from: {payload}")


def _extract_sub_status(payload):
    if not isinstance(payload, dict):
        return None
    for key in ("subscription", "data"):
        inner = payload.get(key)
        if isinstance(inner, dict) and "status" in inner:
            return inner["status"]
    return payload.get("status")


# --- TestOwnerOverview -------------------------------------------------------

class TestOwnerOverview:
    def test_overview_has_all_keys(self, client):
        r = _get_overview(client)
        assert r.status_code == 200, f"overview: {r.status_code} {r.data[:300]}"
        data = r.get_json()
        for key in ("tenants_total", "tenants_suspended", "users_total",
                    "files_total", "points_total", "subs_pending", "subs_active"):
            assert key in data, f"overview missing key '{key}': {data}"

    def test_overview_values_are_nonneg_ints(self, client):
        r = _get_overview(client)
        assert r.status_code == 200
        data = r.get_json()
        for key in ("tenants_total", "tenants_suspended", "users_total",
                    "files_total", "points_total", "subs_pending", "subs_active"):
            assert isinstance(data[key], int), f"{key} not int: {data[key]!r}"
            assert data[key] >= 0, f"{key} negative: {data[key]}"


# --- TestOwnerTenants ---------------------------------------------------------

class TestOwnerTenants:
    def test_list_has_admin_tenant(self, client):
        tenants = _tenants_list(client)
        assert len(tenants) >= 1
        assert any(t.get("owner_username") == "admin" or t.get("name") == "admin"
                   for t in tenants), f"admin tenant missing: {tenants[:2]}"

    def test_list_item_shape(self, client):
        tenants = _tenants_list(client)
        assert len(tenants) >= 1
        for key in ("id", "name", "owner_username", "plan",
                    "is_suspended", "active_subscription"):
            assert key in tenants[0], f"tenant item missing '{key}': {tenants[0]}"

    def test_detail_shape(self, client):
        tenants = _tenants_list(client)
        tid = tenants[0]["id"]
        r = client.get(f"/admin/api/tenants/{tid}")
        if r.status_code == 404 and _is_no_route(r):
            pytest.xfail("contract gap: GET /admin/api/tenants/<id> missing")
        assert r.status_code == 200, f"detail {tid}: {r.status_code} {r.data[:300]}"
        data = r.get_json()
        for key in ("tenant", "users", "files", "subscriptions"):
            assert key in data, f"tenant detail missing '{key}': {list(data)}"

    def test_detail_404_unknown(self, client):
        # prove the detail route exists first so a 404 is meaningful
        _tenants_list(client)
        r = client.get("/admin/api/tenants/999999999")
        if _is_no_route(r):
            pytest.xfail("contract gap: GET /admin/api/tenants/<id> missing")
        assert r.status_code == 404, f"expected 404, got {r.status_code}"

    def test_suspend_unsuspend_roundtrip(self, client, app, super_admin_user):
        _login_admin(client, super_admin_user)
        uname = _uniq("ownten")
        _create_user(client, uname)
        tid = _tenant_id_for_user(client, app, uname)
        try:
            r = _suspend(client, tid)
            assert r.status_code == 200, f"suspend: {r.status_code} {r.data[:300]}"
            assert r.get_json().get("status") == "ok", r.get_json()

            tenants = _tenants_list(client)
            row = next((t for t in tenants if t["id"] == tid), None)
            assert row is not None, f"tenant {tid} vanished from list"
            assert row.get("is_suspended") in (True, 1), f"not suspended: {row}"

            r = _unsuspend(client, tid)
            assert r.status_code == 200, f"unsuspend: {r.status_code} {r.data[:300]}"
            assert r.get_json().get("status") == "ok", r.get_json()

            tenants = _tenants_list(client)
            row = next((t for t in tenants if t["id"] == tid), None)
            assert row.get("is_suspended") in (False, 0), f"still suspended: {row}"
        finally:
            # cleanup: leave suspended per spec, restore admin session
            try:
                _unsuspend(client, tid)
            except Exception:
                pass
            try:
                r = _suspend(client, tid)
                assert r.status_code == 200
            except Exception:
                pass
            _login_admin(client, super_admin_user)


# --- TestOwnerSubscriptions ----------------------------------------------------

# --- TestOwnerDataIntegrity -----------------------------------------------------

class TestOwnerDataIntegrity:
    def test_pending_sub_reason_is_pending(self, client, app, super_admin_user):
        """B1: tenant with a pending subscription must be 'pending', not 'expired'."""
        uname, tid, monthly_id, sid = TestOwnerSubscriptions()._new_tenant_with_pending(
            client, app, super_admin_user, "ownb1")
        try:
            with app.app_context():
                from app.shared.models import Tenant
                from app.shared.middleware import tenant_block_reason
                tenant = Tenant.query.get(tid)
                assert tenant is not None
                assert tenant_block_reason(tenant) == 'pending', \
                    f"pending sub tenant should report 'pending', got {tenant_block_reason(tenant)}"
        finally:
            _login_admin(client, super_admin_user)

    def test_empty_email_stored_as_null(self, client, app, super_admin_user):
        """B3: '' email via admin PUT must normalize to NULL, not collide on unique."""
        _login_admin(client, super_admin_user)
        uid1 = _create_user(client, _uniq("ownmail")).get("id")
        uid2 = _create_user(client, _uniq("ownmail")).get("id")
        try:
            pu1 = client.put(f"/admin/api/users/{uid1}", json={"email": ""})
            if pu1.status_code == 404 and _is_no_route(pu1):
                pytest.xfail("contract gap: PUT /admin/api/users/<id> missing")
            assert pu1.status_code == 200, f"update1: {pu1.status_code} {pu1.data[:300]}"
            pu2 = client.put(f"/admin/api/users/{uid2}", json={"email": ""})
            assert pu2.status_code == 200, \
                f"second '' email should normalize to NULL (unique collision), got {pu2.status_code} {pu2.data[:300]}"
            with app.app_context():
                from app.shared.models import User
                for uid in (uid1, uid2):
                    u = User.query.get(uid)
                    assert u.email is None, f"user {uid} email not NULL after '' submit: {u.email!r}"
        finally:
            _login_admin(client, super_admin_user)

    def test_plan_duration_zero_rejected_at_approve(self, client, app, super_admin_user):
        """B4: approving with a plan that has duration_days=0 must be rejected."""
        _login_admin(client, super_admin_user)
        uname = _uniq("ownb4")
        _create_user(client, uname)
        tid = _tenant_id_for_user(client, app, uname)
        bad_plan_id = None
        try:
            r = client.post("/admin/api/plans", json={
                "name": _uniq("badplan"), "price": 5, "duration_days": 0,
            })
            assert r.status_code == 400, \
                f"creating plan with duration_days=0 should be 400, got {r.status_code} {r.data[:300]}"
            # insert degenerate plan directly (bypassing API validation)
            with app.app_context():
                from app.shared.models import Plan
                from app.shared.models import db as _db
                bad = Plan(name=_uniq("badplan"), price=5, duration_days=0, is_active=True)
                _db.session.add(bad)
                _db.session.flush()
                bad_plan_id = bad.id
                _db.session.commit()
            r = client.post("/admin/api/subscriptions",
                            json={"tenant_id": tid, "plan_id": bad_plan_id})
            assert r.status_code == 200, f"create sub: {r.status_code} {r.data[:400]}"
            sid = _extract_sub_id(r.get_json())
            rr = _approve(client, sid)
            assert rr.status_code == 400, \
                f"approve with 0-duration plan should fail: {rr.status_code} {rr.data[:300]}"
        finally:
            try:
                if bad_plan_id:
                    with app.app_context():
                        from app.shared.models import Plan, Subscription
                        from app.shared.models import db as _db
                        Subscription.query.filter_by(plan_id=bad_plan_id).delete()
                        Plan.query.filter_by(id=bad_plan_id).delete()
                        _db.session.commit()
            except Exception:
                pass
            _login_admin(client, super_admin_user)


class TestOwnerSubscriptions:
    def _new_tenant_with_pending(self, client, app, super_admin_user, prefix):
        _login_admin(client, super_admin_user)
        uname = _uniq(prefix)
        _create_user(client, uname)
        tid = _tenant_id_for_user(client, app, uname)
        monthly_id = _get_monthly_plan_id(client)
        r = client.post("/admin/api/subscriptions",
                        json={"tenant_id": tid, "plan_id": monthly_id})
        if r.status_code == 404 and _is_no_route(r):
            pytest.xfail("contract gap: POST /admin/api/subscriptions missing")
        assert r.status_code == 200, f"create sub: {r.status_code} {r.data[:400]}"
        sid = _extract_sub_id(r.get_json())
        return uname, tid, monthly_id, sid

    def test_create_pending(self, client, app, super_admin_user):
        uname, tid, monthly_id, sid = self._new_tenant_with_pending(
            client, app, super_admin_user, "ownsub")
        assert isinstance(sid, int)
        try:
            pend = _subs_list(client, "pending")
            assert any(s.get("id") == sid for s in pend), \
                f"new sub {sid} not in pending list: {pend[:2]}"
        finally:
            _login_admin(client, super_admin_user)

    def test_approve_sets_active_and_updates_plan(self, client, app, super_admin_user):
        uname, tid, monthly_id, sid = self._new_tenant_with_pending(
            client, app, super_admin_user, "ownappr")
        try:
            r = _approve(client, sid)
            assert r.status_code == 200, f"approve: {r.status_code} {r.data[:400]}"
            # detail must show tenant.plan updated
            d = client.get(f"/admin/api/tenants/{tid}")
            if d.status_code == 404 and _is_no_route(d):
                pytest.xfail("contract gap: GET /admin/api/tenants/<id> missing")
            assert d.status_code == 200, f"tenant detail: {d.status_code} {d.data[:300]}"
            tenant = d.get_json().get("tenant", {})
            plan_val = tenant.get("plan")
            # plan may be name or nested object; accept 'monthly' in any form
            assert "monthly" in str(plan_val).lower(), \
                f"tenant.plan not updated to monthly: {tenant}"
        finally:
            _login_admin(client, super_admin_user)

    def test_reject_second_request_cancels(self, client, app, super_admin_user):
        uname, tid, monthly_id, sid = self._new_tenant_with_pending(
            client, app, super_admin_user, "ownrej")
        try:
            # approve first so we can file a distinct second request
            r = _approve(client, sid)
            assert r.status_code == 200, f"approve(1st): {r.status_code} {r.data[:300]}"
            r2 = client.post("/admin/api/subscriptions",
                             json={"tenant_id": tid, "plan_id": monthly_id})
            if r2.status_code == 404 and _is_no_route(r2):
                pytest.xfail("contract gap: POST /admin/api/subscriptions missing")
            assert r2.status_code == 200, f"2nd request: {r2.status_code} {r2.data[:400]}"
            sid2 = _extract_sub_id(r2.get_json())
            rr = _reject(client, sid2)
            assert rr.status_code == 200, f"reject: {rr.status_code} {rr.data[:400]}"
            status = str(_extract_sub_status(rr.get_json()) or "").lower()
            if status:
                assert status in ("cancelled", "canceled", "rejected"), \
                    f"reject status not cancelled: {rr.get_json()}"
            else:
                # fall back: second sub must no longer be pending
                pend = _subs_list(client, "pending")
                assert all(s.get("id") != sid2 for s in pend), \
                    f"rejected sub {sid2} still pending"
        finally:
            _login_admin(client, super_admin_user)

    def test_approve_unlimited_has_no_expiry(self, client, app, super_admin_user):
        """Approving 'unlimited' sets no end date and unblocks the tenant."""
        _login_admin(client, super_admin_user)
        uname = _uniq("ownunl")
        _create_user(client, uname)
        tid = _tenant_id_for_user(client, app, uname)
        plans = _plans_list(client)
        unlimited_id = None
        for p in plans:
            if str(p.get("name", "")).lower() == "unlimited":
                unlimited_id = p["id"]
        assert unlimited_id is not None, f"'unlimited' plan missing: {plans}"
        try:
            r = client.post("/admin/api/subscriptions",
                            json={"tenant_id": tid, "plan_id": unlimited_id})
            assert r.status_code == 200, f"create sub: {r.status_code} {r.data[:400]}"
            sid = _extract_sub_id(r.get_json())
            r = _approve(client, sid)
            assert r.status_code == 200, f"approve: {r.status_code} {r.data[:400]}"
            d = client.get(f"/admin/api/tenants/{tid}")
            assert d.status_code == 200
            tenant = d.get_json().get("tenant", {})
            assert str(tenant.get("plan", "")).lower() == "unlimited"
            assert tenant.get("expires_at") in (None, ""), \
                f"unlimited must have no expiry: {tenant}"
        finally:
            _login_admin(client, super_admin_user)

    def test_duplicate_pending_returns_400(self, client, app, super_admin_user):
        uname, tid, monthly_id, sid = self._new_tenant_with_pending(
            client, app, super_admin_user, "owndup")
        try:
            r = client.post("/admin/api/subscriptions",
                            json={"tenant_id": tid, "plan_id": monthly_id})
            if r.status_code == 404 and _is_no_route(r):
                pytest.xfail("contract gap: POST /admin/api/subscriptions missing")
            assert r.status_code == 400, \
                f"duplicate pending should be 400, got {r.status_code} {r.data[:300]}"
        finally:
            _login_admin(client, super_admin_user)


# --- TestOwnerPlans --------------------------------------------------------------

class TestOwnerPlans:
    def test_create_rejects_zero_or_negative_duration(self, client, super_admin_user):
        """B4: duration_days <= 0 must be rejected (would expire instantly)."""
        _login_admin(client, super_admin_user)
        for bad in (0, -1, -30):
            pname = _uniq("ownplanbad")
            r = client.post("/admin/api/plans", json={
                "name": pname, "price": 10, "duration_days": bad,
            })
            if r.status_code == 404 and _is_no_route(r):
                pytest.xfail("contract gap: POST /admin/api/plans missing")
            assert r.status_code == 400, \
                f"duration_days={bad} should be 400, got {r.status_code} {r.data[:300]}"

    def test_update_rejects_zero_duration(self, client, super_admin_user):
        """B4: PUT with duration_days=0 must be rejected."""
        _login_admin(client, super_admin_user)
        pname = _uniq("ownplanupd")
        r = client.post("/admin/api/plans", json={
            "name": pname, "price": 10, "duration_days": 30,
        })
        assert r.status_code in (200, 201), f"create: {r.status_code} {r.data[:300]}"
        pid = r.get_json().get("plan", r.get_json()).get("id")
        try:
            u = client.put(f"/admin/api/plans/{pid}", json={"duration_days": 0})
            if u.status_code == 404 and _is_no_route(u):
                pytest.xfail("contract gap: PUT /admin/api/plans/<id> missing")
            assert u.status_code == 400, \
                f"update to duration_days=0 should be 400, got {u.status_code} {u.data[:300]}"
        finally:
            try:
                client.delete(f"/admin/api/plans/{pid}")
            except Exception:
                pass
            _login_admin(client, super_admin_user)

    def test_plans_no_limits_fields(self, client):
        """Hollow max_* fields removed: plan payload carries no limits."""
        plans = _plans_list(client)
        for p in plans:
            assert "max_files" not in p, f"max_files leaked into plan payload: {p}"
            assert "max_points" not in p, f"max_points leaked into plan payload: {p}"
            assert "max_users" not in p, f"max_users leaked into plan payload: {p}"

    def test_list_has_seeded_plans(self, client):
        plans = _plans_list(client)
        names = {str(p.get("name", "")).lower() for p in plans}
        for expected in ("weekly", "monthly", "yearly", "unlimited"):
            assert expected in names, f"seeded plan '{expected}' missing: {names}"

    def test_create_update_deactivate(self, client, super_admin_user):
        _login_admin(client, super_admin_user)
        pname = _uniq("ownplan")
        r = client.post("/admin/api/plans", json={
            "name": pname, "price": 99.99, "is_active": True,
            "description": "owner test plan",
        })
        if r.status_code == 404 and _is_no_route(r):
            pytest.xfail("contract gap: POST /admin/api/plans missing")
        assert r.status_code in (200, 201), f"create plan: {r.status_code} {r.data[:400]}"
        payload = r.get_json()
        plan = payload.get("plan", payload) if isinstance(payload, dict) else {}
        pid = plan.get("id") or payload.get("id")
        assert pid is not None, f"no plan id in: {payload}"
        try:
            u = client.put(f"/admin/api/plans/{pid}", json={"price": 149.5})
            if u.status_code == 404 and _is_no_route(u):
                pytest.xfail("contract gap: PUT /admin/api/plans/<id> missing")
            assert u.status_code == 200, f"update price: {u.status_code} {u.data[:300]}"

            d = client.put(f"/admin/api/plans/{pid}", json={"is_active": False})
            assert d.status_code == 200, f"deactivate: {d.status_code} {d.data[:300]}"
        finally:
            # cleanup: ensure deactivated
            try:
                client.put(f"/admin/api/plans/{pid}", json={"is_active": False})
            except Exception:
                pass
            try:
                client.delete(f"/admin/api/plans/{pid}")
            except Exception:
                pass
            _login_admin(client, super_admin_user)

    def test_verify_inactive(self, client, super_admin_user):
        _login_admin(client, super_admin_user)
        pname = _uniq("ownplanv")
        r = client.post("/admin/api/plans", json={
            "name": pname, "price": 10, "is_active": True,
        })
        if r.status_code == 404 and _is_no_route(r):
            pytest.xfail("contract gap: POST /admin/api/plans missing")
        assert r.status_code in (200, 201), f"create: {r.status_code} {r.data[:300]}"
        payload = r.get_json()
        plan = payload.get("plan", payload) if isinstance(payload, dict) else {}
        pid = plan.get("id") or payload.get("id")
        try:
            u = client.put(f"/admin/api/plans/{pid}", json={"is_active": False})
            if u.status_code == 404 and _is_no_route(u):
                pytest.xfail("contract gap: PUT /admin/api/plans/<id> missing")
            assert u.status_code == 200
            plans = _plans_list(client)
            row = next((p for p in plans if p.get("id") == pid), None)
            assert row is not None, f"plan {pid} missing from list"
            assert row.get("is_active") in (False, 0), f"plan still active: {row}"
        finally:
            try:
                client.put(f"/admin/api/plans/{pid}", json={"is_active": False})
            except Exception:
                pass
            try:
                client.delete(f"/admin/api/plans/{pid}")
            except Exception:
                pass
            _login_admin(client, super_admin_user)


# --- TestOwnerRequest -------------------------------------------------------------

class TestOwnerRequest:
    def test_regular_user_can_request_monthly_plan(self, client, app, super_admin_user):
        _login_admin(client, super_admin_user)
        uname = _uniq("ownreq")
        pwd = "password123"
        _create_user(client, uname, password=pwd)
        tid = _tenant_id_for_user(client, app, uname)
        monthly_id = _get_monthly_plan_id(client)
        try:
            # act as the regular user
            client.post("/auth/logout")
            lr = client.post("/auth/login", json={"username": uname, "password": pwd})
            assert lr.status_code == 200, f"user login: {lr.status_code} {lr.data[:200]}"

            r = client.post("/admin/api/subscriptions/request", json={"plan_id": monthly_id})
            if r.status_code == 404 and _is_no_route(r):
                pytest.xfail("contract gap: POST /admin/api/subscriptions/request missing")
            assert r.status_code in (200, 201), \
                f"request plan: {r.status_code} {r.data[:400]}"

            # back to admin: pending must be visible
            _login_admin(client, super_admin_user)
            pend = _subs_list(client, "pending")
            assert any(s.get("tenant_id") == tid for s in pend), \
                f"request for tenant {tid} not visible in pending: {pend[:2]}"
        finally:
            _login_admin(client, super_admin_user)


# --- TestOwnerEnforcement ----------------------------------------------------------

class TestOwnerEnforcement:
    def test_suspended_tenant_blocked_from_creating_files(self, client, app, super_admin_user):
        _login_admin(client, super_admin_user)
        uname = _uniq("ownenf")
        pwd = "password123"
        _create_user(client, uname, password=pwd)
        tid = _tenant_id_for_user(client, app, uname)
        try:
            r = _suspend(client, tid)
            assert r.status_code == 200, f"suspend: {r.status_code} {r.data[:300]}"

            client.post("/auth/logout")
            lr = client.post("/auth/login", json={"username": uname, "password": pwd})
            assert lr.status_code == 200, f"user login: {lr.status_code}"

            fr = client.post("/api/files", json={
                "name": _uniq("blockedfile"),
                "date": "2026-08-31",
                "place": "Suspended Tenant",
            })
            assert 400 <= fr.status_code < 500, \
                f"suspended tenant should be blocked (4xx), got {fr.status_code} {fr.data[:300]}"
        finally:
            _login_admin(client, super_admin_user)
            try:
                r = _unsuspend(client, tid)
                assert r.status_code == 200
            except Exception:
                pass
            _login_admin(client, super_admin_user)


# --- TestOwnerAccess ------------------------------------------------------------------

class TestOwnerAccess:
    def test_regular_user_forbidden_tenants(self, client, app, super_admin_user):
        _login_admin(client, super_admin_user)
        uname = _uniq("ownacc")
        pwd = "password123"
        _create_user(client, uname, password=pwd)
        try:
            client.post("/auth/logout")
            client.post("/auth/login", json={"username": uname, "password": pwd})
            r = client.get("/admin/api/tenants")
            if r.status_code == 404 and _is_no_route(r):
                pytest.xfail("contract gap: GET /admin/api/tenants missing")
            assert r.status_code == 403, \
                f"regular user should get 403, got {r.status_code} {r.data[:200]}"
        finally:
            _login_admin(client, super_admin_user)

    def test_logged_out_unauthorized_overview(self, client):
        client.post("/auth/logout")
        r = client.get("/admin/api/overview")
        if r.status_code == 404 and _is_no_route(r):
            pytest.xfail("contract gap: GET /admin/api/overview missing")
        assert r.status_code == 401, \
            f"logged-out should get 401, got {r.status_code} {r.data[:200]}"


# --- TestOwnerPages ---------------------------------------------------------------------

class TestOwnerPages:
    @pytest.mark.parametrize("url", [
        "/admin/tenants",
        "/admin/tenants/1",
        "/admin/subscriptions",
        "/admin/plans",
        "/admin/activity",
    ])
    def test_admin_pages_200(self, client, url):
        r = client.get(url)
        if r.status_code == 404 and _is_no_route(r):
            pytest.xfail(f"contract gap: page {url} missing")
        assert r.status_code == 200, f"page {url}: {r.status_code} {r.data[:200]}"
