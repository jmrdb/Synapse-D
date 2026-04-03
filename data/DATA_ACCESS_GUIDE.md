# Brain Digital Twin 데이터 접근 가이드

## 목차
1. [자유 다운로드 가능 데이터셋](#1-자유-다운로드-가능-데이터셋)
2. [신청 필요 데이터셋](#2-신청-필요-데이터셋)
3. [요청해야 할 데이터 종류](#3-요청해야-할-데이터-종류)
4. [현재 샘플 데이터](#4-현재-샘플-데이터)

---

## 1. 자유 다운로드 가능 데이터셋

### OpenNeuro
- **URL**: https://openneuro.org
- **라이선스**: CC0 (대부분)
- **절차**: 회원가입 없이 즉시 다운로드 가능
- **형식**: BIDS (NIfTI)
- **추천 데이터셋**:
  - `ds000228` - Richardson et al., 소아/성인 T1w + fMRI
  - `ds000101` - Simon et al., 성인 T1w + fMRI
  - `ds000114` - 다중 세션 T1w/T2w/dMRI/fMRI
- **다운로드 방법**: `openneuro-cli` 또는 S3 직접 다운로드
  ```bash
  # S3 직접 다운로드 예시
  curl -L -o sub-01_T1w.nii.gz \
    "https://s3.amazonaws.com/openneuro.org/ds000101/sub-01/anat/sub-01_T1w.nii.gz"
  ```

### IXI Dataset
- **URL**: https://brain-development.org/ixi-dataset/
- **라이선스**: CC BY-SA 3.0
- **절차**: 즉시 다운로드 (전체 모달리티별 tar 아카이브)
- **형식**: NIfTI
- **데이터**: T1, T2, PD, MRA, dMRI (약 600명)
- **주의**: 개별 피험자 파일 다운로드 불가, 전체 모달리티 아카이브만 제공
  - T1 전체: ~1.3GB (`IXI-T1.tar`)

### OASIS (Open Access Series of Imaging Studies)
- **URL**: https://www.oasis-brains.org
- **라이선스**: 무료 (DUA 동의 필요)
- **절차**: 온라인 DUA 동의 후 즉시 다운로드 (1-2일)
- **데이터**:
  - OASIS-1: 횡단면 T1 (416명, 18-96세)
  - OASIS-3: 종단면 T1/T2/FLAIR/dMRI/fMRI (1,098명)
- **형식**: NIfTI

### FreeSurfer Sample Data (bert)
- **URL**: https://surfer.nmr.mgh.harvard.edu/fswiki/FsTutorial/Data
- **용도**: FreeSurfer/FastSurfer 파이프라인 테스트 전용
- **절차**: FreeSurfer 설치 시 포함 또는 별도 다운로드

---

## 2. 신청 필요 데이터셋

### UK Biobank
- **신청 URL**: https://www.ukbiobank.ac.uk/enable-your-research/apply-for-access
- **예상 소요 시간**: 2-6개월
- **절차**:
  1. 연구 제안서 제출 (Application Form)
  2. UK Biobank Access Committee 심사
  3. MTA (Material Transfer Agreement) 서명
  4. 접근 비용 지불 (약 £2,000-5,000, 데이터 규모에 따라)
- **규모**: ~50,000명 뇌 MRI
- **데이터**: T1, T2 FLAIR, dMRI (60방향), resting fMRI, task fMRI, SWI
- **특이사항**: 데이터는 UK Biobank 전용 플랫폼(RAP)에서 분석 권장

### ADNI (Alzheimer's Disease Neuroimaging Initiative)
- **신청 URL**: https://adni.loni.usc.edu/data-samples/access-data/
- **예상 소요 시간**: 1-4주
- **절차**:
  1. LONI IDA 계정 생성
  2. DUA (Data Use Agreement) 제출
  3. ADNI Data Access Committee 승인
- **규모**: ~2,000명 (종단면)
- **데이터**: T1, T2/FLAIR, dMRI, fMRI, PET (Amyloid, Tau)
- **비용**: 무료

### HCP (Human Connectome Project)
- **신청 URL**: https://db.humanconnectome.org (ConnectomeDB)
- **예상 소요 시간**: 1-2주
- **절차**:
  1. ConnectomeDB 계정 생성
  2. Open Access DUA 동의 (즉시)
  3. Restricted Access는 별도 신청 필요 (IRB 승인 필요)
- **규모**: ~1,200명 (Young Adult), ~1,500명 (Aging)
- **데이터**: T1, T2, dMRI (고해상도 270방향), resting fMRI, task fMRI
- **특이사항**: Open Access 데이터는 비교적 빠르게 접근 가능

### ABCD (Adolescent Brain Cognitive Development)
- **신청 URL**: https://nda.nih.gov/abcd
- **예상 소요 시간**: 2-4주
- **절차**:
  1. NDA (NIMH Data Archive) 계정 생성
  2. DUC (Data Use Certification) 제출
  3. 소속 기관 Signing Official 서명 필요
  4. NDA 승인
- **규모**: ~12,000명 (9-10세 아동, 종단면)
- **데이터**: T1, T2, dMRI, resting fMRI, task fMRI
- **비용**: 무료

### dHCP (Developing Human Connectome Project)
- **신청 URL**: https://www.developingconnectome.org/data-release/
- **예상 소요 시간**: 1-3주
- **절차**:
  1. 온라인 DUA 제출
  2. dHCP Data Access Committee 승인
- **규모**: ~800명 (태아 및 신생아)
- **데이터**: T1, T2, dMRI, resting fMRI
- **특이사항**: 태아/신생아 전용, 성인 데이터 없음

---

## 3. 요청해야 할 데이터 종류

Brain Digital Twin 파이프라인에 필요한 데이터 우선순위:

### 필수 (1순위)
| 모달리티 | 용도 | 파이프라인 단계 |
|---------|------|---------------|
| **T1-weighted** | 뇌 구조 분할, 피질 두께 측정 | HD-BET → ANTs → FastSurfer |
| **T2-weighted / FLAIR** | 백질 병변 검출, 피질 표면 정교화 | FastSurfer (선택적 입력) |

### 권장 (2순위)
| 모달리티 | 용도 | 파이프라인 단계 |
|---------|------|---------------|
| **dMRI (확산 MRI)** | 백질 섬유 추적, 구조적 연결성 | MRtrix3/Dipy → Connectome |
| **resting fMRI** | 기능적 연결성 | fMRIPrep → Nilearn |

### 선택 (3순위)
| 모달리티 | 용도 | 파이프라인 단계 |
|---------|------|---------------|
| **task fMRI** | 특정 인지 과제 활성화 맵 | fMRIPrep → Nilearn |
| **SWI** | 미세출혈, 철분 침착 | 별도 분석 |
| **PET** | 아밀로이드/타우 축적 | PETSurfer |

### 데이터셋 신청 시 권장 조합
```
최소 요청: T1w
권장 요청: T1w + T2/FLAIR + dMRI
전체 요청: T1w + T2/FLAIR + dMRI + resting fMRI
```

---

## 4. 현재 샘플 데이터

`data/sample/` 디렉터리에 파이프라인 테스트용 데이터 포함:

| 파일 | 출처 | 해상도 | 크기 |
|------|------|--------|------|
| `sub-pixar001/anat/sub-pixar001_T1w.nii.gz` | OpenNeuro ds000228 | 176×192×192 | 7.1MB |
| `sub-01/anat/sub-01_T1w.nii.gz` | OpenNeuro ds000101 | 176×256×256 | 10.2MB |

### 테스트 파이프라인 실행 순서
```bash
# 1. HD-BET 뇌 추출
hd-bet -i sub-01/anat/sub-01_T1w.nii.gz -o sub-01/anat/sub-01_T1w_brain.nii.gz

# 2. ANTs 정규화 (MNI 템플릿 기준)
antsRegistrationSyNQuick.sh -d 3 \
  -f $FSLDIR/data/standard/MNI152_T1_1mm.nii.gz \
  -m sub-01/anat/sub-01_T1w_brain.nii.gz \
  -o sub-01/anat/sub-01_T1w_MNI_

# 3. FastSurfer 분할
fastsurfer --t1 sub-01/anat/sub-01_T1w.nii.gz \
  --sid sub-01 --sd ./derivatives/fastsurfer
```

---

*문서 작성일: 2026-04-03*
*Brain Digital Twin (Synapse-D) 프로젝트*
