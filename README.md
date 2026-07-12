# Astron Trading Engine

국내 주식(KRX), 가상자산(COIN), 글로벌 선물(FUTURES)을 한 화면에서 관리하고, 여러 투자 전략의 스크리닝과 백테스트를 실행할 수 있는 통합 투자 대시보드입니다.

이 프로젝트는 FastAPI 기반 백엔드와 React/Vite 기반 프론트엔드로 구성되어 있으며, SQLite를 로컬 분석 데이터베이스로 사용합니다.

## Tech Stack

### Backend

- **Language**: Python >= 3.12
- **Framework**: FastAPI
- **Database**: SQLite
- **Data Engineering**: Pandas, NumPy
- **Package Manager**: uv

### Frontend

- **Framework**: React 19, TypeScript
- **Build Tool**: Vite
- **Styling**: TailwindCSS v4
- **Icons**: Lucide React

## Project Structure

```text
pj_invest_platform/
├── backend/
│   ├── app/
│   │   ├── cleaners/      # KRX, DART 등 수집 데이터 정제 모듈
│   │   ├── clients/       # 외부 API 클라이언트
│   │   ├── core/          # 공통 설정
│   │   ├── db/            # SQLite 스키마 및 DB 헬퍼
│   │   ├── pipelines/     # 시세, 재무, 매크로 데이터 동기화 파이프라인
│   │   ├── strategies/    # 투자 전략 및 백테스트 로직
│   │   └── main.py        # FastAPI 앱 엔트리포인트
│   ├── pyproject.toml
│   └── uv.lock
├── frontend/
│   ├── src/
│   │   ├── components/    # 대시보드 및 기능별 UI 컴포넌트
│   │   ├── App.tsx        # 화면 전환 및 앱 상태 관리
│   │   └── main.tsx       # Vite 진입점
│   ├── package.json
│   └── vite.config.ts
└── data/
    └── invest_platform.db # 로컬 SQLite 데이터베이스
```

## Key Features

### 1. 포트폴리오 및 계좌 모니터링

- 국내 주식, 가상자산, 선물 계좌의 자산 비중을 통합 확인
- 현금, 보유 자산 평가액, 손익률, MDD 등 주요 지표 추적
- 거래 내역과 실시간 로그 확인

### 2. 데이터 수집 및 정제 파이프라인

- `krx_daily_price_pipeline`: KRX 일별 시세 수집 및 저장
- `sync_financials_pipeline`: DART 재무제표 및 배당 데이터 동기화
- `sync_yahoo_futures_pipeline`: Yahoo 기반 글로벌 선물 시세 동기화
- `sync_macro_pipeline`, `sync_cftc_cot_pipeline`: 매크로 지표와 CFTC COT 데이터 수집

### 3. 투자 전략

- `undervalued_dividend_strategy`: 저평가 고배당주 스크리닝
- `opportunity_growth_strategy`: 우량 기회 성장주 스크리닝
- `sector_diversified_growth_strategy`: 섹터 분산 성장주 스크리닝
- `volume_climax`, `volume_climax_flip`: 거래량 기반 가상자산/선물 전략
- `dead_cat_short`: 낙폭과대/반등 국면 대응 전략

### 4. 프론트엔드 대시보드

- `UnifiedOverview`, `AssetMonitor`: 통합 자산 현황
- `AccountDetails`: 계좌별 자산 명세
- `StrategyList`, `StrategyDetail`: 전략 목록, 스크리닝, 백테스트 결과
- `StockExplorer`, `StockDetail`: 종목 검색 및 상세 분석
- `TransactionEntry`: 거래 입력 및 현금 수정
- `MacroDashboard`: 매크로 지표와 경제 일정 확인

## How to Run

### 1. 환경 변수 설정

`backend/.env` 파일을 생성하고 필요한 API 키를 입력합니다.

```env
DART_API_KEY=your_dart_api_key_here
ADEN_API_KEY=your_aden_api_key_here
ADEN_API_SECRET=your_aden_api_secret_here
ADEN_BASE_URL=https://api.aden.io/api/v1
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
DATABASE_URL=sqlite:///../data/invest_platform.db
```

### 2. Backend 실행

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### 3. Frontend 실행

```bash
cd frontend
npm install
npm run dev
```

개발 서버가 실행되면 `http://localhost:5173`에서 프론트엔드에 접속할 수 있습니다. Vite 프록시는 `/api` 요청을 `http://localhost:8000` 백엔드로 전달합니다.

## Verification

```bash
cd backend
uv run python -m compileall app

cd ../frontend
npm run build
```

## Security & Git Management

- `.env`, `.env.local`, `*.env` 파일은 Git 추적에서 제외합니다.
- `data/*.db`, SQLite WAL/SHM/JOURNAL 파일은 Git 추적에서 제외합니다.
- 외부 거래소 API 키와 Telegram 토큰은 반드시 환경 변수로 관리합니다.
