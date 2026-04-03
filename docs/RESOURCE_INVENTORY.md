# Synapse-D 리소스 인벤토리
> 최종 업데이트: 2026-04-03

## 1. 오픈소스 소프트웨어 현황

### Layer 2: 전처리 파이프라인 (전체 Apache 2.0)

| 도구 | 버전/커밋 | 라이선스 | 기능 | 크기 | 상태 |
|:---|:---|:---|:---|:---|:---|
| **HD-BET** | latest | Apache 2.0 | 뇌 추출 (Brain Extraction) | 176K | 확보 완료 |
| **ANTsPy** | latest | Apache 2.0 | 공간 정합/정규화 (Registration) | 16M | 확보 완료 |
| **FastSurfer** | latest | Apache 2.0 | 피질/피질하 세그멘테이션 (FreeSurfer 대체) | 36M | 확보 완료 |
| **SynthSeg** | latest | Apache 2.0 | 대조도 무관 범용 세그멘테이션 | 168M | 확보 완료 |
| **nnU-Net** | latest | Apache 2.0 | WMH/병변 세그멘테이션 | 11M | 확보 완료 |

> 경로: `vendor/layer2-preprocessing/`

### Layer 3: 형태계측 분석

| 도구 | 버전/커밋 | 라이선스 | 기능 | 크기 | 상태 |
|:---|:---|:---|:---|:---|:---|
| **Nilearn** | latest | BSD-3 | 뇌영상 통계 분석/시각화 | 91M | 확보 완료 |
| **BrainStat** | latest | BSD-3 | 규범 모델링/통계 분석 | 100M | 확보 완료 |
| **Connectome Mapper 3** | latest | BSD-3 | 다중모달 연결체 생성 | 667M | 확보 완료 |

> 경로: `vendor/layer3-morphometry/`

### Layer 4: AI 예측 엔진

| 도구 | 버전/커밋 | 라이선스 | 기능 | 크기 | 상태 |
|:---|:---|:---|:---|:---|:---|
| **SFCN-BrainAge** | latest | MIT | Brain Age 예측 (사전학습 모델 포함) | 45M | 확보 완료 |
| **AD-Diagnosis** | latest | MIT | AD/MCI 위험 분류 (SHAP 해석) | 754M | 확보 완료 |
| **MONAI** | latest | Apache 2.0 | 의료영상 DL 프레임워크 | 46M | 확보 완료 |
| **Nobrainer** | latest | Apache 2.0 | 3D 뇌영상 DL (세그멘테이션/생성) | 1.8M | 확보 완료 |

> 경로: `vendor/layer4-ai-prediction/`

### 데이터 통합 도구

| 도구 | 버전/커밋 | 라이선스 | 기능 | 크기 | 상태 |
|:---|:---|:---|:---|:---|:---|
| **BrainScape** | latest | MIT | 공개 MRI 데이터 통합/전처리 (160+ 데이터셋) | 20M | 확보 완료 |
| **MIMIC** | latest | MIT | 장내 미생물 군집 모델링 (gLV/베이지안) | 48M | 확보 완료 |
| **Scbean** | latest | MIT | 단일 세포 다중 오믹스 분석 | 11M | 확보 완료 |
| **Clinica** | latest | MIT | 신경영상 임상연구 파이프라인 (BIDS) | 14M | 확보 완료 |

> 경로: `vendor/data-integration/`

---

## 2. 라이선스 요약

| 라이선스 | 도구 수 | 상용 판매 | 비고 |
|:---|:---|:---|:---|
| **Apache 2.0** | 8개 | 가능 | 전처리 파이프라인 전체 + MONAI + Nobrainer |
| **MIT** | 5개 | 가능 | SFCN, AD진단, BrainScape, MIMIC, Scbean, Clinica |
| **BSD-3** | 3개 | 가능 | Nilearn, BrainStat, Connectome Mapper 3 |

**GPL/CC-NC 도구: 0개** — 전체 스택이 상용 판매 가능

---

## 3. 샘플 데이터 현황

### 확보 완료 (개발/테스트용)

| 파일 | 출처 | 모달리티 | 크기 | 라이선스 |
|:---|:---|:---|:---|:---|
| `sub-pixar001/anat/sub-pixar001_T1w.nii.gz` | OpenNeuro ds000228 | T1w | 7.2MB | CC0 |
| `sub-01/anat/sub-01_T1w.nii.gz` | OpenNeuro ds000101 | T1w | 11MB | CC0 |

