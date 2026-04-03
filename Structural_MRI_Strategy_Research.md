# Synapse-D: 구조적 MRI 기반 상용 브레인 디지털 트윈 전략 조사 보고서

> 조사일: 2026-04-03  
> 목적: TRIBE v2 (CC BY-NC) 대체 및 상업적 판매 가능한 구조적 MRI 기반 플랫폼 구축 전략

---

## 1. 왜 구조적 MRI가 뇌 발달/퇴화 예측에 더 적합한가

### 1.1 TRIBE v2 (fMRI 기반)의 한계

| 항목 | TRIBE v2 (fMRI) | 구조적 MRI 접근 |
|:---|:---|:---|
| **라이선스** | CC BY-NC 4.0 (상용 불가) | 다수 도구가 Apache/MIT/BSD |
| **데이터 요구** | task-fMRI (자극 실험 필요) | T1/T2 MRI (표준 임상 촬영) |
| **임상 가용성** | fMRI는 연구 세팅에서만 일반적 | T1 MRI는 모든 병원에서 촬영 |
| **재현성** | fMRI BOLD 신호는 변동성 높음 | 구조적 측정은 재현성 높음 |
| **용도** | 자극 반응 예측 (연구 특화) | 발달/퇴화 바이오마커 (임상 적용 가능) |
| **데이터 규모** | 학습에 700명 1,000시간 fMRI | UK Biobank만 50,000+ 구조적 MRI |

### 1.2 구조적 MRI 모달리티별 역할

#### T1-weighted MRI
- **피질 두께 (Cortical Thickness)**: 발달 단계 추적, 알츠하이머 초기 지표
- **회백질 부피 (Gray Matter Volume)**: VBM 분석, 노화/퇴행 정량화
- **뇌 형태계측 (Brain Morphometry)**: 뇌실 확장, 해마 위축 등
- **Brain Age 예측**: 생물학적 나이 vs 실제 나이 차이 = 뇌 건강 바이오마커
- **표면 기반 분석**: 주름(sulci), 이랑(gyri) 패턴 = 발달 지표

#### T2/FLAIR MRI
- **백질 고신호 병변 (WMH)**: 소혈관 질환, 치매 위험 지표
- **병변 탐지**: 다발성 경화증, 외상성 뇌손상
- **병리적 변화 추적**: 종단적 WMH 진행 = 혈관성 치매 예측
- **수초화(Myelination) 매핑**: 영유아 발달 추적

#### dMRI (확산 MRI)
- **백질 신경로 추적 (Tractography)**: 구조적 연결체(Structural Connectome) 생성
- **FA/MD 지표**: 백질 무결성 정량화
- **TVB 입력**: 뇌 네트워크 시뮬레이션의 핵심 연결 행렬
- **발달 추적**: 수초화 진행 패턴 모니터링

### 1.3 발달/퇴화 바이오마커 매핑

| 생애 단계 | 핵심 구조적 바이오마커 | MRI 모달리티 | 예측 대상 |
|:---|:---|:---|:---|
| 영유아 (0-2세) | 전체 뇌 부피, 수초화 패턴 | T1, T2 | 발달 지연, ASD 위험 |
| 아동-청소년 | 피질 두께, 백질 성숙 | T1, dMRI | 인지 발달 궤적, ADHD |
| 청년-중년 | Brain Age Gap, WMH 발생 | T1, FLAIR | 조기 노화, 치매 위험 |
| 노년 | 해마 위축, WMH 진행, 뇌실 확장 | T1, T2/FLAIR | AD 진행, 혈관성 치매 |

---

## 2. 구조적 MRI 분석 도구 라이선스 종합표

### 2.1 상용 가능 도구 (MIT / Apache 2.0 / BSD)

