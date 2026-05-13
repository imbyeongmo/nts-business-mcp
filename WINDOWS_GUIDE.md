# Windows 사용자 가이드

소스 코드 없이 Windows에서 빠르게 사용하는 방법입니다.

---

## 1단계: uv 설치 (1회)

PowerShell을 **관리자 권한**으로 실행하고 다음 명령어 입력:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

설치 확인:
```powershell
uv --version
```

---

## 2단계: API 키 발급 (무료, 1회)

1. [공공데이터포털](https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15081808) 접속
2. 회원가입 → 로그인
3. **"국세청_사업자등록정보 진위확인 및 상태조회 서비스"** 활용 신청
4. 마이페이지 → **인코딩된 서비스키** 복사해서 메모장에 저장

---

## 3단계: Claude Code에 MCP 추가

### 방법 A: 명령어로 추가 (추천)

PowerShell 또는 명령 프롬프트에서:

```powershell
claude mcp add nts-business --command uvx --args "git+https://github.com/imbyeongmo/nts-business-mcp" --env NTS_SERVICE_KEY="여기에_서비스키_입력"
```

### 방법 B: 설정 파일 직접 편집

1. 파일 탐색기에서 `%USERPROFILE%` 입력 (또는 `C:\Users\사용자명`)
2. `.claude.json` 파일 열기 (없으면 새로 만들기)
3. 다음 내용 추가:

```json
{
  "mcpServers": {
    "nts-business": {
      "command": "uvx",
      "args": ["git+https://github.com/imbyeongmo/nts-business-mcp"],
      "env": {
        "NTS_SERVICE_KEY": "여기에_서비스키_입력"
      }
    }
  }
}
```

> **중요**: `여기에_서비스키_입력` 부분을 2단계에서 복사한 인코딩된 서비스키로 교체하세요.

---

## 4단계: Claude Code 재시작

```powershell
# MCP 연결 확인
claude mcp list
```

`nts-business`가 목록에 있으면 성공!

---

## 사용 방법

Claude Code에서 자연어로 요청:

```
삼성전자 상태 확인해줘
```

```
두유비 상태 확인해줘
```

```
사업자번호 123-45-67890 상태 확인해줘
```

```
이 사업자들 중 폐업한 곳만 알려줘: 123-45-67890, 234-56-78901
```

---

## 문제 해결

### "uvx 명령어를 찾을 수 없습니다"

PowerShell을 닫고 다시 열거나, 컴퓨터를 재시작하세요.

### "NTS_SERVICE_KEY 환경변수가 설정되지 않았습니다"

1. `.claude.json` 파일에서 `NTS_SERVICE_KEY` 값이 올바른지 확인
2. 서비스키를 따옴표(`"`) 안에 넣었는지 확인

### "MCP 연결 실패"

1. `claude mcp list`로 목록 확인
2. 연결 안 되면 삭제 후 재추가:
   ```powershell
   claude mcp remove nts-business
   claude mcp add nts-business --command uvx --args "git+https://github.com/imbyeongmo/nts-business-mcp" --env NTS_SERVICE_KEY="서비스키"
   ```

### 회사명 검색이 안 될 때

- 정확한 회사명 입력: "두유비" 대신 "(주)두유비"
- 사업자번호를 알고 있다면 직접 입력

---

## 요약

| 단계 | 설명 | 1회/매번 |
|------|------|---------|
| uv 설치 | PowerShell에서 설치 스크립트 실행 | 1회 |
| API 키 발급 | 공공데이터포털에서 신청 | 1회 |
| MCP 추가 | `claude mcp add` 명령어 실행 | 1회 |
| 사용 | Claude Code에서 "OO 상태 확인해줘" | 매번 |
