import os
import requests

from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright


WIB = timezone(
    timedelta(hours=7)
)


# ============================================================
# HEALTH BAR
# ============================================================

def inject_health_bar(
    page,
    http_status,
    dashboard_ready,
    failed_requests,
    failed_api_requests,
    status=None,
    message=None,
):

    if status is None:

        is_healthy = (
            http_status == 200
            and dashboard_ready
            and failed_requests == 0
            and len(failed_api_requests) == 0
        )

        if is_healthy:

            status = "HEALTHY"
            message = "Dashboard operating normally"
            status_background = "#087f46"

        else:

            status = "CHECK"
            message = "Dashboard requires attention"
            status_background = "#9f1239"

    else:

        status_background = "#9f1239"

    checked_at = datetime.now(
        WIB
    ).strftime(
        "%d %b %Y %H:%M WIB"
    )

    page.evaluate(
        """
        ({
            status,
            message,
            httpStatus,
            dashboardReady,
            failedRequests,
            failedApiRequests,
            checkedAt,
            statusBackground
        }) => {

            const existing =
                document.getElementById(
                    'automation-dashboard-health'
                );

            if (existing) {
                existing.remove();
            }

            const container =
                document.createElement('div');

            container.id =
                'automation-dashboard-health';

            const box =
                document.createElement('div');

            box.style.cssText = `
                position: fixed;
                left: 0;
                right: 0;
                bottom: 0;
                min-height: 42px;
                display: flex;
                align-items: center;
                background: rgba(9, 15, 28, 0.96);
                border-top: 2px solid ${statusBackground};
                box-shadow:
                    0 -4px 12px rgba(0, 0, 0, 0.25);
                z-index: 2147483647;
                font-family:
                    Arial,
                    Helvetica,
                    sans-serif;
                color: #ffffff;
                padding: 0 16px;
                box-sizing: border-box;
                gap: 14px;
                font-size: 12px;
                overflow: hidden;
            `;


            // ====================================================
            // STATUS
            // ====================================================

            const statusElement =
                document.createElement('div');

            statusElement.style.cssText = `
                height: 42px;
                display: flex;
                align-items: center;
                padding: 0 16px;
                margin-left: -16px;
                background: ${statusBackground};
                color: #ffffff;
                font-weight: 700;
                letter-spacing: 0.5px;
                white-space: nowrap;
                flex-shrink: 0;
            `;

            statusElement.textContent =
                status;


            // ====================================================
            // MESSAGE
            // ====================================================

            const messageElement =
                document.createElement('div');

            messageElement.style.cssText = `
                font-weight: 600;
                white-space: nowrap;
                flex-shrink: 0;
            `;

            messageElement.textContent =
                message;


            // ====================================================
            // HTTP STATUS
            // ====================================================

            const httpElement =
                document.createElement('div');

            httpElement.style.cssText = `
                white-space: nowrap;
                opacity: 0.9;
                flex-shrink: 0;
            `;

            httpElement.textContent =
                `HTTP ${httpStatus}`;


            // ====================================================
            // DASHBOARD READY
            // ====================================================

            const renderElement =
                document.createElement('div');

            renderElement.style.cssText = `
                white-space: nowrap;
                opacity: 0.9;
                flex-shrink: 0;
            `;

            renderElement.textContent =
                dashboardReady
                    ? 'View ready'
                    : 'View not ready';


            // ====================================================
            // FAILED REQUESTS
            // ====================================================

            const requestElement =
                document.createElement('div');

            requestElement.style.cssText = `
                white-space: nowrap;
                opacity: 0.9;
                flex-shrink: 0;
            `;

            requestElement.textContent =
                failedRequests === 0
                    ? 'Connection stable'
                    : `${failedRequests} failed requests`;


            // ====================================================
            // API STATUS
            // ====================================================

            const apiElement =
                document.createElement('div');

            apiElement.style.cssText = `
                white-space: nowrap;
                opacity: 0.95;
                overflow: hidden;
                text-overflow: ellipsis;
                min-width: 0;
                flex: 1;
            `;


            if (failedApiRequests.length === 0) {

                apiElement.textContent =
                    'API stable';

            } else {

                apiElement.textContent =
                    'API: ' +
                    failedApiRequests.join(' | ');

                apiElement.title =
                    failedApiRequests.join('\\n');
            }


            // ====================================================
            // CHECKED TIME
            // ====================================================

            const timeElement =
                document.createElement('div');

            timeElement.style.cssText = `
                margin-left: auto;
                white-space: nowrap;
                opacity: 0.8;
                flex-shrink: 0;
            `;

            timeElement.textContent =
                `Checked ${checkedAt}`;


            // ====================================================
            // APPEND
            // ====================================================

            box.appendChild(
                statusElement
            );

            box.appendChild(
                messageElement
            );

            box.appendChild(
                httpElement
            );

            box.appendChild(
                renderElement
            );

            box.appendChild(
                requestElement
            );

            box.appendChild(
                apiElement
            );

            box.appendChild(
                timeElement
            );

            container.appendChild(
                box
            );

            document.body.appendChild(
                container
            );
        }
        """,
        {
            "status": status,
            "message": message,
            "httpStatus": http_status,
            "dashboardReady": dashboard_ready,
            "failedRequests": failed_requests,
            "failedApiRequests": failed_api_requests,
            "checkedAt": checked_at,
            "statusBackground": status_background,
        }
    )

    return {
        "status": status,
        "message": message,
        "checked_at": checked_at,
    }


