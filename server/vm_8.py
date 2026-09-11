import os
import re
import requests
import paramiko

from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

from rc_analyst.infra_rc_analyst import (
    analyze,
    format_diagnostics,
)

from core.server_ss_template import render_terminal


PAGE_NAME = "Server 8"

HOST = "192.168.120.8"

CURRENT_DIRECTORY = (
    "ulo_commercial/"
    "be-dashboard-cp-platform-backup/"
    "logs"
)

COMMANDS = [
    "cd ulo_commercial/be-dashboard-cp-platform-backup/logs/",
    'journalctl -u daemon_clean_database.service --since "2 hours ago" --no-pager | grep "trx_id" | tail -n 10',
    "ls -lah",
    "df -h",
    "netstat -tnlp",
    "ps ax | grep clean",
    "date",
]

WIB = timezone(
    timedelta(hours=7)
)


def get_last_transaction(ssh):
    _, stdout, _ = ssh.exec_command(
        'journalctl -u daemon_clean_database.service '
        '--since "24 hours ago" '
        '--no-pager '
        '| grep "trx_id" '
        '| tail -n 1'
    )

    output = (
        stdout
        .read()
        .decode(
            "utf-8",
            errors="replace",
        )
        .strip()
    )

    if not output:
        return None

    match = re.search(
        r"^[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}",
        output,
    )

    if not match:
        return None

    timestamp = datetime.strptime(
        match.group(0),
        "%b %d %H:%M:%S",
    ).replace(
        year=datetime.now(WIB).year,
        tzinfo=WIB,
    )

    return timestamp


def get_cpu_usage(ssh):
    _, stdout, _ = ssh.exec_command(
        "top -bn1 | grep 'Cpu(s)'"
    )

    output = (
        stdout
        .read()
        .decode(
            "utf-8",
            errors="replace",
        )
    )

    match = re.search(
        r"([\d.,]+)\s*id",
        output,
    )

    if not match:
        return None

    idle = float(
        match.group(1).replace(
            ",",
            ".",
        )
    )

    return round(
        100 - idle,
        1,
    )


def get_ram_usage(ssh):
    _, stdout, _ = ssh.exec_command(
        'free | awk \'/Mem:/ '
        '{printf "%.1f", ($3/$2)*100}\''
    )

    output = (
        stdout
        .read()
        .decode(
            "utf-8",
            errors="replace",
        )
        .strip()
    )

    try:
        return float(output)
    except ValueError:
        return None


def get_disk_usage(ssh):
    _, stdout, _ = ssh.exec_command(
        "df -P / | "
        "awk 'NR==2 "
        "{gsub(/%/,\"\",$5); print $5}'"
    )

    output = (
        stdout
        .read()
        .decode(
            "utf-8",
            errors="replace",
        )
        .strip()
    )

    try:
        return float(output)
    except ValueError:
        return None


def format_usage(label, value):
    if value is None:
        return f"{label}: UNKNOWN"

    return f"{label}: {value:.1f}%"


