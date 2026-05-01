"""Entrypoint: runs proxy on 8000 and admin on 8080 in one process."""
import uvicorn
import threading
from main import proxy_app, admin_app


def run_proxy():
    uvicorn.run(proxy_app, host="0.0.0.0", port=8000, log_level="info")

def run_admin():
    uvicorn.run(admin_app, host="0.0.0.0", port=8080, log_level="info")


if __name__ == "__main__":
    t1 = threading.Thread(target=run_proxy, daemon=True)
    t2 = threading.Thread(target=run_admin, daemon=True)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
