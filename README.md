# Astron Trading Engine (아스트론 트레이딩 엔진)

다중 자산 통합 투자 파이프라인 및 전략 시뮬레이션/모니터링 대시보드 플랫폼입니다. 국내 주식(KRX), 가상자산(COIN), 글로벌 선물(FUTURES) 등 다중 자산을 통합 관리하고 다양한 계량 매매 전략을 백테스트하고 관제할 수 있는 시스템입니다.

---

## 🛠 Tech Stack (기술 스택)

### Backend
- **Language**: Python >= 3.12
- **Framework**: FastAPI (Astron Trading Engine API)
- **Database**: SQLite (로컬 가볍고 신속한 관계형 DB 관리)
- **Data Engineering**: Pandas, NumPy (시계열 데이터 처리 및 세정)
- **Package Manager**: `uv` (빠르고 안정적인 패키지 동기화)

### Frontend
- **Framework**: React 19 (TypeScript)
- **Build Tool**: Vite
- **Styling**: TailwindCSS v4 (유연한 Glassmorphism 및 네온 다크 테마 구현)
- **Icons**: Lucide React

---

## 📂 Project Structure (프로젝트 구조)

```text
pj_invest_platform/
├── backend/
│   ├── app/
│   │   ├── cleaners/      # 수집된 원시 데이터(KRX, DART 등) 정제 모듈
│   │   ├── clients/       # API 통신 클라이언트 (KRX 수집기, DART 공시 수집기 등)
│   │   ├── core/          # 공통 유틸리티 및 설정
│   │   ├── db/            # 데이터베이스 스키마 및 초기화 모듈
│   │   ├── pipelines/     # 일일 시세 및 재무 데이터 동기화 파이프라인
│   │   ├── strategies/    # 퀀트 투자 전략 핵심 알고리즘
│   │   └── main.py        # FastAPI 엔드포인트 및 서버 엔트리포인트
│   ├── pyproject.toml     # 백엔드 의존성 및 프로젝트 메타데이터
│   └── uv.lock            # uv 패키지 잠금 파일
├── frontend/
│   ├── src/
│   │   ├── components/    # 기능별 공통 UI 컴포넌트
│   │   ├── App.tsx        # 프론트엔드 라우터 및 상태 관리 메인 랩퍼
│   │   └── main.tsx       # Vite 앱 진입점
│   ├── package.json       # 프론트엔드 의존성 설정
│   └── vite.config.ts     # Vite 빌드 설정
└── data/
    └── invest_platform.db # 로컬 분석용 SQLite 데이터베이스 파일 (Git Ignore 대상)
```

---

## 🌟 Key Features (핵심 기능)

### 1. 다중 자산 실시간 포트폴리오 관리 (Asset Allocation)
- 보유 자산에 따른 실시간 포트폴리오 비중(주식, 가상자산, 현금) 자동 시각화.
- MDD(최대 낙폭), 누적 수익률, 당일 손익 등 핵심 포트폴리오 지표 실시간 추적.

### 2. 백엔드 데이터 파이프라인 & 데이터 클리너
- **시세 동기화 (`krx_daily_price_pipeline`)**: KRX 일일 시세 수집 및 유효성 검증.
- **재무 동기화 (`sync_financials_pipeline`)**: DART OpenAPI 연동 기업 재무 지표 자동 적재.
- **데이터 세정기 (`cleaners/`)**: 불완전 데이터 보정 및 정규화(주식 분할/병합 처리, 배당금 정보 정제 등).

### 3. 탑재된 퀀트 매매 전략 (Investment Strategies)
- **우량 기회 성장 전략 (`opportunity_growth_strategy`)**: 재무 건전성 및 시장 점수 기반 고성장주 포착.
- **저평가 고배당 전략 (`undervalued_dividend_strategy`)**: 역사적 배당 성향 및 밸류에이션 지표 필터링.
- **거래량 임계 돌파 전략 (`volume_climax`)**: 급격한 거래량 스파이크 분석 및 모멘텀 매매 시그널.
- **역발상 거래량 전략 (`volume_climax_flip`)**: 거래량 폭발 후 추세 반전을 노리는 스윙 매매.

### 4. 고해상도 대시보드 화면 및 컴포넌트
- **대시보드 오버뷰 (`UnifiedOverview`, `AssetMonitor`)**: 자산 분배 원형 차트 및 실시간 시세 시계열 관제.
- **실시간 알림 및 콘솔 (`SignalAlerts`, `LiveLogs`)**: 매매 알고리즘이 발행한 시그널과 백엔드 배치 서버 실행 로그 실시간 확인.
- **원장 입력 폼 (`TransactionEntry`)**: 신규 거래 내역(매수/매도) 추가, 삭제 및 예수금 잔고(Cash) 즉각 업데이트 기능.
- **종목 검색 및 분석 (`StockExplorer`, `StockDetail`)**: 개별 상장 종목 재무 지표 대시보드 및 차트 상세 분석 지원.

---

## 🚀 How to Run (실행 방법)

### 1. 환경 변수 설정
`backend/.env` 파일을 생성하고 필요한 API 토큰 및 키를 입력합니다:
```env
# backend/.env 예시
DART_API_KEY=your_dart_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
DATABASE_URL=sqlite:///../data/invest_platform.db
```

### 2. Backend 실행
백엔드 폴더(`backend/`)로 이동하여 종속성을 설치하고 서버를 실행합니다:
```bash
cd backend

# uv가 설치되어 있는 경우 패키지 동기화 및 가상환경 설정
uv sync

# uvicorn을 이용해 FastAPI 서버 가동
uv run uvicorn app.main:app --reload --port 8000
```

### 3. Frontend 실행
프론트엔드 폴더(`frontend/`)로 이동하여 패키지를 설치하고 개발 서버를 실행합니다:
```bash
cd frontend

# 종속성 패키지 설치
npm install

# Vite 개발 서버 실행
npm run dev
```
개발 서버 실행 후 `http://localhost:5173`을 통해 접속할 수 있으며, 개발 환경에서는 Vite 프록시 설정을 통해 백엔드 API 서버(`http://localhost:8000`)와 연결됩니다.

---

## 🔒 Security & Git Management (보안 및 버전 관리)
- 로컬 SQLite 데이터베이스 파일(`data/*.db`)과 API 키가 보관된 `.env` 파일은 민감 정보 노출 및 비대한 바이너리 커밋 방지를 위해 루트 레벨 `.gitignore`를 통해 Git 추적에서 제외되었습니다.
