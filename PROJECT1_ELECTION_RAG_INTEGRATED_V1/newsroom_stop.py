"""Stop only a server launched by the companion Korean launcher."""
import subprocess,sys,os
from pathlib import Path
root=Path(__file__).resolve().parent
pidfile=root/'.newsroom_ko_server.pid'
if not pidfile.is_file():
 print('한글 실행 도우미로 실행된 서버 PID 기록이 없습니다.')
 print('기존 BAT로 실행했다면 해당 실행창을 닫으세요.')
 sys.exit(0)
try:pid=int(pidfile.read_text().strip())
except ValueError:
 print('서버 기록이 올바르지 않아 종료를 수행하지 않습니다.');sys.exit(2)
if os.name!='nt':
 print('이 종료 도우미는 Windows 전용입니다.');sys.exit(2)
check=subprocess.run(['tasklist','/FI',f'PID eq {pid}','/FO','CSV','/NH'],capture_output=True,text=True,errors='replace')
if 'python.exe' not in check.stdout.lower() and 'pythonw.exe' not in check.stdout.lower():
 print('기록된 PID가 Python 서버인지 확인되지 않아 강제 종료하지 않습니다.');sys.exit(2)
result=subprocess.run(['taskkill','/PID',str(pid),'/T','/F'],capture_output=True,text=True,errors='replace')
print('서버 종료 요청을 보냈습니다.' if result.returncode==0 else '서버가 이미 종료됐거나 접근이 거부되었습니다.')
pidfile.unlink(missing_ok=True)
