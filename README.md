# 국세청 사업자등록정보 상태조회 MCP 서버

회사명 또는 사업자등록번호로 사업자 상태(계속/휴업/폐업)를 확인하는 MCP 서버입니다.

## 주요 기능

- **회사명으로 검색**: "삼성전자 상태 확인해줘" → 사업자번호 자동 검색 + 상태 확인
- **사업자번호로 조회**: 직접 사업자번호 입력하여 상태 확인
- **폐업 사업자 필터링**: 여러 사업자 중 폐업/휴업 업체만 필터링
- **비상장 기업 지원**: bizno.net 우선 검색으로 중소/중견 기업도 검색 가능

---

## 빠른 시작 (소스 코드 없이 설치)

### Windows 사용자

👉 **[Windows 전용 가이드](WINDOWS_GUIDE.md)** 참조

**요약:**
```powershell
# 1. uv 설치 (관리자 PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. MCP 추가
claude mcp add nts-business --command uvx --args "git+https://github.com/imbyeongmo/nts-business-mcp" --env NTS_SERVICE_KEY="서비스키"
```

### macOS/Linux 사용자

```bash
# 1. uv 설치
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. MCP 추가
claude mcp add nts-business \
  --command uvx \
  --args "git+https://github.com/imbyeongmo/nts-business-mcp" \
  --env NTS_SERVICE_KEY="서비스키"
```

---

## 사전 준비: API 키 발급 (무료)

1. [공공데이터포털](https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15081808) 접속
2. 회원가입 후 로그인
3. **"국세청_사업자등록정보 진위확인 및 상태조회 서비스"** 활용 신청
4. 마이페이지에서 **인코딩된 서비스키** 복사

---

## 사용 방법

Claude Code에서 자연어로 요청:

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

| 도구 | 기능 |
|------|------|
| `search_and_check_status` | 회사명 → 사업자번호 검색 → 상태 확인 (추천) |
| `search_business_by_name` | 회사명으로 사업자번호만 검색 |
| `check_business_status` | 사업자번호로 상태 조회 |
| `check_business_closure` | 폐업/휴업 사업자만 필터링 |

### search_and_check_status (추천)

회사명으로 사업자번호 검색 + 상태 확인을 한 번에 수행합니다.

**검색 우선순위:** bizno.net → 구글 → DART

**출력:**
- 회사명, 사업자등록번호
- 납세자상태 (계속사업자/휴업자/폐업자)
- 과세유형, 폐업일자

### check_business_status

사업자등록번호 목록의 상태를 조회합니다.

**출력:**
- 납세자상태 (계속사업자/휴업자/폐업자)
- 상태코드 (01: 계속, 02: 휴업, 03: 폐업)
- 과세유형, 폐업일자

---

## 설정 파일 직접 편집 (대안)

### Claude Code

`~/.claude.json` (macOS/Linux) 또는 `%USERPROFILE%\.claude.json` (Windows):

```json
{
  "mcpServers": {
    "nts-business": {
      "command": "uvx",
      "args": ["git+https://github.com/imbyeongmo/nts-business-mcp"],
      "env": {
        "NTS_SERVICE_KEY": "발급받은_서비스키"
      }
    }
  }
}
```

### Claude Desktop

macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "nts-business": {
      "command": "uvx",
      "args": ["git+https://github.com/imbyeongmo/nts-business-mcp"],
      "env": {
        "NTS_SERVICE_KEY": "발급받은_서비스키"
      }
    }
  }
}
```

---

## 로컬 설치 (개발자용)

```bash
git clone https://github.com/imbyeongmo/nts-business-mcp.git
cd nts-business-mcp
uv sync
```

MCP 추가 (로컬 경로):
```bash
claude mcp add nts-business \
  --command uv \
  --args "--directory" "/path/to/nts-business-mcp" "run" "nts-business-mcp" \
  --env NTS_SERVICE_KEY="서비스키"
```

---

## 문제 해결

| 오류 | 해결 방법 |
|------|----------|
| uvx/uv 명령어 없음 | uv 설치 후 터미널 재시작 |
| MCP 연결 실패 | `claude mcp list`로 확인 후 재추가 |
| 서비스키 오류 | 공공데이터포털에서 **인코딩된** 키 사용 |
| 회사 검색 안 됨 | 정확한 회사명 또는 사업자번호 직접 입력 |

---

## API 제한사항

- 1회 요청당 최대 100건 (자동 분할 처리됨)
- 1일 최대 100만건 (무료)

## 라이선스

MIT
