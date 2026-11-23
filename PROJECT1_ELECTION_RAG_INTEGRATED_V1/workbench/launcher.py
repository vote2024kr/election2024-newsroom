"""Start the local tool, check readiness, and open the system browser."""
from __future__ import annotations
import subprocess
import sys
import time
import webbrowser
from urllib.request import urlopen

PORT=8530
URL=f'http://127.0.0.1:{PORT}'

def main():
    cmd=[sys.executable,'-m','uvicorn','app.server:app','--host','127.0.0.1','--port',str(PORT)]
    proc=subprocess.Popen(cmd)
    try:
        ready=False
        for _ in range(60):
            if proc.poll() is not None:break
            try:
                with urlopen(URL+'/api/health',timeout=.5) as r:ready=r.status==200
                if ready:break
            except Exception:time.sleep(.25)
        if not ready:
            print(f'서버가 열리지 않았습니다. 포트 {PORT} 사용 여부 또는 위의 오류를 확인하세요.')
            return 1
        print(f'통합 통계툴 실행 중: {URL}')
        print('브라우저가 열리지 않으면 위 주소를 직접 입력하세요. Ctrl+C로 종료합니다.')
        webbrowser.open(URL)
        proc.wait()
        return proc.returncode or 0
    except KeyboardInterrupt:
        print('서버를 종료합니다.')
        return 0
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill()
if __name__=='__main__':raise SystemExit(main())