# ============================================================
# DISCORD
# ============================================================

def send_discord(
    webhook_url,
    page_name,
    screenshot_path,
    status,
    checked_at,
    message,
):

    with open(
        screenshot_path,
        "rb",
    ) as image:

        response = requests.post(
            webhook_url,

            data={
                "content": (
                    f"📊 **{page_name}**\n"
                    f"Status: **{status}**\n"
                    f"{message}\n"
                    f"Checked: {checked_at}"
                )
            },

            files={
                "file": (
                    os.path.basename(
                        screenshot_path
                    ),
                    image,
                    "image/png",
                )
            },

            timeout=120,
        )

    if response.status_code not in (
        200,
        204,
    ):

        raise Exception(
            f"Discord error: "
            f"{response.status_code} "
            f"{response.text}"
        )


# ============================================================
# OFFLINE SCREENSHOT
# ============================================================

def create_offline_screenshot(
    page,
    page_name,
    error_message,
    screenshot_path,
):

    checked_at = datetime.now(
        WIB
    ).strftime(
        "%d %b %Y %H:%M WIB"
    )

    html = f"""
    <!DOCTYPE html>

    <html>

    <head>
        <meta charset="UTF-8">
        <title>Dashboard Offline</title>
    </head>

    <body style="
        margin: 0;
        width: 100vw;
        height: 100vh;

        background: #0b1220;
        color: white;

        font-family:
            Arial,
            Helvetica,
            sans-serif;

        display: flex;
        align-items: center;
        justify-content: center;
    ">

        <div style="
            width: 80%;
            max-width: 900px;

            padding: 36px;

            box-sizing: border-box;

            border: 2px solid #9f1239;
            border-radius: 12px;

            background: #111827;
        ">

            <div style="
                color: #f87171;
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 16px;
            ">
                OFFLINE
            </div>

            <div style="
                font-size: 28px;
                font-weight: 700;
                margin-bottom: 12px;
            ">
                {page_name}
            </div>

            <div style="
                color: #d1d5db;
                font-size: 18px;
                margin-bottom: 24px;
            ">
                Dashboard is unreachable,
                please check VPN or Dashboard
            </div>

            <div style="
                background: #1f2937;
                border-radius: 8px;

                padding: 16px;

                color: #fca5a5;

                font-family: monospace;
                font-size: 14px;

                word-break: break-word;
            ">
                {error_message}
            </div>

            <div style="
                margin-top: 24px;
                color: #9ca3af;
                font-size: 14px;
            ">
                Checked {checked_at}
            </div>

        </div>

    </body>

    </html>
    """

    page.set_content(
        html,
        wait_until="commit",
        timeout=10000
    )

    page.wait_for_timeout(
        500
    )

    page.screenshot(
        path=screenshot_path,
        full_page=False
    )

    return checked_at


