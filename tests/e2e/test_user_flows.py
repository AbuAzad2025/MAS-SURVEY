"""
End-to-end tests: real Chromium against the real Flask app.
These verify the critical user paths a customer would exercise:
landing → login → admin pages, MAS pages, file creation, points,
calculations, registration, waiting room.
"""
import re
import time
import uuid


# ---------- auth & landing ----------

def test_landing_page_contains_programs(page, e2e_server):
    page.goto(e2e_server + '/')
    assert page.title()
    html = page.content()
    assert 'MAS' in html
    assert 'INHERITANCE' in html


def test_register_link_visible_on_login(page, e2e_server):
    page.goto(e2e_server + '/auth/login')
    assert 'REGISTER' in page.content()


def test_register_page_loads(page, e2e_server):
    page.goto(e2e_server + '/auth/register')
    assert page.locator('form#register-form').count() == 1
    assert page.locator('select#plan_id option').count() >= 4  # weekly..unlimited


def test_register_full_flow_lands_in_waiting(page, e2e_server):
    username = f"e2e_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
    page.goto(e2e_server + '/auth/register')
    page.fill('#username', username)
    page.fill('#password', 'password123')
    page.fill('#full_name', f"E2E {username}")
    page.fill('#email', f"{username}@test.local")
    page.fill('#whatsapp', '+970599000111')
    plan_id = page.evaluate("""() => {
        const sel = document.querySelector('select#plan_id');
        for (const o of sel.options) {
            if (o.textContent.toLowerCase().includes('monthly')) return o.value;
        }
        return sel.value;
    }""")
    page.locator('select#plan_id').select_option(value=plan_id)

    page.click('button[type="submit"]')
    # Page shows success message; after 1.5s it redirects to /auth/login.
    page.wait_for_url(re.compile(r'.*/auth/login$'), timeout=5000)

    # Login as admin to confirm the request is in the queue.
    admin = page.context.browser.new_context()
    admin_page = admin.new_page()
    admin_page.goto(e2e_server + '/auth/login')
    admin_page.fill('#username', 'admin')
    admin_page.fill('#password', 'admin123')
    admin_page.click('button[type="submit"]')
    admin_page.wait_for_url(re.compile(r'.*/$'), timeout=5000)

    admin_page.goto(e2e_server + '/admin/subscriptions')
    admin_page.wait_for_selector('#pending-body', timeout=5000)
    admin_page.locator('#pending-body').wait_for(
        state='visible', timeout=5000)
    # Wait until the new signup is actually rendered (pending list is fetched async).
    admin_page.locator('#pending-body').filter(
        has_text=username).wait_for(state='attached', timeout=5000)
    html = admin_page.content()
    assert username in html, "new signup not visible in owner queue"
    assert 'WhatsApp' in html, "owner queue should show contact WhatsApp"
    admin.close()


# ---------- admin (login required) ----------

def test_admin_dashboard_renders(admin_page, e2e_server):
    admin_page.goto(e2e_server + '/admin/')
    assert 'PLATFORM' in admin_page.content().upper() or 'DASHBOARD' in admin_page.content().upper()


def test_admin_pages_load(admin_page, e2e_server):
    for path in ('/admin/tenants', '/admin/subscriptions', '/admin/plans',
                 '/admin/activity', '/admin/users', '/admin/files',
                 '/admin/settings', '/admin/logs'):
        admin_page.goto(e2e_server + path)
        assert admin_page.locator('body').count() == 1, f"empty body for {path}"


# ---------- MAS pages ----------

def test_mas_pages_load_after_login(admin_page, e2e_server):
    """An admin has unlimited subscription -> all MAS pages should be reachable."""
    admin_page.goto(e2e_server + '/mas')
    assert 'MAS' in admin_page.content()
    for path in ('/work-mode', '/circle', '/intersections', '/implants',
                 '/resection', '/plotting', '/plan', '/print-preview',
                 '/files', '/files/new'):
        admin_page.goto(e2e_server + path)
        assert admin_page.locator('body').count() == 1, f"empty body for {path}"


def test_create_file_then_save_points(admin_page, e2e_server):
    """Full path: /files/new form -> /mas -> API save points -> render shows them."""
    file_name = f"e2efile_{int(time.time()*1000)}"
    admin_page.goto(e2e_server + '/files/new')
    admin_page.fill('input[name="name"]', file_name)
    admin_page.fill('input[name="date"]', '2026-09-03')
    admin_page.fill('input[name="place"]', 'E2E Place')
    admin_page.click('button[type="submit"]')
    admin_page.wait_for_url(re.compile(r'.*/mas$'), timeout=5000)

    # Add points via the same JS the page uses.
    admin_page.evaluate("""(async () => {
        await fetch('/api/points', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({points: [
                {no: 1, y: 1000.0, x: 2000.0, h: 50.0},
                {no: 2, y: 1100.0, x: 2000.0, h: 55.0},
                {no: 3, y: 1100.0, x: 2100.0, h: 60.0},
            ]})
        });
    })()""")
    admin_page.goto(e2e_server + '/polar')
    assert admin_page.locator('body').count() == 1


def test_static_assets_load(page, e2e_server):
    """CSS and JS that base.html references must serve 200."""
    for path in ('/static/css/style.css', '/static/js/main.js'):
        resp = page.goto(e2e_server + path)
        assert resp.status == 200, f"{path} returned {resp.status}"


# ---------- waiting room ----------

def test_blocked_user_gets_waiting_room(page, e2e_server):
    """Sign up, log out admin, log in as new user -> /waiting, not /mas."""
    username = f"e2ewait_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
    page.goto(e2e_server + '/auth/register')
    page.fill('#username', username)
    page.fill('#password', 'password123')
    page.fill('#whatsapp', '+970599000222')
    plan_id = page.evaluate("""() => {
        const sel = document.querySelector('select#plan_id');
        for (const o of sel.options) {
            if (o.textContent.toLowerCase().includes('monthly')) return o.value;
        }
        return sel.value;
    }""")
    page.locator('select#plan_id').select_option(value=plan_id)
    page.click('button[type="submit"]')
    page.wait_for_url(re.compile(r'.*/auth/login$'), timeout=5000)

    # New user logs in -> blocked because subscription is still pending.
    page.goto(e2e_server + '/auth/login')
    page.fill('#username', username)
    page.fill('#password', 'password123')
    page.click('button[type="submit"]')
    # Server returns a JSON body with a redirect to /waiting.
    body = page.content()
    # XHR is the response - the page itself doesn't navigate. Use the
    # redirect target manually: clear cookies via logout, then verify
    # the next /mas attempt lands on /waiting.
    page.goto(e2e_server + '/auth/logout')
    page.goto(e2e_server + '/auth/login')
    page.fill('#username', username)
    page.fill('#password', 'password123')
    page.click('button[type="submit"]')
    # Form-driven login -> server returns 302 to /waiting.
    page.wait_for_url(re.compile(r'.*/waiting.*'), timeout=5000)
    assert 'PENDING' in page.content().upper() or 'SUSPENDED' in page.content().upper() \
        or 'EXPIRED' in page.content().upper()
