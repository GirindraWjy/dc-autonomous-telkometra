import os

from dotenv import load_dotenv

from core.ss_template import run_page


# ============================================================
# CONFIG
# ============================================================

PAGE_NAME = "uptime-kuma"

LOGIN_URL = "http://192.168.120.14:3001/dashboard"
DASHBOARD_URL = "http://192.168.120.14:3001/dashboard"


# ============================================================
# LOGIN + DASHBOARD ACTION
# ============================================================

def login_uptime_kuma(page):

    load_dotenv()

    username = os.getenv(
        "UPTIME_KUMA_USERNAME"
    )

    password = os.getenv(
        "UPTIME_KUMA_PASSWORD"
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    if not username:
        raise ValueError(
            "UPTIME_KUMA_USERNAME belum ditemukan di .env"
        )

    if not password:
        raise ValueError(
            "UPTIME_KUMA_PASSWORD belum ditemukan di .env"
        )

    # ========================================================
    # OPEN LOGIN PAGE
    # ========================================================

    print(
        f"[{PAGE_NAME}] Opening login page"
    )

    page.goto(
        LOGIN_URL,
        wait_until="domcontentloaded",
        timeout=120000
    )

    print(
        f"[{PAGE_NAME}] Current URL: {page.url}"
    )

    # ========================================================
    # WAIT PAGE LOAD
    # ========================================================

    print(
        f"[{PAGE_NAME}] Waiting page load..."
    )

    try:

        page.wait_for_load_state(
            "networkidle",
            timeout=60000
        )

    except Exception:

        print(
            f"[{PAGE_NAME}] "
            f"networkidle timeout, continuing..."
        )

    # Berikan Vue waktu render
    page.wait_for_timeout(
        5000
    )

    # ========================================================
    # DEBUG DOM
    # ========================================================

    print(
        f"[{PAGE_NAME}] "
        f"Checking login DOM..."
    )

    print(
        f"[{PAGE_NAME}] "
        f"Input count: "
        f"{page.locator('input').count()}"
    )

    print(
        f"[{PAGE_NAME}] "
        f"Button count: "
        f"{page.locator('button').count()}"
    )

    # ========================================================
    # USERNAME
    # ========================================================

    print(
        f"[{PAGE_NAME}] "
        f"Waiting #floatingInput..."
    )

    username_input = page.locator(
        "#floatingInput"
    )

    try:

        username_input.wait_for(
            state="attached",
            timeout=60000
        )

        print(
            f"[{PAGE_NAME}] "
            f"#floatingInput detected"
        )

    except Exception:

        debug_path = (
            f"{PAGE_NAME}-login-debug.png"
        )

        page.screenshot(
            path=debug_path,
            full_page=True
        )

        print(
            f"[{PAGE_NAME}] "
            f"DEBUG screenshot: "
            f"{debug_path}"
        )

        try:

            html = page.content()

            print(
                "\n========== HTML DEBUG ==========\n"
            )

            print(
                html[:10000]
            )

            print(
                "\n================================\n"
            )

        except Exception:
            pass

        raise Exception(
            "#floatingInput tidak ditemukan "
            "setelah 60 detik."
        )

    # ========================================================
    # USERNAME VISIBLE
    # ========================================================

    print(
        f"[{PAGE_NAME}] "
        f"Waiting username visible..."
    )

    username_input.wait_for(
        state="visible",
        timeout=30000
    )

    # ========================================================
    # FILL USERNAME
    # ========================================================

    print(
        f"[{PAGE_NAME}] "
        f"Filling username"
    )

    username_input.fill(
        username
    )

    # ========================================================
    # PASSWORD
    # ========================================================

    print(
        f"[{PAGE_NAME}] "
        f"Waiting #floatingPassword..."
    )

    password_input = page.locator(
        "#floatingPassword"
    )

    password_input.wait_for(
        state="attached",
        timeout=30000
    )

    password_input.wait_for(
        state="visible",
        timeout=30000
    )

    print(
        f"[{PAGE_NAME}] "
        f"Filling password"
    )

    password_input.fill(
        password
    )

    # ========================================================
    # LOGIN BUTTON
    # ========================================================

    print(
        f"[{PAGE_NAME}] "
        f"Finding login button..."
    )

    login_button = page.locator(
        'button[type="submit"]'
    ).first

    login_button.wait_for(
        state="attached",
        timeout=30000
    )

    login_button.wait_for(
        state="visible",
        timeout=30000
    )

    print(
        f"[{PAGE_NAME}] "
        f"Clicking login"
    )

    login_button.click()

    # ========================================================
    # WAIT AUTHENTICATION
    # ========================================================

    print(
        f"[{PAGE_NAME}] "
        f"Waiting authentication..."
    )

    page.wait_for_timeout(
        5000
    )

    try:

        page.wait_for_load_state(
            "networkidle",
            timeout=30000
        )

    except Exception:

        pass

    print(
        f"[{PAGE_NAME}] "
        f"After login URL: {page.url}"
    )

    # ========================================================
    # CHECK LOGIN
    # ========================================================

    if "/login" in page.url:

        print(
            f"[{PAGE_NAME}] "
            f"Still login page, waiting..."
        )

        page.wait_for_timeout(
            5000
        )

    if "/login" in page.url:

        debug_path = (
            f"{PAGE_NAME}-login-failed.png"
        )

        page.screenshot(
            path=debug_path,
            full_page=True
        )

        raise Exception(
            "Login gagal. "
            "Uptime Kuma masih berada di /login."
        )

    print(
        f"[{PAGE_NAME}] "
        f"Login successful"
    )

    # ========================================================
    # OPEN DASHBOARD
    # ========================================================

    print(
        f"[{PAGE_NAME}] "
        f"Opening dashboard"
    )

    page.goto(
        DASHBOARD_URL,
        wait_until="domcontentloaded",
        timeout=120000
    )

    # ========================================================
    # WAIT DASHBOARD
    # ========================================================

    print(
        f"[{PAGE_NAME}] "
        f"Waiting dashboard render..."
    )

    try:

        page.wait_for_load_state(
            "networkidle",
            timeout=60000
        )

    except Exception:

        pass

    page.wait_for_timeout(
        10000
    )

    print(
        f"[{PAGE_NAME}] "
        f"Dashboard URL: {page.url}"
    )

    # ========================================================
    # CHECK SESSION
    # ========================================================

    if "/login" in page.url:

        raise Exception(
            "Session login tidak bertahan. "
            "Dashboard kembali ke /login."
        )

    print(
        f"[{PAGE_NAME}] "
        f"Dashboard ready"
    )


# ============================================================
# RUN
# ============================================================

def run():

    run_page(
        page_name=PAGE_NAME,
        url=LOGIN_URL,
        wait_after_load=0,
        before_screenshot=login_uptime_kuma
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run()