# ============================================================
# RUN PAGE
# ============================================================

def run_page(
    page_name,
    url,
    wait_after_load=5000,
    before_screenshot=None,
    persistent_session_dir=None,
):

    load_dotenv()

    webhook_url = os.getenv(
        "DISCORD_WEBHOOK_URL"
    )

    width = int(
        os.getenv(
            "SCREENSHOT_WIDTH",
            "1365"
        )
    )

    height = int(
        os.getenv(
            "SCREENSHOT_HEIGHT",
            "768"
        )
    )

    if not webhook_url:

        raise ValueError(
            "DISCORD_WEBHOOK_URL belum ditemukan di .env"
        )


    # ========================================================
    # PLAYWRIGHT
    # ========================================================

    with sync_playwright() as playwright:

        browser = None
        context = None
        page = None


        # ====================================================
        # CREATE BROWSER CONTEXT
        # ====================================================

        if persistent_session_dir:

            print(
                f"[{page_name}] "
                f"Using persistent session: "
                f"{persistent_session_dir}"
            )

            os.makedirs(
                persistent_session_dir,
                exist_ok=True
            )

            context = (
                playwright.chromium
                .launch_persistent_context(
                    user_data_dir=persistent_session_dir,

                    headless=True,

                    viewport={
                        "width": width,
                        "height": height,
                    },

                    ignore_https_errors=True,
                )
            )

            if context.pages:

                page = context.pages[0]

            else:

                page = context.new_page()

        else:

            print(
                f"[{page_name}] "
                f"Using temporary browser session"
            )

            browser = playwright.chromium.launch(
                headless=True
            )

            context = browser.new_context(
                viewport={
                    "width": width,
                    "height": height,
                },

                ignore_https_errors=True,
            )

            page = context.new_page()


        # ====================================================
        # FAILED REQUEST TRACKING
        # ====================================================

        failed_requests = []

        failed_api_requests = []


        # ====================================================
        # NETWORK REQUEST FAILED
        # ====================================================

        page.on(
            "requestfailed",
            lambda request: failed_requests.append(
                request.url
            )
        )


        # ====================================================
        # API RESPONSE TRACKING
        # ====================================================

        def handle_api_response(response):

            try:

                request = response.request

                resource_type = (
                    request.resource_type
                )

                # Only monitor API-style requests.
                #
                # XHR:
                #   XMLHttpRequest
                #
                # FETCH:
                #   fetch()
                #
                if resource_type in (
                    "xhr",
                    "fetch",
                ):

                    status_code = (
                        response.status
                    )

                    if status_code != 200:

                        api_error = (
                            f"{response.url} "
                            f"[{status_code}]"
                        )

                        failed_api_requests.append(
                            api_error
                        )

                        print(
                            f"[{page_name}] "
                            f"API ERROR: "
                            f"{api_error}"
                        )

            except Exception as error:

                print(
                    f"[{page_name}] "
                    f"API tracking error: "
                    f"{error}"
                )


        page.on(
            "response",
            handle_api_response
        )


        screenshot_path = (
            f"{page_name}.png"
        )


        # ====================================================
        # MAIN TRY
        # ====================================================

        try:

            # =================================================
            # OPEN PAGE
            # =================================================

            print(
                f"[{page_name}] "
                f"Opening {url}"
            )

            try:

                response = page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=120000,
                )

                http_status = (
                    response.status
                    if response
                    else 0
                )

                print(
                    f"[{page_name}] "
                    f"HTTP status: {http_status}"
                )

            except Exception as error:

                print(
                    f"[{page_name}] "
                    f"Connection failed: {error}"
                )

                error_message = str(
                    error
                )


                # =============================================
                # RESET PAGE
                # =============================================

                try:

                    page.goto(
                        "about:blank",
                        wait_until="commit",
                        timeout=10000
                    )

                except Exception:

                    pass


                # =============================================
                # OFFLINE SCREENSHOT
                # =============================================

                checked_at = create_offline_screenshot(
                    page=page,
                    page_name=page_name,
                    error_message=error_message,
                    screenshot_path=screenshot_path,
                )


                # =============================================
                # DISCORD
                # =============================================

                send_discord(
                    webhook_url=webhook_url,
                    page_name=page_name,
                    screenshot_path=screenshot_path,
                    status="OFFLINE",
                    checked_at=checked_at,
                    message="Dashboard is unreachable",
                )

                print(
                    f"[{page_name}] "
                    f"Offline report sent to Discord"
                )

                return


            # =================================================
            # WAIT
            # =================================================

            print(
                f"[{page_name}] "
                f"Waiting "
                f"{wait_after_load / 1000:.0f} seconds..."
            )

            page.wait_for_timeout(
                wait_after_load
            )


            # =================================================
            # CUSTOM PAGE ACTION
            # =================================================

            if before_screenshot:

                print(
                    f"[{page_name}] "
                    f"Running custom page action..."
                )

                before_screenshot(
                    page
                )


            # =================================================
            # DASHBOARD CHECK
            # =================================================

            body_text = page.locator(
                "body"
            ).inner_text(
                timeout=30000
            ).strip()

            dashboard_ready = (
                len(body_text) > 100
            )


            # =================================================
            # REMOVE DUPLICATE API ERRORS
            # =================================================

            failed_api_requests = list(
                dict.fromkeys(
                    failed_api_requests
                )
            )


            # =================================================
            # HEALTH BAR
            # =================================================

            health = inject_health_bar(
                page=page,
                http_status=http_status,
                dashboard_ready=dashboard_ready,
                failed_requests=len(
                    failed_requests
                ),
                failed_api_requests=(
                    failed_api_requests
                ),
            )


            # =================================================
            # RESET SCROLL
            # =================================================

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
                1000
            )


            # =================================================
            # SCREENSHOT
            # =================================================

            page.screenshot(
                path=screenshot_path,
                full_page=False,
            )

            print(
                f"[{page_name}] "
                f"Screenshot created"
            )


            # =================================================
            # DISCORD
            # =================================================

            send_discord(
                webhook_url=webhook_url,
                page_name=page_name,
                screenshot_path=screenshot_path,
                status=health["status"],
                checked_at=health["checked_at"],
                message=health["message"],
            )

            print(
                f"[{page_name}] "
                f"Screenshot sent to Discord"
            )


        # =====================================================
        # GLOBAL ERROR HANDLER
        # =====================================================

        except Exception as error:

            print(
                f"[{page_name}] "
                f"ERROR: {error}"
            )

            error_message = str(
                error
            )


            # =================================================
            # TRY CREATE ERROR SCREENSHOT
            # =================================================

            try:

                checked_at = create_offline_screenshot(
                    page=page,
                    page_name=page_name,
                    error_message=error_message,
                    screenshot_path=screenshot_path,
                )


                # =============================================
                # SEND ERROR TO DISCORD
                # =============================================

                send_discord(
                    webhook_url=webhook_url,
                    page_name=page_name,
                    screenshot_path=screenshot_path,
                    status="ERROR",
                    checked_at=checked_at,
                    message=error_message,
                )

                print(
                    f"[{page_name}] "
                    f"Error report sent to Discord"
                )

            except Exception as discord_error:

                print(
                    f"[{page_name}] "
                    f"Failed to send error report: "
                    f"{discord_error}"
                )

            raise

        # CLEANUP

        finally:

            if os.path.exists(
                screenshot_path
            ):

                os.remove(
                    screenshot_path
                )


            if context:

                context.close()

                print(
                    f"[{page_name}] "
                    f"Browser context closed"
                )