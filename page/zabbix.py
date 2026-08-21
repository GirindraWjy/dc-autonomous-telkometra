import os

from dotenv import load_dotenv

from core.ss_template import run_page


# ============================================================
# CONFIGURATION
# ============================================================

PAGE_NAME = "zabbix"

BASE_URL = "http://192.168.120.14/zabbix"

LOGIN_URL = (
    f"{BASE_URL}/index.php"
)

DASHBOARD_URL = (
    f"{BASE_URL}/zabbix.php"
    "?action=dashboard.view"
    "&dashboardid=354"
    "&kiosk=1"
)

SESSION_DIR = os.path.join(
    "browser_data",
    "zabbix"
)


# ============================================================
# ZABBIX LOGIN + DASHBOARD
# ============================================================

def zabbix_action(page):

    load_dotenv()

    username = os.getenv(
        "ZABBIX_USERNAME"
    )

    password = os.getenv(
        "ZABBIX_PASSWORD"
    )

    if not username:
        raise ValueError(
            "ZABBIX_USERNAME belum ditemukan di .env"
        )

    if not password:
        raise ValueError(
            "ZABBIX_PASSWORD belum ditemukan di .env"
        )

    # ========================================================
    # CHECK CURRENT SESSION
    # ========================================================

    print(
        f"[{PAGE_NAME}] "
        f"Checking existing Zabbix session..."
    )

    login_form = page.locator(
        'input[name="name"]'
    )

    not_logged_in = page.get_by_text(
        "You are not logged in",
        exact=False
    )

    is_login_required = (
        login_form.count() > 0
        or not_logged_in.count() > 0
    )

    # ========================================================
    # LOGIN IF REQUIRED
    # ========================================================

    if is_login_required:

        print(
            f"[{PAGE_NAME}] "
            f"Existing session is not valid."
        )

        print(
            f"[{PAGE_NAME}] "
            f"Opening login page..."
        )

        page.goto(
            LOGIN_URL,
            wait_until="domcontentloaded",
            timeout=120000
        )

        print(
            f"[{PAGE_NAME}] "
            f"Login page opened"
        )

        print(
            f"[{PAGE_NAME}] "
            f"Current URL: {page.url}"
        )

        # ====================================================
        # WAIT LOGIN FORM
        # ====================================================

        page.wait_for_selector(
            'input[name="name"]',
            timeout=30000
        )

        # ====================================================
        # USERNAME
        # ====================================================

        print(
            f"[{PAGE_NAME}] "
            f"Filling username..."
        )

        page.fill(
            'input[name="name"]',
            username
        )

        # ====================================================
        # PASSWORD
        # ====================================================

        print(
            f"[{PAGE_NAME}] "
            f"Filling password..."
        )

        page.fill(
            'input[name="password"]',
            password
        )

        # ====================================================
        # SUBMIT
        # ====================================================

        print(
            f"[{PAGE_NAME}] "
            f"Submitting login..."
        )

        page.click(
            'button[type="submit"]'
        )

        # ====================================================
        # WAIT LOGIN
        # ====================================================

        try:

            page.wait_for_load_state(
                "domcontentloaded",
                timeout=120000
            )

        except Exception:

            print(
                f"[{PAGE_NAME}] "
                f"Login load-state timeout, continuing..."
            )

        page.wait_for_timeout(
            3000
        )

        print(
            f"[{PAGE_NAME}] "
            f"Login response received"
        )

        print(
            f"[{PAGE_NAME}] "
            f"Current URL: {page.url}"
        )

        # ====================================================
        # VERIFY LOGIN
        # ====================================================

        login_form_after = page.locator(
            'input[name="name"]'
        )

        not_logged_in_after = page.get_by_text(
            "You are not logged in",
            exact=False
        )

        if (
            login_form_after.count() > 0
            or not_logged_in_after.count() > 0
        ):

            raise Exception(
                "Login Zabbix gagal. "
                "Session tidak berhasil dibuat."
            )

        print(
            f"[{PAGE_NAME}] "
            f"Login successful"
        )

    else:

        print(
            f"[{PAGE_NAME}] "
            f"Existing Zabbix session is valid."
        )

        print(
            f"[{PAGE_NAME}] "
            f"Login skipped."
        )

    # ========================================================
    # OPEN DASHBOARD
    # ========================================================

    print(
        f"[{PAGE_NAME}] "
        f"Opening Zabbix dashboard..."
    )

    page.goto(
        DASHBOARD_URL,
        wait_until="domcontentloaded",
        timeout=120000
    )

    print(
        f"[{PAGE_NAME}] "
        f"Dashboard opened"
    )

    print(
        f"[{PAGE_NAME}] "
        f"Current URL: {page.url}"
    )

    # ========================================================
    # WAIT DASHBOARD
    # ========================================================

    print(
        f"[{PAGE_NAME}] "
        f"Waiting for dashboard..."
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

    page.wait_for_timeout(
        10000
    )

    # ========================================================
    # VERIFY LOGIN
    # ========================================================

    print(
        f"[{PAGE_NAME}] "
        f"Verifying login..."
    )

    still_not_logged_in = page.get_by_text(
        "You are not logged in",
        exact=False
    )

    if still_not_logged_in.count() > 0:

        raise Exception(
            "Zabbix masih menampilkan "
            "'You are not logged in'. "
            "Session tidak valid."
        )

    if "/index.php" in page.url:

        raise Exception(
            "Zabbix kembali ke halaman login."
        )

    print(
        f"[{PAGE_NAME}] "
        f"Login verified"
    )

    # ========================================================
    # RESET SCROLL
    # ========================================================

    page.evaluate(
        """
        () => {
            window.scrollTo(0, 0);
            document.documentElement.scrollTop = 0;
            document.body.scrollTop = 0;
        }
        """
    )

    page.wait_for_timeout(
        2000
    )

    print(
        f"[{PAGE_NAME}] "
        f"Dashboard ready for screenshot"
    )


# ============================================================
# RUN
# ============================================================

def run():

    run_page(
        page_name=PAGE_NAME,
        url=DASHBOARD_URL,
        wait_after_load=0,
        before_screenshot=zabbix_action,
        persistent_session_dir=SESSION_DIR,
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run()