def run():
    load_dotenv()

    username = os.getenv(
        "USN_SERVER_8"
    )

    password = os.getenv(
        "PW_SERVER_8"
    )

    webhook_url = os.getenv(
        "INFRA_DISCORD_WEBHOOK_URL"
    )

    if not username:
        raise ValueError(
            "USN_SERVER_8 belum ditemukan di .env"
        )

    if not password:
        raise ValueError(
            "PW_SERVER_8 belum ditemukan di .env"
        )

    if not webhook_url:
        raise ValueError(
            "INFRA_DISCORD_WEBHOOK_URL belum ditemukan di .env"
        )

    screenshot_path = "server8.png"

    ssh = paramiko.SSHClient()

    ssh.set_missing_host_key_policy(
        paramiko.AutoAddPolicy()
    )

    output_sections = []
    command_results = []
    journal_output = ""

    try:
        print(
            f"[{PAGE_NAME}] Connecting to {HOST}..."
        )

        ssh.connect(
            hostname=HOST,
            username=username,
            password=password,
            timeout=15,
        )

        print(
            f"[{PAGE_NAME}] Connected"
        )

        for index, command in enumerate(
            COMMANDS,
            start=1,
        ):
            print(
                f"[{PAGE_NAME}] Running command {index}: {command}"
            )

            if command.startswith("cd "):
                full_command = (
                    f"cd {command[3:]} && pwd"
                )
            else:
                full_command = (
                    f"cd {CURRENT_DIRECTORY} && {command}"
                )

            stdin, stdout, stderr = ssh.exec_command(
                full_command,
                timeout=60,
            )

            stdout_text = (
                stdout
                .read()
                .decode(
                    "utf-8",
                    errors="replace",
                )
            )

            stderr_text = (
                stderr
                .read()
                .decode(
                    "utf-8",
                    errors="replace",
                )
            )

            exit_code = (
                stdout.channel.recv_exit_status()
            )

            command_results.append(
                {
                    "command": command,
                    "exit_code": exit_code,
                    "stderr": stderr_text,
                }
            )

            if "journalctl" in command:
                journal_output = stdout_text

            output_sections.append(
                f"$ {command}"
            )

            if stdout_text.strip():
                output_sections.append(
                    stdout_text.rstrip()
                )

            if stderr_text.strip():
                output_sections.append(
                    "[stderr]"
                )
                output_sections.append(
                    stderr_text.rstrip()
                )

            output_sections.append(
                f"[exit code: {exit_code}]"
            )

            output_sections.append("")

            print(
                f"[{PAGE_NAME}] Command {index} completed "
                f"(exit code: {exit_code})"
            )

        print(
            f"[{PAGE_NAME}] Checking server resources..."
        )

        cpu_usage = get_cpu_usage(ssh)
        ram_usage = get_ram_usage(ssh)
        disk_usage = get_disk_usage(ssh)
        last_transaction_dt = get_last_transaction(ssh)

        print(
            f"[{PAGE_NAME}] CPU: {cpu_usage}%"
        )

        print(
            f"[{PAGE_NAME}] RAM: {ram_usage}%"
        )

        print(
            f"[{PAGE_NAME}] Disk: {disk_usage}%"
        )

        print(
            f"[{PAGE_NAME}] Last transaction: "
            f"{last_transaction_dt}"
        )

        print(
            f"[{PAGE_NAME}] Running infrastructure RCA..."
        )

        analysis = analyze(
            cpu=cpu_usage,
            ram=ram_usage,
            disk=disk_usage,
            last_transaction=last_transaction_dt,
            command_results=command_results,
            check_transaction=True,
            ssh=ssh,
        )

        status = analysis["status"]
        root_causes = analysis["root_causes"]
        diagnostics = analysis["diagnostics"]

        diagnostic_text = format_diagnostics(
            diagnostics,
            max_lines=30,
        )

        if last_transaction_dt:
            last_transaction = (
                last_transaction_dt.strftime(
                    "%b %d %H:%M:%S"
                )
            )
        else:
            last_transaction = "No transaction found"

        checked_at = datetime.now(
            WIB
        ).strftime(
            "%d %b %Y %H:%M WIB"
        )

        output_sections.append(
            "========================================"
        )

        output_sections.append(
            "SERVER HEALTH"
        )

        output_sections.append(
            format_usage(
                "CPU Usage",
                cpu_usage,
            )
        )

        output_sections.append(
            format_usage(
                "RAM Usage",
                ram_usage,
            )
        )

        output_sections.append(
            format_usage(
                "Disk Usage",
                disk_usage,
            )
        )

        output_sections.append(
            f"Last Transaction: {last_transaction}"
        )

        output_sections.append(
            f"Status: {status}"
        )

        if root_causes:
            output_sections.append("")
            output_sections.append(
                "ROOT CAUSE"
            )

            for cause in root_causes:
                output_sections.append(
                    f"- {cause}"
                )

        output_sections.append("")
        output_sections.append(
            f"Checked: {checked_at}"
        )

        terminal_output = "\n".join(
            output_sections
        )

        render_terminal(
            title=PAGE_NAME,
            host=HOST,
            output=terminal_output,
            output_path=screenshot_path,
        )

        print(
            f"[{PAGE_NAME}] Screenshot created"
        )

        discord_lines = [
            f"🖥️ **{PAGE_NAME}**",
            f"Status: **{status}**",
            f"Last Transaction: **{last_transaction}**",
            format_usage(
                "CPU Usage",
                cpu_usage,
            ),
            format_usage(
                "RAM Usage",
                ram_usage,
            ),
            format_usage(
                "Disk Usage",
                disk_usage,
            ),
        ]

        if root_causes:
            discord_lines.append("")
            discord_lines.append(
                "**Critical Root Cause:**"
            )

            for cause in root_causes:
                discord_lines.append(
                    f"• {cause}"
                )

        if diagnostic_text:
            diagnostic_for_discord = format_diagnostics(
                diagnostics,
                max_lines=15,
            )

            discord_lines.append("")
            discord_lines.append(
                "**Diagnostic:**"
            )
            discord_lines.append(
                "```text"
            )
            discord_lines.append(
                diagnostic_for_discord
            )
            discord_lines.append(
                "```"
            )

        discord_lines.append("")
        discord_lines.append(
            f"Checked: {checked_at}"
        )

        discord_content = "\n".join(
            discord_lines
        )

        print(
            f"[{PAGE_NAME}] Sending screenshot to Discord..."
        )

        with open(
            screenshot_path,
            "rb",
        ) as image:
            response = requests.post(
                webhook_url,
                data={
                    "content": discord_content
                },
                files={
                    "file": (
                        screenshot_path,
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

        print(
            f"[{PAGE_NAME}] Screenshot sent to Discord"
        )

    except Exception as error:
        print(
            f"[{PAGE_NAME}] ERROR: {error}"
        )
        raise

    finally:
        try:
            ssh.close()
        except Exception:
            pass

        if os.path.exists(
            screenshot_path
        ):
            os.remove(
                screenshot_path
            )

        print(
            f"[{PAGE_NAME}] SSH connection closed"
        )


if __name__ == "__main__":
    run()