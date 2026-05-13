# 국세청 사업자등록정보 상태조회 MCP 서버

회사명 또는 사업자등록번호로 사업자 상태(계속/휴업/폐업)를 확인하는 MCP 서버입니다.

## 주요 기능

- **회사명으로 검색**: "삼성전자 상태 확인해줘" → 사업자번호 자동 검색 + 상태 확인
- **사업자번호로 조회**: 직접 사업자번호 입력하여 상태 확인
- **폐업 사업자 필터링**: 여러 사업자 중 폐업/휴업 업체만 필터링

---

## 비개발자를 위한 설치 가이드

### 1단계: API 키 발급 (무료)

1. [공공데이터포털](https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15081808) 접속
2. 회원가입 후 로그인
3. **"국세청_사업자등록정보 진위확인 및 상태조회 서비스"** 활용 신청
4. 마이페이지에서 **인코딩된 서비스키** 복사

### 2단계: Claude Code에 MCP 추가

터미널에서 다음 명령어 실행:

```bash
claude mcp add nts-business \
  --command uv \
  --args "--directory" "/Users/nhn/ai/tmp/nts-business-mcp" "run" "nts-business-mcp" \
  --env NTS_SERVICE_KEY="여기에_발급받은_서비스키_입력"
```

> **Windows 사용자**: 경로를 `C:\Users\사용자명\...\nts-business-mcp` 형식으로 변경

### 3단계: Claude Code 재시작

```bash
# MCP 연결 확인
claude mcp list
```

---

## 사용 방법

Claude Code에서 자연어로 요청하면 됩니다:

### 회사명으로 상태 확인
```
삼성전자 상태 확인해줘
두유비 상태 확인해줘
(주)시냅스엠 상태 확인해줘
```

### 사업자번호로 직접 조회
```
사업자번호 123-45-67890 상태 확인해줘
451-81-00041, 446-87-01318 상태 조회해줘
```

### 폐업 사업자 필터링
```
이 사업자들 중 폐업한 곳만 알려줘: 123-45-67890, 234-56-78901, 345-67-89012
```

---

## 제공 도구

### 1. `search_and_check_status` (추천)

회사명으로 사업자번호 검색 + 상태 확인을 한 번에 수행합니다.

**입력:** 회사명 (예: "삼성전자", "두유비")

**출력:**
- 회사명, 사업자등록번호
- 납세자상태 (계속사업자/휴업자/폐업자)
- 과세유형, 폐업일자

**검색 우선순위:** bizno.net → 구글 → DART (비상장 기업도 검색 가능)

### 2. `search_business_by_name`

회사명으로 사업자등록번호만 검색합니다.

### 3. `check_business_status`

사업자등록번호 목록의 상태를 조회합니다.

**입력:** 사업자등록번호 목록 (예: `["123-45-67890", "1234567890"]`)

**출력:**
- 납세자상태 (계속사업자/휴업자/폐업자)
- 상태코드 (01: 계속, 02: 휴업, 03: 폐업)
- 과세유형
- 폐업일자 (폐업자인 경우)

### 4. `check_business_closure`

사업자등록번호 목록 중 폐업/휴업된 사업자만 필터링합니다.

---

## 설정 파일 직접 편집 (대안)

### Claude Code

`~/.claude.json` 또는 프로젝트의 `.mcp.json` 파일:

```json
{
  "mcpServers": {
    "nts-business": {
      "command": "uv",
      "args": ["--directory", "/Users/nhn/ai/tmp/nts-business-mcp", "run", "nts-business-mcp"],
      "env": {
        "NTS_SERVICE_KEY": "발급받은_서비스키"
      }
    }
  }
}
```

### Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
`%APPDATA%\Claude\claude_desktop_config.json` (Windows)

```json
{
  "mcpServers": {
    "nts-business": {
      "command": "uv",
      "args": ["--directory", "/path/to/nts-business-mcp", "run", "nts-business-mcp"],
      "env": {
        "NTS_SERVICE_KEY": "발급받은_서비스키"
      }
    }
  }
}
```

---

## 문제 해결

### "MCP 연결 실패" 오류
1. `uv`가 설치되어 있는지 확인: `uv --version`
2. 설치 안 됨: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### "NTS_SERVICE_KEY 환경변수가 설정되지 않았습니다" 오류
- MCP 설정에서 `env.NTS_SERVICE_KEY` 값이 올바른지 확인

### 회사명 검색이 안 될 때
- 정확한 회사명 입력 (예: "두유비" 대신 "(주)두유비")
- 사업자번호를 알고 있다면 직접 입력

---

## API 제한사항

- 1회 요청당 최대 100건 (자동 분할 처리됨)
- 1일 최대 100만건 (무료)

## 라이선스

MIT