| 도구명 | 기능 | 라이선스 | 상용 가능 | 비고 |
|:---|:---|:---|:---|:---|
| **FastSurfer** | FreeSurfer 대체 DL 세그멘테이션 | **Apache 2.0** | **가능** | FreeSurfer 대비 100배 빠름, 피질두께/부피 측정 |
| **SynthSeg** | 대조도 무관 뇌 세그멘테이션 | **Apache 2.0** | **가능** | 어떤 MRI 대조도에서도 작동, FreeSurfer 팀 개발 |
| **ANTs** | 이미지 정합(Registration), 형태계측 | **Apache 2.0** | **가능** | 업계 표준 비선형 정합 |
| **HD-BET** | 뇌 추출 (Brain Extraction) | **Apache 2.0** | **가능** | T1/T2/FLAIR 모두 지원, DL 기반 |
| **nnU-Net** | 범용 의료영상 세그멘테이션 | **Apache 2.0** | **가능** | 자동 설정, WMH 세그멘테이션에 활용 가능 |
| **MONAI** | 의료영상 DL 프레임워크 | **Apache 2.0** | **가능** | PyTorch 기반, NVIDIA 지원 |
| **Nobrainer** | 3D 뇌영상 DL (세그멘테이션/생성) | **Apache 2.0** | **가능** | TensorFlow 기반, 뇌 추출/세그멘테이션 |
| **Nilearn** | 뇌영상 통계 분석/시각화 | **BSD-3** | **가능** | Python scikit-learn 기반 |
| **BrainStat** | 뇌영상 통계 분석/컨텍스트 디코딩 | **BSD-3** | **가능** | 표면/부피/파셀 지원 |
| **Clinica** | 신경영상 임상연구 파이프라인 | **MIT** | **가능** | BIDS 표준, FreeSurfer/ANTs/FSL 통합 |
| **NiMARE** | 신경영상 메타분석 | **MIT** | **가능** | 좌표/영상 기반 메타분석 |
| **Connectome Mapper 3** | 다중모달 연결체 생성 | **BSD-3** | **가능** | T1+dMRI+fMRI 통합 파이프라인 |
| **SFCN (UK Biobank)** | Brain Age 예측 DL 모델 | **MIT** | **가능** | 12,000+ 샘플 학습, 경량 CNN |
| **AD 진단 프레임워크 (vkola-lab)** | MRI 기반 AD/MCI 분류 | **MIT** | **가능** | Nature Communications 2022, SHAP 해석 |
| **BrainScape** | 공개 MRI 데이터 통합/전처리 | **MIT** | **가능** | 160+ 데이터셋 자동 다운로드 |

### 2.2 제한적 사용 도구 (LGPL / GPL / 커스텀)

| 도구명 | 기능 | 라이선스 | 상용 제한 사항 |
|:---|:---|:---|:---|
| **FreeSurfer** | 피질 재건, 세그멘테이션 (골드 스탠다드) | **커스텀 라이선스** | 상용 가능하나 "연구 목적 설계" 명시, 법무 검토 필요 |
| **FSL** | 뇌영상 분석 종합 도구 | **커스텀 (비상용)** | **비상용 무료, 상용시 별도 라이선스 필요** |
| **CAT12/SPM** | VBM, 피질두께, 표면재건 | **GPL v2+** | 파생물 GPL 공개 의무, 코드 공개 필요 |
| **TVB** | 뇌 네트워크 시뮬레이션 | **GPL v3** | **파생물 전체 코드 공개 의무** |
| **brainageR** | Brain Age 예측 (GPR) | **LGPL v3** | 라이브러리 사용 가능, 수정 시 공개 의무 |
| **micapipe** | 다중모달 연결체 파이프라인 | **GPL v3** | 파생물 GPL 공개 의무 |
| **NiChart (CBICA)** | 뇌 차트/규범 모델링 | **비상용 라이선스** | **상용 불가** |
| **SLANT** | 133 영역 전뇌 세그멘테이션 | **비상용 무료** | **상용시 별도 라이선스 필요** |
| **TRIBE v2** | fMRI BOLD 반응 예측 | **CC BY-NC 4.0** | **상용 절대 불가** |

### 2.3 핵심 권장 스택 (상용 가능)

```
[입력: T1/T2/FLAIR/dMRI]
    |
    v
[전처리] HD-BET (뇌추출) + ANTs (정합/정규화)
    |
    v
[세그멘테이션] FastSurfer (피질/피질하) + SynthSeg (대조도 무관)
    |           + nnU-Net (WMH 세그멘테이션)
    v
[형태계측] ANTs (VBM/DBM) + FastSurfer (피질두께/부피)
    |
    v
[AI 예측] SFCN (Brain Age) + MONAI/nnU-Net (커스텀 모델)
    |       + 자체 학습 모델 (위축 진행, WMH 진행)
    v
[연결체] Connectome Mapper 3 (dMRI 트랙토그래피)
    |
    v
[시각화/분석] Nilearn + BrainStat
    |
    v
[시뮬레이션] 자체 네트워크 시뮬레이터 (TVB 대체)
```

