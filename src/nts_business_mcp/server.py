"""국세청 사업자등록정보 상태조회 MCP 서버"""

import io
import os
import re
import zipfile
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

# MCP 서버 초기화
mcp = FastMCP("nts-business")

# 상수
API_BASE_URL = "https://api.odcloud.kr/api/nts-businessman/v1/status"
DART_API_BASE_URL = "https://opendart.fss.or.kr/api"
MAX_BATCH_SIZE = 100

# DART 기업 코드 캐시 (회사명 -> 기업정보)
_corp_code_cache: dict[str, list[dict[str, str]]] = {}

# 상태 코드 매핑
STATUS_CODES = {
    "01": "계속사업자",
    "02": "휴업자",
    "03": "폐업자",
}


def get_service_key() -> str:
    """환경변수에서 서비스키를 가져옵니다."""
    key = os.environ.get("NTS_SERVICE_KEY")
    if not key:
        raise ValueError(
            "NTS_SERVICE_KEY 환경변수가 설정되지 않았습니다. "
            "공공데이터포털에서 발급받은 서비스키를 설정해주세요."
        )
    return key


def get_dart_api_key() -> str:
    """환경변수에서 DART API 키를 가져옵니다."""
    key = os.environ.get("DART_API_KEY")
    if not key:
        raise ValueError(
            "DART_API_KEY 환경변수가 설정되지 않았습니다. "
            "DART OpenAPI에서 발급받은 API 키를 설정해주세요. "
            "(https://opendart.fss.or.kr)"
        )
    return key


def validate_business_number(b_no: str) -> bool:
    """사업자등록번호 형식을 검증합니다 (10자리 숫자)."""
    # 하이픈 제거 후 검증
    cleaned = re.sub(r"[-\s]", "", b_no)
    return bool(re.match(r"^\d{10}$", cleaned))


def clean_business_number(b_no: str) -> str:
    """사업자등록번호에서 하이픈과 공백을 제거합니다."""
    return re.sub(r"[-\s]", "", b_no)


async def load_corp_code_list() -> None:
    """DART 기업코드 목록을 로드합니다 (XML zip 파일)."""
    global _corp_code_cache

    if _corp_code_cache:
        return  # 이미 로드됨

    dart_api_key = get_dart_api_key()

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            f"{DART_API_BASE_URL}/corpCode.xml",
            params={"crtfc_key": dart_api_key},
        )
        response.raise_for_status()

        # ZIP 파일 압축 해제
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            xml_content = zf.read("CORPCODE.xml").decode("utf-8")

        # XML 파싱 (간단한 정규식 사용)
        import xml.etree.ElementTree as ET

        root = ET.fromstring(xml_content)

        for item in root.findall(".//list"):
            corp_code = item.findtext("corp_code", "")
            corp_name = item.findtext("corp_name", "")
            stock_code = item.findtext("stock_code", "")
            modify_date = item.findtext("modify_date", "")

            if corp_name:
                if corp_name not in _corp_code_cache:
                    _corp_code_cache[corp_name] = []
                _corp_code_cache[corp_name].append({
                    "corp_code": corp_code,
                    "corp_name": corp_name,
                    "stock_code": stock_code.strip() if stock_code else "",
                    "modify_date": modify_date,
                })


async def search_corp_by_name(company_name: str) -> list[dict[str, str]]:
    """회사명으로 기업코드를 검색합니다 (부분 일치)."""
    await load_corp_code_list()

    results = []
    search_name = company_name.lower()

    for corp_name, corp_list in _corp_code_cache.items():
        if search_name in corp_name.lower():
            results.extend(corp_list)

    return results


async def get_company_info(corp_code: str) -> dict[str, Any]:
    """기업코드로 기업 상세 정보를 조회합니다 (사업자번호 포함)."""
    dart_api_key = get_dart_api_key()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{DART_API_BASE_URL}/company.json",
            params={
                "crtfc_key": dart_api_key,
                "corp_code": corp_code,
            },
        )
        response.raise_for_status()
        return response.json()


