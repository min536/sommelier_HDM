# PythonAnywhere SQLite 첫 세팅

이 프로젝트는 PythonAnywhere에서 **SQLite 파일 1개**로 바로 운영할 수 있게 구성되어 있다.

기본 DB 파일:

```text
sommelier.sqlite3
```

원하면 `SQLITE_PATH` 환경변수로 절대 경로를 바꿀 수 있다.

## 1. 왜 SQLite인가

현재 PythonAnywhere에서 MySQL 사용이 막혀 있는 상황이라면,
`data.json`보다 SQLite가 훨씬 낫다.

- 주문/재고/상태를 테이블로 관리
- 트랜잭션 처리 가능
- 파일 전체를 매번 덮어쓰는 JSON보다 안정적
- 별도 DB 서버 없이 바로 배포 가능

다만 PythonAnywhere 공식 도움말은 SQLite를 누구나 쓸 수 있다고 안내하면서도,
클라우드 파일 시스템 기반이라 프로덕션 DB로는 적극 권장하지 않는다고 설명한다.
이 프로젝트처럼 소규모 행사성 운영에는 현실적인 선택이지만,
장기 확장 시에는 MySQL/Postgres 재검토가 좋다.

## 2. PythonAnywhere에 코드 올리기

방법은 둘 중 하나다.

### Git으로 받기

```bash
git clone <your-repo-url>
cd korea-university-sommelier-event-pos
```

### 파일 업로드

PythonAnywhere Files 탭으로 프로젝트 폴더 전체를 올린다.

## 3. 가상환경 만들기

PythonAnywhere Bash console에서:

```bash
mkvirtualenv --python=/usr/bin/python3.13 sommelier-venv
workon sommelier-venv
pip install -r requirements.txt
```

`requirements.txt`는 Flask만 설치한다.

## 4. SQLite 초기화

프로젝트 폴더에서:

```bash
python3 scripts/init_sqlite.py
```

실행되면 DB 파일이 생성되고 기본 메뉴가 들어간다.

## 5. 기존 `data.json` 내용을 옮길 때

현재 JSON 운영 데이터를 그대로 가져가려면:

```bash
python3 scripts/migrate_json_to_sqlite.py
```

주의:

- 이 스크립트는 SQLite DB의 메뉴/테이블/통계를 `data.json` 기준으로 다시 채운다.
- 최초 1회 이전용으로만 쓰는 것이 안전하다.

## 6. Web 탭 설정

PythonAnywhere Web 탭에서:

1. **Add a new web app**
2. **Manual configuration**
3. Python 버전 선택
4. Virtualenv에 `sommelier-venv` 연결
5. WSGI 파일 수정

예시:

```python
import sys

path = "/home/YOURUSERNAME/korea-university-sommelier-event-pos"
if path not in sys.path:
    sys.path.insert(0, path)

from app import app as application
```

이 앱은 `if __name__ == "__main__":` 안에서만 `app.run()`을 호출하므로
WSGI import와 충돌하지 않는다.

## 7. SQLite 파일 경로를 고정하고 싶을 때

기본값은 프로젝트 루트의:

```text
/home/YOURUSERNAME/korea-university-sommelier-event-pos/sommelier.sqlite3
```

다른 위치를 쓰고 싶으면 WSGI 파일에서 import 전에 환경변수를 잡는다.

```python
import os
os.environ["SQLITE_PATH"] = "/home/YOURUSERNAME/korea-university-sommelier-event-pos/sommelier.sqlite3"
```

## 8. Static files 매핑

이미지 자산을 더 안정적으로 서빙하려면 Web 탭의 Static files에 아래 매핑을 추가한다.

```text
URL:       /static/
Directory: /home/YOURUSERNAME/korea-university-sommelier-event-pos/static
```

추가 후 웹앱을 Reload 한다.

## 9. 최종 확인

브라우저에서:

- `/menu`
- `/table/1`
- `/admin`

순서로 확인한다.

체크할 것:

- 메뉴 카드 이미지 로드
- 스태프 주문 생성
- 관리자 화면 반영
- 입금/서빙 토글
- 테이블 비우기

## 10. 백업

SQLite는 DB 파일 하나만 백업하면 된다.

```text
sommelier.sqlite3
```

운영 전/후로 이 파일만 따로 내려받아도 상태 백업이 가능하다.