---

## 3. AI/ML 모델: 허용적 라이선스 기반

### 3.1 Brain Age 예측 모델

| 모델 | 학습 데이터 | 성능 | 라이선스 | 상용 가능 |
|:---|:---|:---|:---|:---|
| **SFCN (UK Biobank pretrain)** | 12,000+ T1 MRI | MAE ~2.14년 | **MIT** | **가능** |
| **brainageR** | 3,377 T1 MRI | MAE ~3.9년 | LGPL v3 | 조건부 (수정 공개) |
| **DeepBrainNet** | 11,729 다양한 MRI | 여러 스캐너 강건 | 미명시 | 확인 필요 |
| **자체 학습 (MONAI 기반)** | UK Biobank/ADNI | 커스터마이즈 가능 | Apache 2.0 | **가능** |

### 3.2 세그멘테이션/형태계측 DL 모델

| 모델 | 기능 | 라이선스 | 상용 가능 |
|:---|:---|:---|:---|
| **FastSurfer** | 전뇌 세그멘테이션 (1분 이내) | Apache 2.0 | **가능** |
| **SynthSeg** | 대조도 무관 세그멘테이션 | Apache 2.0 | **가능** |
| **nnU-Net** | WMH/병변 세그멘테이션 (학습 필요) | Apache 2.0 | **가능** |
| **Nobrainer** | 뇌 추출/세그멘테이션 | Apache 2.0 | **가능** |
| **HD-BET** | 뇌 추출 (모든 MRI 대조도) | Apache 2.0 | **가능** |

### 3.3 질병 예측 / 진행 모델

| 모델 | 기능 | 라이선스 | 상용 가능 |
|:---|:---|:---|:---|
| **AD 진단 (vkola-lab, Nature Comms)** | MRI 기반 AD/MCI/NC 분류, SHAP 해석 | **MIT** | **가능** |
| **DKT** | 희귀 퇴행성 질환 궤적 전이학습 | 커스텀 | 원저작자 확인 필요 |
| **MONAI + 자체 모델** | 위축 진행 예측, WMH 진행 | Apache 2.0 | **가능** |

### 3.4 구조적 MRI 파운데이션 모델 현황 (2026년 4월 기준)

**현재 상황**: fMRI 기반 TRIBE v2와 같은 대규모 구조적 MRI 파운데이션 모델은 아직 공개되지 않았음.

**그러나 대안이 존재:**
1. **MONAI + Self-supervised Learning**: MONAI 프레임워크에서 자기지도 사전학습(MAE, contrastive learning) 가능
2. **SFCN 사전학습 모델**: UK Biobank 12,000+ 데이터로 학습된 모델을 전이학습 기반으로 활용
3. **nnU-Net 자동 적응**: 데이터셋에 자동 적응하는 세그멘테이션 → 파운데이션 모델적 범용성
4. **SynthSeg의 대조도 무관성**: 합성 데이터로 학습하여 어떤 MRI에서든 작동 → 일종의 "파운데이션 세그멘테이션"
5. **자체 파운데이션 모델 학습**: UK Biobank (50,000+), ADNI, HCP, ABCD 등의 공개 T1 데이터로 MAE/ViT 기반 자체 모델 사전학습 가능

---

## 4. TRIBE v2 역할 대체 전략

### 4.1 TRIBE v2가 하는 것
- fMRI BOLD 반응을 자극(시각/청각/언어)에 대해 제로샷 예측
- 70,000+ 복셀 수준 해상도
- 연구 특화: "가상 fMRI 실험" 가속화

### 4.2 구조적 MRI 플랫폼에 실제로 필요한 AI 역량

**TRIBE v2는 대체할 필요가 없다** -- 플랫폼의 핵심 가치를 재정의해야 한다.

| TRIBE v2 역할 | 구조적 MRI 대체 역량 | 구현 방법 |
|:---|:---|:---|
| 자극 반응 예측 | **Brain Age 예측** | SFCN (MIT) + 자체 모델 |
| 제로샷 뇌 활동 예측 | **형태학적 이상 탐지** | FastSurfer + 규범 모델링 |
| 가상 fMRI 실험 | **종단적 위축 시뮬레이션** | 자체 위축 진행 모델 |
| 개인화된 뇌 모델 | **개인화된 뇌 형태 프로파일** | FastSurfer + ANTs + Brain Age |
| 뇌 반응 예측 | **질병 진행 궤적 예측** | DKT + 자체 진행 모델 |