async def call_status_api(business_numbers: list[str]) -> dict[str, Any]:
    """국세청 상태조회 API를 호출합니다."""
    service_key = get_service_key()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            API_BASE_URL,
            params={"serviceKey": service_key},
            json={"b_no": business_numbers},
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()


async def batch_status_query(business_numbers: list[str]) -> list[dict[str, Any]]:
    """100건씩 분할하여 상태를 조회합니다."""
    all_results = []

    for i in range(0, len(business_numbers), MAX_BATCH_SIZE):
        batch = business_numbers[i : i + MAX_BATCH_SIZE]
        result = await call_status_api(batch)

        if "data" in result:
            all_results.extend(result["data"])

    return all_results


def format_status_result(item: dict[str, Any]) -> dict[str, Any]:
    """API 응답을 정리된 형식으로 변환합니다."""
    b_stt_cd = item.get("b_stt_cd", "")

    return {
        "사업자등록번호": item.get("b_no", ""),
        "납세자상태": item.get("b_stt", "") or STATUS_CODES.get(b_stt_cd, "알 수 없음"),
        "상태코드": b_stt_cd,
        "과세유형": item.get("tax_type", ""),
        "폐업일자": item.get("end_dt", "") or None,
        "최근신고일자": item.get("utcc_yn", ""),
        "세금계산서적용일자": item.get("tax_type_change_dt", ""),
    }


def extract_text_from_html(html: str) -> str:
    """HTML 태그를 제거하고 텍스트만 추출합니다."""
    # HTML 태그 제거
    text = re.sub(r'<[^>]+>', '', html)
    # HTML 엔티티 디코딩
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
    return text.strip()


async def search_business_number_via_bizno(company_name: str) -> list[dict[str, Any]]:
    """bizno.net을 통해 회사의 사업자등록번호를 찾습니다."""
    import urllib.parse

    encoded_query = urllib.parse.quote(company_name)

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    results = []

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        # bizno.net 검색
        response = await client.get(
            f"https://bizno.net/?query={encoded_query}",
            headers=headers,
        )

        if response.status_code == 200:
            html_content = response.text

            # bizno.net 검색 결과에서 회사 정보 추출
            # <a href="/article/XXXXXXXXXX">...</a> 패턴 (중첩 태그 포함)
            # re.DOTALL 플래그로 줄바꿈도 매칭
            article_pattern = re.findall(
                r'<a[^>]*href="/article/(\d{10})"[^>]*>(.*?)</a>',
                html_content,
                re.DOTALL
            )

            found_numbers = set()

            for biz_no, inner_html in article_pattern:
                if biz_no not in found_numbers:
                    found_numbers.add(biz_no)
                    formatted = f"{biz_no[:3]}-{biz_no[3:5]}-{biz_no[5:]}"
                    # 내부 HTML에서 텍스트 추출
                    corp_name = extract_text_from_html(inner_html)
                    if not corp_name:
                        corp_name = company_name
                    results.append({
                        "회사명": corp_name,
                        "사업자등록번호": formatted,
                        "사업자등록번호_숫자만": biz_no,
                        "출처": "bizno.net",
                    })

    # 검색어와 가장 유사한 결과를 상위로 정렬
    def similarity_score(item: dict) -> int:
        corp_name = item.get("회사명", "").lower()
        search_name = company_name.lower()
        # (주), 주식회사 등 제거하고 비교
        corp_name_clean = re.sub(r'\(주\)|주식회사|\s+', '', corp_name)
        search_name_clean = re.sub(r'\(주\)|주식회사|\s+', '', search_name)
        if corp_name_clean == search_name_clean:
            return 0
        if search_name_clean in corp_name_clean or corp_name_clean in search_name_clean:
            return 1
        return 2

    results.sort(key=similarity_score)
    return results[:20]  # 최대 20개까지 반환