> 경로: `data/sample/` (BIDS 구조)
> 총 크기: ~18MB

### 추가 확보 가능 (자유 다운로드)

| 데이터셋 | 피험자 수 | 모달리티 | 접근 방법 | 비용 |
|:---|:---|:---|:---|:---|
| OpenNeuro (다수) | 다양 | T1/T2/dMRI | 즉시 다운로드 | 무료 |
| IXI | ~600 | T1/T2/dMRI | 즉시 다운로드 (tar) | 무료 |
| OASIS-1/3 | 416/1,098 | T1/T2/FLAIR | DUA 동의 후 1-2일 | 무료 |

### 신청 필요 (대규모 학습용)

| 데이터셋 | 피험자 수 | 모달리티 | 소요 시간 | 비용 |
|:---|:---|:---|:---|:---|
| **UK Biobank** | 50,000+ | T1/T2/FLAIR/dMRI | 2-6개월 | £2,000-5,000 |
| **ADNI** | 2,000+ | T1/T2/FLAIR/dMRI/PET | 1-4주 | 무료 |
| **HCP** | 1,200 | T1/T2/dMRI | 1-2주 | 무료 |
| **ABCD** | 11,000+ | T1/T2/dMRI | 2-4주 | 무료 |
| **dHCP** | 800+ | T1/T2/dMRI | 1-3주 | 무료 |

> 상세 신청 절차: `data/DATA_ACCESS_GUIDE.md` 참조

---

## 4. 디렉터리 구조

```
Synapse-D/
├── docs/
│   └── RESOURCE_INVENTORY.md      ← 이 문서
├── data/
│   ├── sample/                     ← 개발/테스트용 샘플 MRI (BIDS)
│   │   ├── sub-01/anat/
│   │   ├── sub-pixar001/anat/
│   │   └── dataset_description.json
│   ├── raw/                        ← 원본 데이터 (향후)
│   ├── processed/                  ← 전처리 결과 (향후)
│   └── DATA_ACCESS_GUIDE.md       ← 데이터 접근 가이드 (한국어)
├── vendor/
│   ├── layer2-preprocessing/       ← 전처리 도구 (Apache 2.0)
│   │   ├── HD-BET/
│   │   ├── ANTsPy/
│   │   ├── FastSurfer/
│   │   ├── SynthSeg/
│   │   └── nnUNet/
│   ├── layer3-morphometry/         ← 형태계측 도구 (BSD-3)
│   │   ├── nilearn/
│   │   ├── BrainStat/
│   │   └── connectomemapper3/
│   ├── layer4-ai-prediction/       ← AI 예측 모델 (MIT/Apache 2.0)
│   │   ├── SFCN-BrainAge/
│   │   ├── AD-Diagnosis/
│   │   ├── MONAI/
│   │   └── nobrainer/
│   └── data-integration/           ← 데이터 통합 도구 (MIT)
│       ├── BrainScape/
│       ├── MIMIC/
│       ├── Scbean/
│       └── Clinica/
├── Brain_Digital Twin.md           ← 기술 보고서
├── Structural_MRI_Strategy_Research.md ← 구조적 MRI 전략 조사
└── 연구용_브레인_디지털_트윈_Platform_기획서.md ← 플랫폼 기획서
```

---

## 5. 사전학습 가중치 확인

| 모델 | 가중치 포함 여부 | 다운로드 필요 | 크기 추정 |
|:---|:---|:---|:---|
| **SFCN-BrainAge** | 리포에 포함 | 불필요 | ~30MB |
| **AD-Diagnosis** | 리포에 포함 | 불필요 | ~500MB |
| **FastSurfer** | 최초 실행 시 자동 다운로드 | 자동 | ~300MB |
| **SynthSeg** | 리포에 포함 | 불필요 | ~150MB |
| **HD-BET** | 최초 실행 시 자동 다운로드 | 자동 | ~50MB |
| **nnU-Net** | 학습 필요 (WMH 데이터로) | 별도 학습 | - |

---

*문서 작성일: 2026-04-03*
*Synapse-D 프로젝트 — Brain Digital Twin Platform*