### 4.3 플랫폼 재포지셔닝

**기존 (TRIBE v2 의존):**
> "자극에 대한 뇌 반응을 예측하는 인실리코 실험 플랫폼"

**새로운 (구조적 MRI 중심):**
> "구조적 MRI 기반 뇌 발달/퇴화 궤적 예측 및 디지털 트윈 플랫폼"

핵심 가치 제안:
1. **Brain Age Gap 분석**: 개인의 뇌 나이 갭 → 뇌 건강 상태 정량화
2. **종단적 형태 변화 예측**: 현재 MRI에서 미래 뇌 구조 변화 예측
3. **WMH 진행 예측**: 백질 병변 부담 → 혈관성 치매 위험
4. **규범 모델링**: 개인 뇌를 인구 기반 규범과 비교
5. **가상 코호트 생성**: 합성 뇌 MRI 데이터로 가상 임상시험

---

## 5. TVB와 구조적 MRI 통합 및 GPLv3 문제 해결

### 5.1 TVB의 구조적 MRI 파이프라인

TVB는 이미 구조적 MRI에 크게 의존:
- **T1 MRI** → 뇌 파셀레이션 (Desikan-Killiany, Destrieux 등)
- **dMRI** → 구조적 연결체 (Structural Connectivity Matrix)
- **연결 행렬 + 신경질량모델** → 뇌 활동 시뮬레이션

```
T1 MRI → FreeSurfer/FastSurfer → 뇌 영역 분할
                                        ↓
dMRI → MRtrix3/FSL → 트랙토그래피 → 연결 행렬
                                        ↓
                              TVB → 뇌 네트워크 시뮬레이션
```

### 5.2 TVB GPLv3 문제: 세 가지 해결 전략

#### 전략 A: SaaS 모델 (서버 사이드 실행)
- TVB를 서버에서만 실행하고 결과만 API로 전달
- GPLv3는 "배포(distribution)"에 적용 → SaaS는 배포가 아님
- **단, AGPL과 혼동 금지**: TVB는 GPLv3이므로 SaaS 사용 가능
- **위험도**: 낮음 (법적으로 가장 안전한 방법)

```
[클라이언트 앱] ←API→ [Synapse-D 서버] ←내부호출→ [TVB 서버]
   (독점 코드)         (독점 코드)              (GPLv3)
   배포됨              배포 안 됨               배포 안 됨
```

#### 전략 B: TVB 완전 대체 (자체 시뮬레이터 개발)
- 신경질량모델(Neural Mass Model)은 수학 공식이므로 특허/저작권 없음
- Wilson-Cowan, Jansen-Rit, Kuramoto 등의 모델은 학술 문헌에 공개
- 연결 행렬 입력 → 미분방정식 시뮬레이션은 독자 구현 가능
- **필요 개발**: Python/C++ 미분방정식 솔버 + 연결 행렬 로더
- **위험도**: 중간 (개발 비용은 있지만 완전한 자유)

```python
# TVB 없이 구현 가능한 간단한 Neural Mass Model 예시
# Wilson-Cowan 모델: dE/dt = -E + S(c1*E - c2*I + P)
# 이것은 수학 공식이므로 GPL과 무관
import numpy as np
from scipy.integrate import solve_ivp

def wilson_cowan(t, y, connectivity, params):
    n_regions = len(connectivity)
    E = y[:n_regions]
    I = y[n_regions:]
    # ... 미분방정식 구현
    return dydt
```

#### 전략 C: 하이브리드 접근 (권장)
1. **Phase 1**: TVB를 SaaS로 사용 (즉시 시작 가능)
2. **Phase 2**: 핵심 시뮬레이션 기능을 자체 구현으로 점진적 대체
3. **Phase 3**: TVB 완전 제거, 자체 시뮬레이터로 전환

### 5.3 TVB 대체 가능한 상용 친화적 도구

