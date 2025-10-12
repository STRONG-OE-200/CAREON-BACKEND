# CAREON-BACKEND

## 🛠️ 레포 클론 후 최초 세팅

### 1️⃣ venv 생성 (프로젝트 최상단)

```bash
python -m venv myvenv
source myvenv/Scripts/activate
```

### 2️⃣ 패키지 설치

```bash
pip install -r requirements.txt
```

### 3️⃣ 환경 변수 설정 (.env)

> 노션에 공유된 env 파일 내용을 참고하세요.

### 4️⃣ MySQL 연결 (로컬 환경)

MySQL Workbench에서 아래명령어로 DB를 생성한 뒤 `.env` 파일에 접속 정보를 작성합니다.

> ⚠️ DB 비밀번호는 절대 공유하지 마세요.

```sql
CREATE DATABASE careon_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 5️⃣ 서버 실행 확인

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

---

## ⚠️ 주의사항

- 새로운 패키지를 설치할 때마다 다음 명령어로 `requirements.txt`를 최신 상태로 업데이트해주세요:

  ```bash
  pip freeze > requirements.txt
  ```

---

# 🤝 Contributing Guide

---

## 🐞 Issue 작성 규칙

- 이슈는 명확한 제목과 함께 생성해주세요.
- 아래 중 하나의 템플릿을 선택해 사용합니다:

  - 🐛 **Bug Report** → 버그 수정 요청
  - ✨ **Feature Request** → 새로운 기능 제안

- 제목 예시:

  ```
  [BUG] 로그인 시 JWT 토큰 만료 오류
  [FEAT] 회원가입 API 응답 스키마 수정
  ```

---

## 🌿 브랜치 규칙

> 기본 브랜치: `dev`

작업 시 항상 `dev`에서 분기합니다. 브랜치 명은 '작업종류/작업명/이름' 으로 해주세요

| 작업 종류 | 브랜치 예시                     |
| --------- | ------------------------------- |
| 기능 추가 | `feature/login-api/sebin`       |
| 버그 수정 | `fix/token-refresh/soojung`     |
| 문서 수정 | `docs/readme-update/sebin`      |
| 리팩토링  | `refactor/auth-service/soojung` |

---

## 💬 커밋 컨벤션 (Conventional Commits)

커밋 메시지는 다음 형식을 따릅니다 👇

```
<type>: <message>
```

| type     | 의미                         |
| -------- | ---------------------------- |
| feat     | 새로운 기능 추가             |
| fix      | 버그 수정                    |
| docs     | 문서 수정                    |
| style    | 코드 스타일 변경             |
| refactor | 코드 리팩토링                |
| test     | 테스트 코드 추가/수정        |
| chore    | 빌드, 패키지, 설정 파일 변경 |

**예시**

```
feat: 로그인 API 응답에 refresh token 추가
fix: JWT 인증 실패 시 500 → 401 코드로 수정
docs: README에 API 예시 추가
```

---

## 🚀 Pull Request 규칙

- PR 제목은 다음 형식을 권장합니다:

  ```
  [FEAT] 회원가입 API 구현
  [FIX] JWT 토큰 갱신 오류 수정
  ```

- PR 내용에는 반드시 아래를 포함합니다:

  - 작업 요약 (무엇을 변경했는지)
  - 관련 이슈 번호 (`Closes #이슈번호`)
  - 테스트 방법 또는 검증 결과

- PR 전 아래 항목을 꼭 확인하세요 ✅

  - [ ] 로컬에서 정상 빌드 및 테스트 통과
  - [ ] 커밋 메시지 규칙 준수

## 🙏 마지막으로

- 모든 PR은 최소 1명 이상의 리뷰어 승인 후 병합
- `main`, 'dev' 브랜치에 직접 푸시는 금지 🚫
- 간단한 문서 수정도 PR로 올려주세요 (자동 배포 트리거 방지 차원)
