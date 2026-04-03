# 연구용 브레인 디지털 트윈(Brain Digital Twin) 플랫폼 기획서

## 1. 플랫폼 개요 및 목표
### 1.1 개요
본 플랫폼은 **구조적 MRI(T1, T2/FLAIR, dMRI)** 기반으로 뇌의 발달 과정과 퇴행성 뇌질환을 예측하고 시뮬레이션하는 **연구용 인실리코(In-silico) 뇌 시뮬레이션 통합 환경**을 제공합니다. 다중 오믹스(유전체, 전사체 등)와 장내 미생물(Gut Microbiome) 데이터를 추가 통합하여 다차원적 예측 정밀도를 확보합니다.

### 1.2 비즈니스 모델
- **연구용(Research Use Only, RUO) 판매**: 의료기기 허가 없이 연구기관/제약사/대학 등에 연구 도구로 판매
- **SaaS 기반 구독 모델**: 소프트웨어 배포 없이 클라우드에서 서비스 제공 (GPL 라이선스 리스크 최소화)
- **온프레미스 배포 옵션**: 데이터 보안이 중요한 기관을 위한 설치형 (GPL-free 스택만 사용)

### 1.3 목표
- **구조적 MRI 중심 디지털 트윈 구축:** T1/T2/FLAIR/dMRI 기반 뇌 형태, 연결체, 병변을 정량화하여 개인화된 뇌 디지털 트윈 생성
- **초대규모 공개 데이터 활용:** UK Biobank(50,000+ 구조적 MRI), ADNI, HCP, ABCD 등 글로벌 오픈 데이터셋으로 모델의 일반화 성능 확보
- **상용 가능한 기술 스택:** 모든 핵심 구성요소를 Apache 2.0/MIT/BSD 라이선스 도구로 구성하여 상업적 판매에 법적 제약 없음
- **안전한 모의 실험 환경 제공:** 구조적 바이오마커 기반 인실리코 실험 인프라 확립
- **데이터 기반 질병 예측:** 영유아 발달 장애 조기 선별 및 고령층 퇴행성 뇌질환의 종단적 궤적 예측

---

## 2. 핵심 전략: 구조적 MRI 중심 접근

### 2.1 왜 구조적 MRI인가

| 비교 항목 | fMRI 기반 (TRIBE v2 등) | 구조적 MRI 기반 (Synapse-D) |
| :--- | :--- | :--- |
| **상용 가능 여부** | CC BY-NC → 판매 불가 | Apache/MIT 도구 → **판매 가능** |
| **임상 데이터 접근성** | 특수 연구시설에서만 촬영 | **모든 병원**에서 촬영 가능 |
| **재현성** | fMRI BOLD 신호 변동성 높음 | 구조적 측정은 **재현성 높음** |
| **바이오마커 근거** | 자극 반응 예측 (연구 특화) | 발달/퇴화 바이오마커 (**임상 근거 풍부**) |
| **데이터 규모** | TRIBE v2: 700명 fMRI | UK Biobank: **50,000+** 구조적 MRI |
| **시장 범위** | 신경과학 연구자만 | 연구자 + 임상의 + **제약사** |

### 2.2 구조적 MRI 모달리티별 역할

| MRI 모달리티 | 측정 대상 | 발달/퇴화 바이오마커 |
| :--- | :--- | :--- |
| **T1-weighted** | 피질 두께, 회백질 부피, 뇌 형태계측 | Brain Age Gap, 해마 위축, 뇌실 확장, 피질 얇아짐 |
| **T2/FLAIR** | 백질 고신호 병변(WMH), 수초화 | WMH 부담량(혈관성 치매 위험), 영유아 수초화 진행 |
| **dMRI** | 백질 신경로, 구조적 연결체 | FA/MD 이상(백질 무결성), 연결체 변화 |

### 2.3 생애주기별 예측 모델