| 도구/접근 | 기능 | 라이선스 | 설명 |
|:---|:---|:---|:---|
| **자체 구현 (NumPy/SciPy)** | 신경질량모델 시뮬레이션 | 자체 소유 | Wilson-Cowan, Kuramoto 등 수학 모델 직접 구현 |
| **Brian2** | 스파이킹 뉴런 시뮬레이터 | CeCILL v2 (GPL 호환) | GPL 호환이므로 주의 필요 |
| **NEST** | 대규모 SNN 시뮬레이터 | GPL v2+ | 상용 제한 |
| **NetPyNE** | 네트워크 시뮬레이션 | MIT | **상용 가능**, 다만 NEURON 의존 |
| **JAX 기반 자체 시뮬레이터** | 미분가능 뇌 시뮬레이션 | 자체 소유 | GPU 가속, 역전파 가능 → AI 통합 최적 |

**최적 권장**: JAX/PyTorch 기반 자체 미분가능(differentiable) 뇌 시뮬레이터 개발
- 수학적 모델은 공개 문헌에서 가져옴 (저작권 무관)
- GPU 가속으로 TVB보다 빠름
- 역전파 가능 → 관측 데이터에 파라미터 피팅 가능
- 완전한 상업적 자유

---

## 6. 상용 플랫폼 아키텍처 권장안

### 6.1 라이선스 안전 아키텍처

```
================================================================
              Synapse-D 상용 플랫폼 아키텍처
================================================================

[Layer 1: 데이터 입력]
  T1 MRI, T2/FLAIR, dMRI
  BIDS 포맷 표준화
  
[Layer 2: 전처리 파이프라인] ← 모두 Apache 2.0 / BSD
  HD-BET (뇌 추출, Apache 2.0)
  ANTs (정합/정규화, Apache 2.0)
  FastSurfer (세그멘테이션, Apache 2.0)
  SynthSeg (범용 세그멘테이션, Apache 2.0)
  nnU-Net (WMH 세그멘테이션, Apache 2.0)
  
[Layer 3: 형태계측 분석] ← 모두 Apache 2.0 / BSD / MIT
  ANTs (VBM/DBM, Apache 2.0)
  FastSurfer (피질두께/부피, Apache 2.0)
  Nilearn (통계분석, BSD-3)
  BrainStat (규범 모델링, BSD-3)
  Connectome Mapper 3 (연결체, BSD-3)

[Layer 4: AI 예측 엔진] ← 모두 MIT / Apache 2.0
  SFCN Brain Age (MIT)
  자체 위축 진행 모델 (MONAI 기반, Apache 2.0)
  자체 WMH 진행 모델 (nnU-Net 기반, Apache 2.0)
  AD 위험 분류 모델 (MIT)
  
[Layer 5: 뇌 시뮬레이션]
  옵션 A: TVB (GPLv3) → SaaS 모드로 서버에서만 실행
  옵션 B: 자체 JAX 기반 시뮬레이터 (독점)
  
[Layer 6: 시각화/서비스]
  3D 뇌 시각화 (Three.js / VTK.js, MIT/BSD)
  대시보드 (React/Next.js, MIT)
  연구 워크스페이스 (독점)
================================================================
```

### 6.2 GPL 오염 방지 규칙

| 규칙 | 설명 |
|:---|:---|
| **절대 금지** | GPL 코드를 플랫폼 코드에 직접 임포트/링크 |
| **허용 (SaaS)** | GPL 도구를 별도 프로세스/컨테이너에서 실행, API로 결과만 수신 |
| **허용 (도구)** | GPL 도구를 CLI 명령으로 호출 (시스템 라이브러리 예외 적용) |
| **권장** | 모든 핵심 코드는 Apache 2.0/MIT/BSD 도구로만 구성 |
| **법무 검토** | FreeSurfer 커스텀 라이선스 → FastSurfer(Apache 2.0)로 대체 권장 |

---

## 7. 실행 로드맵 (수정안)

### Phase 1: 핵심 파이프라인 구축 (6개월)
- [ ] HD-BET + ANTs + FastSurfer 기반 전처리 파이프라인
- [ ] Brain Age 예측 모델 (SFCN MIT 모델 통합)
- [ ] 피질두께/부피 자동 추출 및 규범 비교
- [ ] BIDS 데이터 관리 인프라
- [ ] 기본 3D 시각화

