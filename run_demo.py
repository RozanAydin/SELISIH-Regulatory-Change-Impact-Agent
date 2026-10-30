import sys
import os
import subprocess
import time
import urllib.request
import webbrowser
import socket

# Root directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.isfile(os.path.join(BASE_DIR, "api.py")):
    REPO_DIR = BASE_DIR
elif os.path.isfile(os.path.join(BASE_DIR, "repo_audit_latest", "api.py")):
    REPO_DIR = os.path.join(BASE_DIR, "repo_audit_latest")
elif os.path.isfile(os.path.join(BASE_DIR, "repo_enterprise_web", "api.py")):
    REPO_DIR = os.path.join(BASE_DIR, "repo_enterprise_web")
else:
    REPO_DIR = BASE_DIR

FRONTEND_DIR = os.path.join(REPO_DIR, "frontend")

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0

def free_port(port: int):
    """Free a port if occupied by terminating the listening process."""
    if not is_port_in_use(port):
        return
    try:
        # Find PID using netstat
        cmd = f'netstat -ano | findstr /R ":{port}\\>"'
        output = subprocess.check_output(cmd, shell=True).decode()
        for line in output.strip().splitlines():
            if "LISTENING" in line:
                pid = line.strip().split()[-1]
                if pid and pid != "0":
                    print(f"  [i] Membebaskan port {port} (menutup proses lama PID: {pid})...")
                    subprocess.call(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
    except Exception:
        pass

def wait_for_url(url: str, name: str, max_wait=15) -> bool:
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SELISIH-HealthCheck"})
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status in [200, 304]:
                    elapsed = round(time.time() - start_time, 1)
                    print(f"  [✓] {name} siap dalam {elapsed}s: {url}")
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def main():
    print("=======================================================================")
    print("  SELISIH: REGULATORY CHANGE IMPACT AGENT (ENTERPRISE DEMO LAUNCHER)")
    print("=======================================================================")
    print(f"  Direktori Backend : {REPO_DIR}")
    print(f"  Direktori Frontend: {FRONTEND_DIR}")
    print()

    # Step 1: Free ports
    print("[1/4] Memeriksa dan membebaskan port 8000 & 3000...")
    free_port(8000)
    free_port(3000)

    # Step 2: Start Backend
    print("[2/4] Menjalankan Backend FastAPI di port 8000...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=REPO_DIR,
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
    )

    # Step 3: Start Frontend
    print("[3/4] Menjalankan Frontend Next.js di port 3000...")
    # Check if npm is available
    frontend_cmd = "npm.cmd run start" if sys.platform == "win32" else "npm run start"
    frontend_proc = subprocess.Popen(
        frontend_cmd,
        cwd=FRONTEND_DIR,
        shell=True,
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
    )

    # Step 4: Health check
    print("[4/4] Menunggu layanan online...")
    backend_ok = wait_for_url("http://127.0.0.1:8000/api/system/health", "Backend FastAPI (Port 8000)", max_wait=15)
    frontend_ok = wait_for_url("http://localhost:3000", "Frontend Next.js (Port 3000)", max_wait=15)

    if backend_ok and frontend_ok:
        print()
        print("=======================================================================")
        print("  🎉 SISTEM SELISIH BERHASIL BERJALAN PENUH!")
        print("  👉 Dashboard Web : http://localhost:3000")
        print("  👉 API Swagger   : http://127.0.0.1:8000/docs")
        print("  👉 Benchmark API : http://127.0.0.1:8000/api/benchmark")
        print("=======================================================================")
        print("  Membuka browser otomatis...")
        try:
            webbrowser.open("http://localhost:3000")
        except Exception:
            pass
        print()
        print("  Tekan Ctrl+C di jendela ini untuk menghentikan seluruh layanan.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n  Menghentikan layanan SELISIH...")
            backend_proc.terminate()
            frontend_proc.terminate()
            free_port(8000)
            free_port(3000)
            print("  Selesai.")
    else:
        print()
        print("  [!] PERINGATAN: Salah satu layanan belum merespons tepat waktu.")
        print(f"      Backend Status : {'ONLINE' if backend_ok else 'GAGAL/MENUNGGU'}")
        print(f"      Frontend Status: {'ONLINE' if frontend_ok else 'GAGAL/MENUNGGU'}")
        print("      Silakan periksa jendela konsol hitam yang terbuka untuk melihat log.")

if __name__ == "__main__":
    main()