| 생애 단계 | 핵심 구조적 바이오마커 | MRI 모달리티 | 예측 대상 |
| :--- | :--- | :--- | :--- |
| 영유아 (0-2세) | 전체 뇌 부피, 수초화 패턴 | T1, T2 | 발달 지연, ASD 위험 |
| 아동-청소년 | 피질 두께, 백질 성숙 | T1, dMRI | 인지 발달 궤적, ADHD |
| 청년-중년 | Brain Age Gap, WMH 발생 | T1, FLAIR | 조기 노화, 치매 위험 |
| 노년 | 해마 위축, WMH 진행, 뇌실 확장 | T1, T2/FLAIR | AD 진행, 혈관성 치매 |

---

## 3. 주요 대상 및 사용자 가치
- **주요 사용자 (Target Audience):** 신경과학 연구자, 임상 의학자, 제약/바이오 R&D 연구원 및 데이터 과학자
- **제공 가치 (Service Value):**
  - **Zero-Data Start 가능:** 플랫폼 내장 공개 데이터베이스 라우팅을 통한 즉각적 연구 착수
  - **표준 MRI로 즉시 분석:** T1/T2 MRI만으로 Brain Age, 형태계측, 병변 탐지 가능
  - **종단적 궤적 예측:** 현재 MRI에서 미래 뇌 구조 변화를 예측
  - **가상 코호트 생성:** 윤리적 제약이 있는 대상(영유아/희귀질환)의 가상 임상시험 지원

---

## 4. 핵심 플랫폼 아키텍처 및 서비스 구성
본 플랫폼은 **5계층 시스템**으로 구성되며, 모든 핵심 구성요소는 상용 가능한 라이선스(Apache 2.0/MIT/BSD)로 구성합니다.

### 4.1 Layer 1: Data Management & Governance (데이터 계층)
- **오픈 데이터셋 자동 병합 인프라:**
  - BrainScape(MIT) 활용 160개+ 공개 MRI 데이터 자동 다운로드 및 BIDS 표준화
  - UK Biobank, ADNI, HCP, ABCD, dHCP, OASIS-3 등 주요 데이터셋 연동
- **다중 모달리티 통합 파이프라인:**
  - **구조적 MRI:** T1/T2/FLAIR/dMRI 자동 전처리 및 품질 관리
  - **다중 오믹스:** 유전체, 전사체, 후성유전체 데이터 통합 (이미징 트랜스크립토믹스)
  - **장내 미생물:** 장-뇌 축(Gut-Brain Axis) 상태 파라미터화 (MIMIC 활용)
- **보안/거버넌스:** 신뢰 연구 환경(TRE) 내 연합 학습(Federated Learning) 지원

### 4.2 Layer 2: Preprocessing Pipeline (전처리 계층) — 전체 Apache 2.0
```
[입력: T1/T2/FLAIR/dMRI (BIDS 포맷)]
    │
    ├── HD-BET (Apache 2.0) ─────── 뇌 추출 (Brain Extraction)
    ├── ANTs (Apache 2.0) ────────── 공간 정합 및 정규화 (Registration)
    ├── FastSurfer (Apache 2.0) ──── 피질/피질하 세그멘테이션 (1분 이내)
    ├── SynthSeg (Apache 2.0) ────── 대조도 무관 범용 세그멘테이션
    └── nnU-Net (Apache 2.0) ─────── WMH/병변 세그멘테이션
```

### 4.3 Layer 3: Morphometric Analysis (형태계측 분석 계층)
- **피질 두께/부피 측정:** FastSurfer(Apache 2.0) — FreeSurfer 대비 100배 빠른 딥러닝 세그멘테이션
- **Voxel-Based Morphometry:** ANTs(Apache 2.0) 기반 VBM/DBM 분석
- **구조적 연결체 생성:** Connectome Mapper 3(BSD-3) — dMRI 트랙토그래피 → 연결 행렬
- **통계 분석/시각화:** Nilearn(BSD-3), BrainStat(BSD-3) — 규범 모델링 및 인구 비교