### Phase 2: 예측 모델 강화 (6개월)
- [ ] WMH 세그멘테이션 및 진행 예측 (nnU-Net)
- [ ] 종단적 위축 진행 모델 (MONAI 기반 자체 학습)
- [ ] AD/MCI 위험 분류 모델 통합
- [ ] dMRI 기반 연결체 생성 (Connectome Mapper 3)
- [ ] 규범 모델링 프레임워크

### Phase 3: 시뮬레이션 및 고도화 (6개월)
- [ ] TVB SaaS 연동 또는 자체 시뮬레이터 개발
- [ ] 다중 오믹스 통합 (MIMIC, Scbean)
- [ ] 가상 코호트 생성 기능
- [ ] XAI (SHAP) 기반 결과 해석 모듈
- [ ] 종단적 추적 대시보드

---

## 8. 최종 권장사항

### 8.1 전략적 판단

1. **TRIBE v2는 포기하라**: CC BY-NC는 상용 불가. 구조적 MRI 중심으로 플랫폼을 재정의하면 TRIBE v2 없이도 더 강력한 임상 가치를 제공할 수 있다.

2. **FreeSurfer → FastSurfer로 교체**: FreeSurfer의 커스텀 라이선스보다 FastSurfer의 Apache 2.0이 상용 제품에 더 안전하다. FastSurfer는 FreeSurfer와 동일한 출력을 생성하면서 100배 빠르다.

3. **FSL 의존 최소화**: FSL은 상용 라이선스가 필요하므로, ANTs(Apache 2.0)와 MRtrix3(Mozilla Public License)로 대체 가능한 기능은 대체하라.

4. **TVB는 SaaS로 시작 → 자체 대체 추진**: 초기에는 TVB를 서버 사이드에서 실행하되, 중장기적으로 JAX 기반 자체 시뮬레이터를 개발하라.

5. **자체 파운데이션 모델 학습 검토**: UK Biobank 50,000+ T1 MRI로 ViT/MAE 기반 구조적 MRI 파운데이션 모델을 자체 학습하면, TRIBE v2를 능가하는 차별화 자산이 된다.

### 8.2 경쟁 우위

| 기존 TRIBE v2 계획 | 새로운 구조적 MRI 전략 |
|:---|:---|
| 연구용만 가능 | **상용 판매 가능** |
| fMRI 필요 (특수 시설) | T1/T2 MRI (모든 병원) |
| 자극 반응 예측 (좁은 용도) | 발달/퇴화 예측 (넓은 시장) |
| Meta 라이선스 의존 | 자체 기술 소유 |
| 연구자만 타겟 | 연구자 + 임상의 + 제약사 |

### 8.3 라이선스 리스크 요약

| 리스크 수준 | 도구 | 대응 |
|:---|:---|:---|
| **위험 없음** | ANTs, FastSurfer, SynthSeg, HD-BET, nnU-Net, MONAI, Nilearn, SFCN | 그대로 사용 |
| **낮은 위험** | FreeSurfer (커스텀), brainageR (LGPL) | FastSurfer로 대체, LGPL 조건 준수 |
| **중간 위험** | TVB (GPLv3) | SaaS 모드 또는 자체 대체 |
| **높은 위험** | CAT12 (GPL), FSL (상용 유료), micapipe (GPL) | Apache/MIT 대안으로 교체 |
| **사용 불가** | TRIBE v2 (CC BY-NC), NiChart (비상용) | 사용 금지 |

---

## 부록: 주요 공개 데이터셋 (구조적 MRI)

| 데이터셋 | 피험자 수 | MRI 종류 | 특징 |
|:---|:---|:---|:---|
| UK Biobank | 50,000+ | T1, T2/FLAIR, dMRI | 최대 규모, 종단 추적 |
| ADNI | 2,000+ | T1, dMRI, PET | AD 특화, 종단 |
| HCP | 1,200 | T1, T2, dMRI | 고해상도, 건강인 |
| ABCD | 11,000+ | T1, dMRI, fMRI | 청소년 발달 |
| dHCP | 800+ | T1, T2, dMRI | 신생아/영아 |
| OASIS-3 | 1,098 | T1, dMRI | AD/노화, 종단 |
| IXI | 600 | T1, T2, dMRI | 건강인, 다기관 |
| CamCAN | 700 | T1, T2, dMRI | 전 연령대 노화 |