async def search_business_number_via_google(company_name: str) -> list[dict[str, Any]]:
    """구글 검색을 통해 회사의 사업자등록번호를 찾습니다."""
    import urllib.parse

    search_query = f"{company_name} 사업자등록번호"
    encoded_query = urllib.parse.quote(search_query)

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    results = []

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        # 구글 검색
        response = await client.get(
            f"https://www.google.com/search?q={encoded_query}&hl=ko",
            headers=headers,
        )

        if response.status_code == 200:
            html_content = response.text

            # 사업자등록번호 패턴 찾기 (XXX-XX-XXXXX 또는 XXXXXXXXXX)
            # 하이픈 포함 패턴
            pattern_with_hyphen = re.findall(r'\d{3}-\d{2}-\d{5}', html_content)
            # 하이픈 없는 10자리 패턴 (문맥상 사업자번호로 보이는 것)
            pattern_without_hyphen = re.findall(r'(?<!\d)\d{10}(?!\d)', html_content)

            # 중복 제거 및 결과 정리
            found_numbers = set()

            for num in pattern_with_hyphen:
                cleaned = num.replace("-", "")
                if cleaned not in found_numbers:
                    found_numbers.add(cleaned)
                    results.append({
                        "회사명": company_name,
                        "사업자등록번호": num,
                        "사업자등록번호_숫자만": cleaned,
                        "출처": "구글 검색",
                        "참고": "검색 결과에서 추출된 번호입니다. 정확성을 확인해주세요.",
                    })

            # 하이픈 없는 번호도 추가 (최대 5개까지)
            for num in pattern_without_hyphen[:5]:
                if num not in found_numbers:
                    found_numbers.add(num)
                    formatted = f"{num[:3]}-{num[3:5]}-{num[5:]}"
                    results.append({
                        "회사명": company_name,
                        "사업자등록번호": formatted,
                        "사업자등록번호_숫자만": num,
                        "출처": "구글 검색",
                        "참고": "검색 결과에서 추출된 번호입니다. 정확성을 확인해주세요.",
                    })

    return results[:10]  # 최대 10개까지 반환


@mcp.tool()
async def check_business_status(business_numbers: list[str]) -> dict[str, Any]:
    """
    사업자등록번호 목록의 상태를 조회합니다.

    Args:
        business_numbers: 사업자등록번호 목록 (하이픈 포함/미포함 모두 가능, 최대 제한 없음 - 자동 분할 처리)

    Returns:
        각 사업자의 상태 정보 (납세자상태, 과세유형, 폐업일자 등)
    """
    if not business_numbers:
        return {"error": "사업자등록번호를 입력해주세요.", "results": []}

    # 사업자번호 정제 및 검증
    cleaned_numbers = []
    invalid_numbers = []

    for b_no in business_numbers:
        cleaned = clean_business_number(b_no)
        if validate_business_number(cleaned):
            cleaned_numbers.append(cleaned)
        else:
            invalid_numbers.append(b_no)

    if invalid_numbers:
        return {
            "error": f"유효하지 않은 사업자등록번호가 있습니다: {invalid_numbers}",
            "message": "사업자등록번호는 10자리 숫자여야 합니다.",
            "results": [],
        }

    try:
        raw_results = await batch_status_query(cleaned_numbers)
        results = [format_status_result(item) for item in raw_results]

        return {
            "total_count": len(results),
            "results": results,
        }

    except httpx.HTTPStatusError as e:
        return {
            "error": f"API 호출 실패: HTTP {e.response.status_code}",
            "detail": str(e),
            "results": [],
        }
    except ValueError as e:
        return {"error": str(e), "results": []}
    except Exception as e:
        return {"error": f"예기치 않은 오류: {str(e)}", "results": []}