### 4.4 Layer 4: AI Prediction Engine (AI 예측 엔진 계층) — 전체 MIT/Apache 2.0
| AI 기능 | 모델/프레임워크 | 라이선스 | 설명 |
| :--- | :--- | :--- | :--- |
| **Brain Age 예측** | SFCN (UK Biobank 사전학습) | MIT | MAE ~2.14년, 뇌 건강 정량화 |
| **AD/MCI 위험 분류** | AD 진단 프레임워크 (vkola-lab) | MIT | SHAP 기반 해석 가능 AI |
| **위축 진행 예측** | 자체 모델 (MONAI 기반) | Apache 2.0 | 종단적 형태 변화 예측 |
| **WMH 진행 예측** | 자체 모델 (nnU-Net 기반) | Apache 2.0 | 혈관성 치매 위험 예측 |
| **커스텀 DL 모델** | MONAI Framework | Apache 2.0 | PyTorch 기반, NVIDIA 지원 |
| **규범 모델링** | BrainStat | BSD-3 | 개인 뇌를 인구 기반 규범과 비교 |

> **자체 파운데이션 모델 로드맵:** UK Biobank 50,000+ T1 MRI 데이터로 ViT/MAE 기반 구조적 MRI 파운데이션 모델을 자체 학습 → 현재 공개된 구조적 MRI 파운데이션 모델이 없으므로 **선점 기회** 존재

### 4.5 Layer 5: Brain Simulation Engine (뇌 시뮬레이션 계층)
- **단기 (Phase 1-2):** TVB를 SaaS 모드로 서버에서만 실행 (GPLv3는 배포에만 적용, SaaS는 배포가 아님)
- **중장기 (Phase 3):** JAX/PyTorch 기반 **자체 미분가능(Differentiable) 뇌 시뮬레이터** 개발
  - 신경질량모델(Wilson-Cowan, Jansen-Rit, Kuramoto 등)은 수학 공식 → 저작권 무관
  - GPU 가속으로 TVB보다 빠름, 역전파 가능 → 관측 데이터에 파라미터 피팅
  - 완전한 상업적 자유

### 4.6 Application & Service Layer (사용자 서비스 계층) — Web 기반

> **결정 근거:** 현존하는 모든 주요 Brain Digital Twin 플랫폼(TVB, EBRAINS, BrainLife.io, Allen Brain Atlas)이 Web 기반을 채택. Python/Jupyter 생태계와의 네이티브 통합, 클라우드 배포, 접근성 측면에서 Web이 Unity 대비 압도적 우위.

| 구성요소 | 기술 | 라이선스 |
| :--- | :--- | :--- |
| 프론트엔드 | React 18+ (Next.js 14+) | MIT |
| 3D 뇌 시각화 | React Three Fiber + VTK.js | MIT/BSD |
| 신경영상 뷰어 | Niivue (fMRI/dMRI 전용) | BSD |
| 차트/그래프 | D3.js + Plotly.js | MIT/BSD |
| 네트워크 시각화 | Cytoscape.js | MIT |
| 백엔드 | FastAPI (Python) + Celery | MIT/BSD |
| Jupyter 통합 | JupyterHub 내장 | BSD |
| 실시간 통신 | WebSocket | - |
| 인프라 | Kubernetes + Docker | Apache 2.0 |
| 인증 | Keycloak | Apache 2.0 |

**주요 서비스 기능:**
- 인실리코 뇌 시뮬레이션 및 모델링 GUI
- Brain Age 대시보드 및 규범 비교 차트
- 종단적(Longitudinal) 형태 변화 3D 시각화 (위축 진행, WMH 진행)
- 가상 피험자 및 환자 코호트 관리
- 연구 워크스페이스 및 Jupyter Notebook 환경

---

## 5. 라이선스 전략 및 기술 스택

### 5.1 상용 안전 스택 (핵심 파이프라인)

