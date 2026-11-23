"""Korean local Windows launcher; avoids a batch nesting loop and saves PID for clean stop."""
import os,sys,socket,subprocess,webbrowser,time,signal
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PORT=8541
PIDFILE=ROOT/'.newsroom_ko_server.pid'

def occupied():
    with socket.socket() as s:
        s.settimeout(0.2)
        return s.connect_ex(('127.0.0.1',PORT))==0

if occupied():
    print('8541번 포트에서 NEWSROOM 또는 다른 프로그램이 이미 실행 중입니다.')
    print('기존 실행창이나 "뉴스룸_종료_한글.bat"로 서버를 종료한 뒤 다시 실행해 주세요.')
    print('기존 서버를 임의로 강제 종료하지 않습니다.')
    sys.exit(2)
py=ROOT/'.venv'/'Scripts'/'python.exe'
if not py.exists():
    print('실행에 필요한 가상환경이 없습니다. 기존 START_PROJECT1_WINDOWS.bat를 한 번 실행해 설치를 완료해 주세요.')
    sys.exit(3)
print('NEWSROOM LAB 서버 실행 중… 주소: http://127.0.0.1:8541/')
print('종료할 때는 "뉴스룸_종료_한글.bat"를 사용하세요.')
proc=subprocess.Popen([str(py),'-m','uvicorn','project1_app:app','--host','127.0.0.1','--port',str(PORT)],cwd=str(ROOT))
PIDFILE.write_text(str(proc.pid),encoding='ascii')
time.sleep(2)
if proc.poll() is None: webbrowser.open('http://127.0.0.1:8541/safe2024')
try:sys.exit(proc.wait())
except KeyboardInterrupt:
    print('\n종료 신호를 받았습니다. 서버를 정리합니다.')
    proc.terminate()
    try:proc.wait(timeout=7)
    except subprocess.TimeoutExpired:proc.kill()
finally:
    try:PIDFILE.unlink(missing_ok=True)
    except OSError:pass