@mcp.tool()
async def check_business_closure(business_numbers: list[str]) -> dict[str, Any]:
    """
    사업자등록번호 목록 중 폐업된 사업자만 필터링하여 반환합니다.

    Args:
        business_numbers: 사업자등록번호 목록 (하이픈 포함/미포함 모두 가능)

    Returns:
        폐업된 사업자 목록과 폐업일자
    """
    # 먼저 전체 상태 조회
    status_result = await check_business_status(business_numbers)

    if "error" in status_result and status_result.get("results") == []:
        return status_result

    results = status_result.get("results", [])

    # 폐업자만 필터링 (상태코드 03)
    closed_businesses = [
        {
            "사업자등록번호": item["사업자등록번호"],
            "폐업일자": item["폐업일자"],
            "과세유형": item["과세유형"],
        }
        for item in results
        if item.get("상태코드") == "03"
    ]

    # 휴업자도 별도로 표시
    suspended_businesses = [
        {
            "사업자등록번호": item["사업자등록번호"],
            "과세유형": item["과세유형"],
        }
        for item in results
        if item.get("상태코드") == "02"
    ]

    return {
        "total_queried": len(results),
        "closed_count": len(closed_businesses),
        "suspended_count": len(suspended_businesses),
        "closed_businesses": closed_businesses,
        "suspended_businesses": suspended_businesses,
    }


@mcp.tool()
async def search_business_by_name(company_name: str) -> dict[str, Any]:
    """
    회사명으로 사업자등록번호를 검색합니다. (bizno.net → 구글 → DART 순서로 검색)

    Args:
        company_name: 검색할 회사명 (부분 일치 검색)

    Returns:
        검색된 회사 목록과 각 회사의 사업자등록번호
    """
    if not company_name or len(company_name) < 2:
        return {
            "error": "회사명은 2글자 이상 입력해주세요.",
            "results": [],
        }

    # 1순위: bizno.net 검색 (비상장 기업 커버리지 높음)
    try:
        bizno_results = await search_business_number_via_bizno(company_name)
        if bizno_results:
            return {
                "message": f"bizno.net에서 '{company_name}' 검색 결과입니다.",
                "total_count": len(bizno_results),
                "results": bizno_results,
            }
    except Exception:
        pass  # bizno.net 실패 시 다음 소스로

    # 2순위: 구글 검색
    try:
        google_results = await search_business_number_via_google(company_name)
        if google_results:
            return {
                "message": f"구글 검색에서 '{company_name}'의 사업자번호를 찾았습니다.",
                "total_count": len(google_results),
                "results": google_results,
            }
    except Exception:
        pass  # 구글 검색 실패 시 다음 소스로

    # 3순위: DART API (상장 기업)
    dart_api_key = os.environ.get("DART_API_KEY")
    if dart_api_key:
        try:
            corp_list = await search_corp_by_name(company_name)

            if corp_list:
                # 검색 결과가 너무 많으면 제한
                if len(corp_list) > 20:
                    return {
                        "message": f"DART 검색 결과가 {len(corp_list)}건으로 너무 많습니다. 더 구체적인 회사명을 입력해주세요.",
                        "sample_results": [
                            {"회사명": c["corp_name"], "종목코드": c["stock_code"]}
                            for c in corp_list[:10]
                        ],
                        "results": [],
                    }

                # 각 기업의 상세 정보 조회 (사업자번호 포함)
                results = []
                for corp in corp_list:
                    try:
                        info = await get_company_info(corp["corp_code"])
                        if info.get("status") == "000":  # 정상 응답
                            bizr_no = info.get("bizr_no", "")
                            # 사업자번호 포맷팅 (XXX-XX-XXXXX)
                            if bizr_no and len(bizr_no) == 10:
                                formatted_bizr_no = f"{bizr_no[:3]}-{bizr_no[3:5]}-{bizr_no[5:]}"
                            else:
                                formatted_bizr_no = bizr_no

                            results.append({
                                "회사명": info.get("corp_name", corp["corp_name"]),
                                "사업자등록번호": formatted_bizr_no,
                                "사업자등록번호_숫자만": bizr_no,
                                "법인등록번호": info.get("jurir_no", ""),
                                "대표자명": info.get("ceo_nm", ""),
                                "종목코드": info.get("stock_code", "").strip(),
                                "법인구분": info.get("corp_cls", ""),
                                "주소": info.get("adres", ""),
                                "홈페이지": info.get("hm_url", ""),
                                "설립일": info.get("est_dt", ""),
                                "출처": "DART",
                            })
                    except Exception:
                        continue

                if results:
                    return {
                        "message": f"DART에서 '{company_name}' 검색 결과입니다.",
                        "total_count": len(results),
                        "results": results,
                    }

        except Exception:
            pass  # DART 검색 실패

    # 모든 소스에서 찾지 못한 경우
    return {
        "message": f"'{company_name}'에 해당하는 회사를 찾을 수 없습니다.",
        "hint": "bizno.net, 구글, DART 모두에서 찾을 수 없습니다. 정확한 회사명을 입력해주세요.",
        "results": [],
    }