| 모듈(기능) | 권장 기술 스택 | 라이선스 | 상용 판매 |
| :--- | :--- | :--- | :--- |
| **뇌 추출** | HD-BET | Apache 2.0 | **가능** |
| **공간 정합** | ANTs | Apache 2.0 | **가능** |
| **세그멘테이션** | FastSurfer, SynthSeg | Apache 2.0 | **가능** |
| **병변 세그멘테이션** | nnU-Net | Apache 2.0 | **가능** |
| **DL 프레임워크** | MONAI | Apache 2.0 | **가능** |
| **Brain Age 예측** | SFCN | MIT | **가능** |
| **AD 위험 분류** | AD 진단 (vkola-lab) | MIT | **가능** |
| **통계 분석** | Nilearn | BSD-3 | **가능** |
| **규범 모델링** | BrainStat | BSD-3 | **가능** |
| **연결체 생성** | Connectome Mapper 3 | BSD-3 | **가능** |
| **DL 뇌 추출** | Nobrainer | Apache 2.0 | **가능** |
| **데이터 통합** | BrainScape | MIT | **가능** |
| **마이크로바이옴** | MIMIC | MIT | **가능** |
| **멀티오믹스** | Scbean | MIT | **가능** |
| **기반 인프라** | PyTorch, Kubernetes | BSD/Apache 2.0 | **가능** |

### 5.2 사용 금지 목록

| 도구 | 라이선스 | 금지 사유 | 대체 도구 |
| :--- | :--- | :--- | :--- |
| **TRIBE v2** (Meta) | CC BY-NC 4.0 | 상업적 사용 절대 불가 | 자체 구조적 MRI AI 모델 |
| **NiChart** (CBICA) | 비상용 라이선스 | 상용 불가 | BrainStat + 자체 규범 모델 |
| **FSL** | 커스텀 (상용 유료) | 상용 시 별도 유료 라이선스 필요 | ANTs (Apache 2.0) |
| **CAT12/SPM** | GPL v2+ | 파생물 GPL 공개 의무 | FastSurfer + ANTs |

### 5.3 조건부 사용 (주의 필요)

| 도구 | 라이선스 | 사용 조건 | 대응 전략 |
| :--- | :--- | :--- | :--- |
| **TVB** | GPLv3 | 배포 시 소스코드 공개 의무 | SaaS 모드(서버 실행)로만 사용 → 배포 아님 |
| **FreeSurfer** | 커스텀 | "연구 목적 설계" 명시, 법무 검토 필요 | FastSurfer(Apache 2.0)로 대체 권장 |
| **DKT** | 기본 저작권 | 상업적 사용 시 원저작자 동의 필요 | 사전 동의 확보 또는 자체 모델 학습 |
| **brainageR** | LGPL v3 | 라이브러리 사용 가능, 수정 시 공개 의무 | SFCN(MIT)으로 대체 권장 |

### 5.4 GPL 오염 방지 규칙

| 규칙 | 설명 |
| :--- | :--- |
| **절대 금지** | GPL 코드를 플랫폼 코드에 직접 import/link |
| **허용 (SaaS)** | GPL 도구를 별도 컨테이너에서 실행, API로 결과만 수신 |
| **허용 (CLI)** | GPL 도구를 CLI 명령으로 호출 (시스템 라이브러리 예외) |
| **권장** | 모든 핵심 코드는 Apache 2.0/MIT/BSD 도구로만 구성 |

> [!WARNING] **상용 판매 시 법무 지침**
> 1. **SaaS 모델 우선:** GPLv3 도구(TVB 등)를 사용하더라도 서버에서만 실행하고 소프트웨어를 배포하지 않으면 소스코드 공개 의무가 발생하지 않습니다.
> 2. **온프레미스 배포 시:** GPL 구성요소를 완전히 제거하거나 별도 컨테이너로 분리하고, GPL-free 스택만 고객에게 배포해야 합니다.
> 3. **CC BY-NC 도구(TRIBE v2 등):** "연구용 판매"라 하더라도 유상 판매는 상업적 활동이므로 NC 조항 위반입니다. 절대 사용 불가합니다.