@mcp.tool()
async def search_and_check_status(company_name: str) -> dict[str, Any]:
    """
    회사명으로 사업자등록번호를 검색하고 국세청 API로 상태까지 확인합니다.

    Args:
        company_name: 검색할 회사명

    Returns:
        검색된 회사의 사업자등록번호와 국세청 상태 정보
    """
    if not company_name or len(company_name) < 2:
        return {
            "error": "회사명은 2글자 이상 입력해주세요.",
            "results": [],
        }

    # 1. 회사명으로 사업자번호 검색
    search_result = await search_business_by_name(company_name)

    if not search_result.get("results"):
        return {
            "message": f"'{company_name}'의 사업자등록번호를 찾을 수 없습니다.",
            "hint": search_result.get("hint", "정확한 회사명을 입력해주세요."),
            "results": [],
        }

    # 2. 찾은 사업자번호들의 상태 조회
    business_numbers = [
        r["사업자등록번호_숫자만"]
        for r in search_result["results"]
        if r.get("사업자등록번호_숫자만")
    ]

    if not business_numbers:
        return {
            "message": f"'{company_name}' 검색 결과에서 유효한 사업자번호를 찾을 수 없습니다.",
            "search_results": search_result["results"],
            "results": [],
        }

    # 3. 국세청 상태 조회
    status_result = await check_business_status(business_numbers)

    if "error" in status_result and not status_result.get("results"):
        return {
            "message": f"'{company_name}' 사업자번호는 찾았으나 상태 조회에 실패했습니다.",
            "search_results": search_result["results"],
            "error": status_result.get("error"),
            "results": [],
        }

    # 4. 검색 결과와 상태 정보 병합
    status_map = {
        r["사업자등록번호"]: r
        for r in status_result.get("results", [])
    }

    combined_results = []
    for search_item in search_result["results"]:
        biz_no = search_item.get("사업자등록번호_숫자만", "")
        status_info = status_map.get(biz_no, {})

        combined = {
            "회사명": search_item.get("회사명", ""),
            "사업자등록번호": search_item.get("사업자등록번호", ""),
            "출처": search_item.get("출처", ""),
            "납세자상태": status_info.get("납세자상태", "조회실패"),
            "상태코드": status_info.get("상태코드", ""),
            "과세유형": status_info.get("과세유형", ""),
            "폐업일자": status_info.get("폐업일자"),
        }

        # 추가 정보가 있으면 포함
        for key in ["대표자명", "주소", "홈페이지", "설립일", "법인등록번호"]:
            if search_item.get(key):
                combined[key] = search_item[key]

        combined_results.append(combined)

    return {
        "message": f"'{company_name}' 검색 및 상태 조회 결과입니다.",
        "total_count": len(combined_results),
        "results": combined_results,
    }


def main():
    """MCP 서버를 실행합니다."""
    mcp.run()


if __name__ == "__main__":
    main()