---

## 6. 사용자 환경: Web 기반 아키텍처

> **결정:** Unity가 아닌 **Web 기반**으로 구축

### 6.1 결정 근거

| 평가 기준 | Web (React+Three.js+VTK.js) | Unity |
| :--- | :--- | :--- |
| Python/Jupyter 통합 | 네이티브 수준 | 본질적 단절 (C# 기반) |
| 클라우드/SaaS 배포 | 네이티브 | 매우 어려움 |
| 접근성 | 브라우저만 필요 | 설치 필요 (수백 MB~수 GB) |
| 과학 데이터 시각화 | D3/Plotly/VTK.js 생태계 | 사실상 부재 |
| 신경영상 전용 도구 | Niivue, VTK.js | 직접 구현 필요 |
| 협업/공유 | URL 기반 즉시 공유 | 불가 |
| 3D 렌더링 성능 | 충분 (WebGL2/WebGPU) | 최고 성능 (유일한 장점) |
| **업계 표준** | TVB, EBRAINS, BrainLife.io 모두 Web | 사례 없음 |

### 6.2 권장 기술 스택
```
프론트엔드: React 18+ / Next.js 14+
3D 렌더링: React Three Fiber (Three.js) + VTK.js (과학 시각화)
신경영상:  Niivue (fMRI/dMRI 전용 뷰어)
차트/그래프: D3.js + Plotly.js
네트워크:  Cytoscape.js (마이크로바이옴/커넥톰)
백엔드:    FastAPI (Python) + Celery + Redis
Jupyter:   JupyterHub 내장
실시간:    WebSocket (시뮬레이션 모니터링)
인프라:    Kubernetes + Docker + Helm
인증:      Keycloak (SSO/OAuth)
```

### 6.3 향후 VR 확장 (선택적)
Phase 4에서 Unity 기반 독립 VR 모듈을 별도 개발하여 몰입형 뇌 구조 탐색/교육용으로 제공 가능. 공유 API로 메인 플랫폼과 데이터 동기화.

---

## 7. 물리 엔진 관련 결정

> **결정:** 물리 엔진(Bullet, PhysX 등)은 **불필요**

Brain Digital Twin은 뇌의 "물리적 구조 역학"이 아닌 **"기능적 역학"**을 시뮬레이션합니다. 플랫폼의 모든 시뮬레이션 엔진은 미분방정식 솔버 또는 AI 추론 엔진을 사용합니다.

| 구성요소 | 물리 엔진 필요? | 실제 사용 기술 |
| :--- | :--- | :--- |
| TVB 뇌 네트워크 시뮬레이션 | 불필요 | ODE/PDE 수치 적분 |
| 스파이킹 신경망 | 불필요 | 이벤트 기반 + ODE 솔버 |
| Brain Age/형태 예측 | 불필요 | 딥러닝 추론 (CNN/ViT) |
| 미생물 모델링 | 불필요 | 베이지안 추론 + gLV ODE |
| 3D 시각화 | 불필요 | WebGL 그래픽 렌더링 |

---

## 8. 단계별 개발 로드맵 (Roadmap)

> **전문가 조언 반영:** Phase 1-2에서 AI 예측 엔진(SFCN Brain Age, nnU-Net 병변 분석)으로 조기 캐시카우를 확보하고, 신경수학적 난이도가 극높은 자체 JAX 시뮬레이터 개발은 Phase 4 이후로 이연하여 리스크를 분산합니다.

### Phase 1: 핵심 파이프라인 및 MVP (6개월)
- **전처리 파이프라인:** HD-BET + ANTs + FastSurfer 기반 구조적 MRI 자동 분석
- **AI 예측 (캐시카우 #1):** Brain Age 예측 모델 통합 (SFCN, MIT) — 즉시 연구 가치 제공
- **형태계측:** 피질 두께/부피 자동 추출 및 규범 비교
- **데이터 인프라:** BIDS 표준 데이터 관리 + S3 호환 오브젝트 스토리지 티어링 설계
- **Web UI:** React + Three.js 기반 기본 3D 뇌 시각화 및 대시보드
- **클라우드:** Kubernetes 기반 기본 배포 환경 구축

### Phase 2: 예측 모델 강화 — 수익 모델 확립 (6개월)
- **AI 예측 (캐시카우 #2):** WMH 세그멘테이션 및 진행 예측 (nnU-Net 기반)
- **AI 예측 (캐시카우 #3):** AD/MCI 위험 분류 모델 통합 (SHAP 해석 포함)
- **종단적 분석:** 위축 진행 예측 모델 (MONAI 기반 자체 학습)
- **연결체:** dMRI 기반 구조적 연결체 생성 (Connectome Mapper 3)
- **규범 모델링:** BrainStat 기반 개인-인구 비교 프레임워크
- **XAI:** SHAP 기반 결과 해석 모듈 — 모든 AI 예측에 근거 시각화 제공
- **SaaS 상용화:** 멀티테넌트 인프라, 과금 체계, 사용자 관리

### Phase 3: 다중 모달리티 확장 및 시뮬레이션 기초 (6개월)
- **뇌 시뮬레이션 (SaaS):** TVB를 서버사이드 SaaS로 연동 (GPL 격리)
- **장-뇌 축:** MIMIC 기반 장내 미생물 모델링 연동
- **다중 오믹스:** 유전체/영상 통합 분석 프레임워크
- **가상 코호트:** 합성 데이터 기반 Virtual Cohort 생성 기능
- **종단적 대시보드:** 시계열 형태 변화 추적 시각화

### Phase 4: 자체 기술 자산 구축 및 차별화 (6개월)
- **자체 파운데이션 모델:** UK Biobank 50,000+ T1 MRI 기반 ViT/MAE 구조적 MRI 파운데이션 모델 학습 (선점 기회)
- **자체 시뮬레이터 (R&D):** JAX/PyTorch 기반 미분가능 뇌 시뮬레이터 연구 착수 (Wilson-Cowan, Jansen-Rit 모델)
- **온프레미스 패키지:** GPL-free 스택만으로 구성된 설치형 배포판
- **API 공개:** 써드파티 통합 지원, 플러그인 생태계

### Phase 5: 고도화 및 확장 (이후)
- 자체 JAX 시뮬레이터 완성 및 TVB 완전 대체
- (선택적) Unity 기반 VR 몰입형 뇌 탐색 모듈
- DKT 활용 희귀 퇴행성 뇌질환 시뮬레이터
- 연합 학습(Federated Learning) 기반 다기관 공동 모델 학습
- 글로벌 시장 진출

---

## 9. 인프라 및 비용 전략

> **전문가 조언 반영:** UK Biobank 50,000명 이상의 3D MRI 데이터는 PB 단위 스토리지와 대규모 GPU 연산을 요구합니다. 초기부터 비용 헤징 전략이 필수입니다.

### 9.1 데이터 스토리지 전략

| 전략 | 설명 | 적용 시점 |
| :--- | :--- | :--- |
| **S3 호환 오브젝트 스토리지 티어링** | Hot(활성 분석 데이터) / Warm(최근 결과) / Cold(원본 아카이브) 3-tier 구성 | Phase 1~ |
| **온디맨드 다운로드** | 전체 데이터를 미리 다운로드하지 않고, 분석 요청 시 필요 데이터만 스트리밍 | Phase 1~ |
| **전처리 결과 캐싱** | Raw MRI가 아닌 전처리 완료된 특성(피질 두께, 부피 등) 테이블만 상시 유지 | Phase 1~ |
| **데이터 레이크 구축** | Delta Lake / Apache Iceberg 기반 버전 관리 가능한 데이터 레이크 | Phase 2~ |

### 9.2 컴퓨팅 비용 헤징

| 전략 | 설명 |
| :--- | :--- |
| **KISTI 초고성능컴퓨팅(HPC) 지원사업** | 국내 연구기관 대상 무상/저가 GPU 클러스터 지원. 대규모 모델 학습에 활용 |
| **클라우드 스팟/프리엠티블 인스턴스** | AWS Spot, GCP Preemptible로 GPU 비용 60-80% 절감 (배치 전처리용) |
| **GPU 타임셰어링** | Kubernetes + NVIDIA MIG/MPS로 단일 GPU를 다수 사용자가 공유 |
| **경량 추론 최적화** | ONNX Runtime, TensorRT로 추론 시 GPU 메모리/시간 절감 |
| **정부 R&D 과제 연계** | IITP, NRF 등 정부 과제를 통한 초기 인프라 구축비 확보 |

### 9.3 예상 인프라 규모 (Phase 1 MVP 기준)

| 구성요소 | 사양 | 월 예상 비용 (클라우드) |
| :--- | :--- | :--- |
| GPU 노드 (추론/전처리) | A100 40GB x 1-2 | ~$3,000-6,000 |
| CPU 노드 (API/웹) | 8vCPU, 32GB x 2-3 | ~$500-1,000 |
| 오브젝트 스토리지 | 10-50 TB (Hot+Warm) | ~$200-500 |
| 데이터베이스 | PostgreSQL (관리형) | ~$200 |
| 기타 (네트워크, 로드밸런서 등) | - | ~$300 |
| **합계 (MVP)** | | **~$4,200-8,000/월** |

---

## 10. 개발 간 주요 고려사항

1. **라이선스 추적 의무화:** 모든 의존성 라이브러리의 라이선스를 SBOM(Software Bill of Materials)으로 관리. GPL 오염 여부를 CI/CD에서 자동 검증.
2. **공개 데이터 저작권 추적:** 160여 종 공개 데이터의 사용 규약(어트리뷰션, 비영리 등)을 연구자에게 자동 안내하고 사전 동의를 받는 프로세스 반영.
3. **데이터 이질성 해소:** BIDS 포맷 자동 변환, SynthSeg의 대조도 무관 세그멘테이션으로 다양한 스캐너/프로토콜의 MRI 데이터를 일관되게 처리.
4. **연산 지연 돌파:** FastSurfer(1분 이내 세그멘테이션), GPU 가속 시뮬레이터 등으로 실시간에 가까운 분석 속도 달성. Kubernetes 기반 HPC 호환성 설계.
5. **설명 가능한 AI (XAI) 필수:** 질환 예측/위험도 분석 결과에 SHAP 등을 통해 근거를 제시하여 연구자 신뢰 확보.
6. **비용 효율 설계:** 초기부터 S3 티어링, 스팟 인스턴스, GPU 타임셰어링 등을 적용하여 PB 규모 데이터 처리의 인프라 비용을 통제.

---

## 10. 공개 데이터셋 (구조적 MRI)

| 데이터셋 | 피험자 수 | MRI 종류 | 특징 |
| :--- | :--- | :--- | :--- |
| UK Biobank | 50,000+ | T1, T2/FLAIR, dMRI | 최대 규모, 종단 추적 |
| ADNI | 2,000+ | T1, dMRI, PET | AD 특화, 종단 |
| HCP | 1,200 | T1, T2, dMRI | 고해상도, 건강인 |
| ABCD | 11,000+ | T1, dMRI, fMRI | 청소년 발달 |
| dHCP | 800+ | T1, T2, dMRI | 신생아/영아 |
| OASIS-3 | 1,098 | T1, dMRI | AD/노화, 종단 |
| IXI | 600 | T1, T2, dMRI | 건강인, 다기관 |
| CamCAN | 700 | T1, T2, dMRI | 전 연령대 노화 |
