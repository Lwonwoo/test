# MPTILib New_Barcode 바코드 인식 실패 분석

- 분석일: 2026-10-02
- 근거: `Barcode.txt` 로그 1개(48,843줄)와 설정 파일 캡처. 소스와 이미지는 아직 보지 못했다.
- 확신 수준 표기:
  - **[확실]** 로그 수치로 직접 확인됨
  - **[가능성높음]** 강한 추론
  - **[추측]** 소스나 이미지로 검증이 필요함

> **새 세션에서 이어갈 때**
> 이 파일을 첫 메시지로 붙여넣는다. 또는 로컬에 저장한 뒤 "BARCODE_NG_ANALYSIS.md 읽고 8~10장 진행해줘"라고 요청한다.
> 할 일은 세 가지다.
> 1. 8장: 소스 코드 확인
> 2. 9장: 이미지 측정
> 3. 10장: 실험 로그 비교

---

## 1. 목표와 제약

- MIL DataMatrix 판독(McodeRead)이 실패하는 원인을 찾는다.
- MIL 런타임(릴리즈) 라이선스라서 디버거를 붙일 수 없다. **로그와 이미지만으로 판단해야 한다.**
- 우선순위는 **판독 시간보다 인식 여부**다. Timeout은 설정 파일 값을 그대로 쓴다.
- 진행 순서: 생산 NG 이미지로 원인을 찾은 다음 전수검사를 한다.

## 2. 경로

| 항목 | 경로 |
|---|---|
| 소스 (cpp, h) | `D:\work\AOI\pemtoFrameworkAll_R_4.0.0.7__Temp\MPTILib\New_Barcode` |
| 생산 NG 이미지 (4,000장 이상) | `C:\Users\USER\Downloads\Barcode_log_temp\log_temp\BCode` |
| 마지막 검사 이미지 (10:26:42, NG) | `D:\log_temp\Logimage\20261002102642` |
| 설정 파일 | `C:\barcode\TestData\CItoP_dll.dat` |
| PublicPattern | `C:\Eagle3D_64x\PROGRAM\PPDB\PublicPattern` |
| DLL 정보 (로그) | MachineType AOI, LicenseType Both, DLLVersion 1,1,111,11, LicenseNum 3 → AOI는 MIL 사용 |

## 3. 설정 파일 (`CItoP_dll.dat`)

```ini
[BarcodeInsp]
type=0
SaveImage=0
LogLevel=3            ; 변경됨
UseCharSpace=0
Event=0
UseNewBarcodeDTK=1

[DataMatrix]
Distortion=0          ; 1 -> 0
DownSize=1            ; 2 -> 1
ThresholdMode=1
InspMilTimeOut=400    ; 200 -> 400
SearchMILRange=50
```

| 시점 | Distortion | DownSize | Timeout | 비고 |
|---|---|---|---|---|
| 그 이전 테스트 | 1 | ? | 200 | NG가 많아서 Distortion을 0으로 바꿈 |
| 1차 배치 (10:06~10:15) | 0 | 2 | 200 | 로그의 Timeout=200 |
| 2차 배치 (10:20~10:23) | 0 | 1 | 200 | DownSize만 변경 |
| 마지막 검사 1장 (10:26:42) | 0 | 1 | 400 | `_save` 로그, 이미지 저장됨 |

`ThresholdMode`, `SearchMILRange`, `Distortion`, `DownSize`가 각각 어떤 MIL 파라미터로 들어가는지는 **소스로 확인해야 한다** (8장).

## 4. 사용자가 확인해 준 사항

1. Distortion=1 테스트는 Timeout 200ms로 진행했다.
2. BCode 폴더의 이미지는 **생산에서 NG가 난 이미지**다.
3. Timeout은 **MIL 판독 1회(McodeRead)에 적용**된다. 검사 전체 시간이 아니다.
4. 판독에 실패하면 **극성을 바꿔서 다시 시도**하는 설계다. 극성은 인식률과 무관하므로 분석 대상에서 뺀다.
5. 원인을 아직 모른다. 그래서 이 분석을 요청했다.

## 5. 로그 구조와 해석

검사 1건의 로그는 다음과 같다. 실패한 경우다.

```
PrepocProcess start
PrePoc Start => StartPt_X:00, StartPt_Y:00, EndPt_X:332, EndPt_Y:344, FOV_X:333, FOV_Y:345
PrepocProcess_inputimg, BarcodeType : DATAMATRIX
PrepocProcess_inputROIimg   Timeout=200
MIL Insp : ForOther Reasons.     <- 시도 1 실패
MIL Insp : ForOther Reasons.     <- 시도 2 실패
MIL Insp : ForOther Reasons.     <- 시도 3 실패
MIL Insp : ForOther Reasons.     <- 시도 4 실패
PrepocProcess end Result : 0 Barcode :
Barcode End
[Simulate Batch] n/N  파일명.bmp  ->  NG (xxx ms)
```

- **[가능성높음]** `ForOther Reasons.` 1줄은 **실패한 판독 1회**이고, `Status : InspOK`는 **성공한 판독**이다. 근거는 세 가지다.
  - 1번째 시도의 소요 시간이 결국 성공한 건과 끝까지 실패한 건에서 똑같다.
    - 1차 배치: 80ms 대 75ms
    - 2차 배치: 96ms 대 97ms
  - 같은 위치의 시도라도 성공한 경우가 실패한 경우보다 짧다.
  - 10:03:49 건은 1번째 시도가 204ms(timeout)에 끝났고, 9ms 뒤에 성공했다.
- 시도는 최대 4회이고, (전처리 변형 2가지) × (극성 2가지)로 추정한다.
- **[확실]** 4,680건 동안 1·3번째 시도는 성공이 0건이다. 성공은 2번째(3,822건)와 4번째(301건)에서만 나왔다. 처음 시도하는 극성이 항상 틀린 것이고, 설계상 정상이다.
- 시도 시간은 로그 시각의 차이로 잰다. **McodeRead 전후의 전처리 시간이 섞여 있다.**
- **[확실]** 실패 6,953회가 전부 `ForOther Reasons.`다. timeout인지 못 찾은 것인지를 로그만으로는 구분할 수 없다.

## 6. 수치 결과

### 6.1 실행별 결과

| 실행 | 시각 | 장수 | OK | NG | 평균 시간 |
|---|---|---|---|---|---|
| 단건 검사 | 10:03:45 ~ 10:04:43 | 42 | 41 | 1 | - |
| 1차 배치 (DownSize=2) | 10:06:12 ~ 10:15:48 | 4,259 | 3,881 | **378** | 135ms/장 |
| 2차 배치 (1차 NG 378장, DownSize=1) | 10:20:48 ~ 10:23:57 | 378 | **201** | **177** | 499ms/장 |
| 마지막 검사 (Timeout=400) | 10:26:42 | 1 | 0 | 1 | - |

- 이미지 촬영 기간(파일명 기준): 2026-08-13 15:46 ~ 08-21 20:20
- 2차 배치의 이미지와 순서는 1차 배치 NG 378장과 정확히 같다.

### 6.2 1차 배치의 FOV(제품)별 NG

| FOV | 코드 접두 | 장수 | NG |
|---|---|---|---|
| **333×345** | **59CA, 59C9, 59C7, 59CB, 59C8** (23자리) | **3,391** | **378 (11.1%)** |
| 333×321 | 5NAD | 302 | 0 |
| 343×321 | 5NAD | 149 | 0 |
| 387×378 | 5QQ* | 132 | 0 |
| 310×328 | 5QQE, 5QQD | 120 | 0 |
| 306×319 | 5NAD | 75 | 0 |
| 328×313 | XT70 | 69 | 0 |
| 337×346 | 5NAD | 15 | 0 |
| 332×321 | 5NAD | 5 | 0 |
| 318×306 | XT70 | 1 | 0 |

59C\* 제품(촬영 08-14 20:21 ~ 08-18 13:24)의 일별 NG율은 8.5%, 14.0%, 7.9%, 13.6%, 10.8%다.

### 6.3 시도별 소요 시간 (중앙값, ms)

| 구분 | 1차 배치 (DownSize=2) | 2차 배치 (DownSize=1) |
|---|---|---|
| 2번째 시도에서 성공 | 시도1 80 → 성공 5 | 시도1 96 → 성공 114 (최대 292) |
| 4번째 시도에서 성공 | 75 / 114 / 65 → 성공 28 | 95 / 285 / 101 → 성공 110 |
| 끝까지 실패 | 75 / 112 / 65 / 85, **최대 160** | 97 / 284 / 101 / 249, **약 303에서 잘림** |

- **[확실]** 1차 배치 NG 378장은 모든 시도가 160ms 안에 끝났다. Timeout 200에 닿지 않았다.
- **[확실]** 2차 배치에서는 2·4번째 시도가 약 300~303ms에서 잘린다. Timeout=200일 때 시도 1회의 상한은 약 300ms다(McodeRead 200 + 전처리 약 100으로 추정).
- **[확실]** Timeout=400인 마지막 검사의 시도 시간은 93 / 359 / 93 / 254ms였다. 상한이 Timeout을 따라 올라갔다.

### 6.4 2차 배치 분류 (`ng378_batch1_vs_batch2.csv`의 `b2_class`)

| 분류 | 장수 | 기준 |
|---|---|---|
| OK | 158 | 성공 시도가 200ms 미만 |
| OK_MARGINAL | 43 | 성공 시도가 200ms 이상. 부하가 걸리면 NG가 될 수 있음 |
| NG_TIMEOUT_SUSPECT | **159** | 한 시도 이상이 240~303ms (그중 66장은 300~303ms) |
| NG_NO_TIMEOUT | **18** | 모든 시도가 190ms 이전에 실패 |

### 6.5 기타 관찰

- **[확실]** 10:03:47 단건 검사(FOV 337×346)는 시도 시간이 204 / 301 / 167 / 303ms로 상한에 걸려 NG였다. 같은 FOV 15장은 1차 배치에서 전부 64~82ms에 OK였다.
  - DLL을 연 시각은 10:01:35로, 그 약 2분 뒤다. 첫 검사의 1번째 시도도 528ms가 걸렸다(콜드 스타트).
- 직전 이미지 결과가 다음 결과에 영향을 주는지 확인했다.
  - 1차 배치: NG 다음 NG일 확률 31%, OK 다음 NG일 확률 5.3%. 생산 시간대가 몰린 탓으로 보인다.
  - 2차 배치: 43% 대 51%로 의존성이 없다. → **[가능성높음]** 컨텍스트 상태가 다음 이미지로 새는 문제는 없다.

## 7. 결론

| # | 확신 | 내용 |
|---|---|---|
| F1 | [확실] | NG는 **FOV 333×345 / 59C\* 제품에만** 있다. 다른 제품은 868장 중 0장이다. |
| F2 | [가능성높음] | 1차 배치 NG의 원인은 시간이 아니라 **DownSize=2로 줄어든 셀 크기**다. 모든 시도가 160ms 안에 끝났고(MIL이 스스로 포기), DownSize=1에서 201장이 회복됐다. 셀 크기 실측은 이미지로 확인해야 한다. |
| F3 | [가능성높음] | DownSize=1 이후에는 **시도당 timeout이 주된 제약**이다. 남은 NG 177장 중 159장이 시간 상한에서 잘렸다. 시간과 무관하게 실패한 것은 18장이다. |
| F4 | [확실] | 지금까지의 결과(2차 배치, Distortion=1 테스트)는 **"인식 불가"와 "200ms 안에 인식 불가"가 섞여 있다.** 인식 여부만 보려면 Timeout을 크게 잡고 다시 측정해야 한다. |
| F5 | [추측] | Distortion=1에서 NG가 늘어난 것도 **보정 탐색이 무거워 200ms에 잘렸기 때문**일 수 있다. 실험 B로 확인한다. |
| F6 | [가능성높음] | 생산 NG 이미지 중 **91%(3,881/4,259)가 지금 설정에서는 오프라인으로 읽힌다.** 생산 NG 대부분은 원인이 이미지가 아니라 당시 설정이나 생산 중 조건(부하로 인한 timeout 등)에 있다. |
| F7 | [확실] | 로그가 실패 원인(MIL status 값), 실제로 적용된 설정값, 시도별 변형을 남기지 않는다. 그래서 로그만으로 진단하는 데 한계가 있다. |
| F8 | [확실] | 마지막 검사(20261002102642)는 Timeout=400에서도 상한에 닿지 않고 실패했다. 시간과 무관한 인식 실패이므로 이미지 분석 1순위 샘플이다. |

## 8. 소스에서 확인할 것 (우선순위 순)

> MIL 버전에 따라 상수 이름이 다를 수 있다.

1. **DownSize 구현**
   - 축소 함수와 보간 방식. `MimResize`라면 `M_NEAREST_NEIGHBOR`인지 `M_AVERAGE`/`M_BILINEAR`인지 본다.
   - nearest 방식은 작은 셀을 깨뜨린다.
   - 축소 비율이 정확히 1/DownSize인지, ROI를 자르기 전과 후 중 언제 축소하는지 본다.
2. **셀 크기 관련 McodeControl**
   - `M_CELL_SIZE_MIN`/`MAX`, `M_CELL_NUMBER_X`/`Y` 등을 설정하는지, 기본값을 쓰는지
   - DownSize와 연동되는지
3. **Distortion, ThresholdMode, SearchMILRange의 매핑**
   - 예: `M_DECODE_ALGORITHM`(`M_CODE_DEFORMED`), `M_DISTORTION`, `M_THRESHOLD_MODE`, 검색 영역이나 각도
4. **재시도 루프**
   - 1·2번째 시도와 3·4번째 시도의 전처리가 무엇이 다른지
   - 각 시도의 입력 버퍼가 올바른지 (자식 버퍼 오프셋, 크기, 축소본인지 원본인지)
5. **상태 로깅**
   - `McodeGetResult(res, M_GENERAL, M_GENERAL, M_STATUS + M_TYPE_MIL_INT, &status)`에서 `status`가 `MIL_INT`인지
   - 타입이 맞지 않으면(예: `long`에 `M_TYPE_MIL_INT` 없이 받으면) 릴리즈 빌드에서 값이 깨질 수 있다.
   - `M_STATUS_TIMEOUT_END`와 `M_STATUS_NOT_FOUND` case가 있는지, 왜 전부 `ForOther`로 빠지는지
6. **`M_TIMEOUT` 설정 위치**
   - 시도마다 설정하는지, Timeout=200인데 왜 약 300ms에서 끊기는지 (McodeRead 밖의 전처리 시간인지)
7. **시도 간 컨텍스트 복구 여부** (우선순위 낮음, 6.5 참고)

**로그 개선 제안**: 아래 값을 로그에 남기면 이후에는 로그만으로 원인을 구분할 수 있다.
- 시도마다: 시도 번호, 변형, 극성, McodeRead 소요 시간(`MappTimer`), MIL status 원래 값
- 검사 시작 시: 실제로 적용된 설정값(DownSize, Distortion, ThresholdMode), 축소 후 이미지 크기

## 9. 이미지에서 확인할 것

### 측정 항목 (59C\* NG와 같은 제품 OK 비교)

- 셀(모듈) 크기(px/cell)와 심볼 크기(행×열)
- DownSize=2(1/2 축소)일 때의 셀 크기
- 대비(흑백 셀 밝기 차이), 초점(블러), quiet zone, 손상이나 반사
- 다른 디코더(예: zxing-cpp)로 교차 판독. 다른 디코더는 읽는데 MIL만 못 읽는다면 원인은 MIL 설정이나 코드 쪽이다.

### 샘플

1차 배치 기준 분류다.

- **최우선:** `D:\log_temp\Logimage\20261002102642`의 마지막 검사 이미지
- **시간과 무관한 실패 18장** (2차 배치 `NG_NO_TIMEOUT`):

```
BCodeMILNG_20260815182210633.bmp  BCodeMILNG_20260815221535726.bmp  BCodeMILNG_20260816034136829.bmp
BCodeMILNG_20260816112921376.bmp  BCodeMILNG_20260817014132558.bmp  BCodeMILNG_20260817014305153.bmp
BCodeMILNG_20260817014855415.bmp  BCodeMILNG_20260817044231872.bmp  BCodeMILNG_20260817074830312.bmp
BCodeMILNG_20260817103155665.bmp  BCodeMILNG_20260817122909646.bmp  BCodeMILNG_20260817154532485.bmp
BCodeMILNG_20260817182200397.bmp  BCodeMILNG_20260818054235324.bmp  BCodeMILNG_20260818063542164.bmp
BCodeMILNG_20260818090832223.bmp  BCodeMILNG_20260818090959413.bmp  BCodeMILNG_20260818102950313.bmp
```

- **시간 상한(약 300ms)에서 잘린 NG** (전체 66장 중 예시): `BCodeMILNG_20260814215232119.bmp`, `BCodeMILNG_20260814222139071.bmp`, `BCodeMILNG_20260815001349691.bmp`
- **DownSize=1에서 빠르게 회복된 이미지**: `BCodeMILNG_20260814231651447.bmp`, `BCodeMILNG_20260815113212608.bmp`, `BCodeMILNG_20260815125911758.bmp`
- **같은 제품의 정상(DownSize=2에서도 OK)**: `BCodeMILNG_20260814203317516.bmp`, `BCodeMILNG_20260817221444550.bmp`

## 10. 다음 실험 (인식 여부 측정, Timeout을 크게)

| 실행 | DownSize | Distortion | InspMilTimeOut | 대상 | 확인할 것 |
|---|---|---|---|---|---|
| A | 1 | 0 | 3000 | 2차 배치 NG 177장 | 시간에 걸렸던 159장 중 몇 장이 읽히는지 |
| B | 1 | 1 | 3000 | 177장 | 시간 제약이 없을 때 Distortion이 인식을 돕는지 (F5) |
| C | 2 | 0 | 3000 | 1차 배치 NG 378장 | 대조군. 거의 그대로 NG면 F2(크기 문제)가 확인됨 |
| D (선택) | 2 | 1 | 3000 | 378장 | 축소 상태에서 Distortion의 효과 |

- 최악의 경우 이미지 1장에 약 4 × 3.1초가 걸린다. 177장이면 최대 약 35분이다.
- A와 B를 거친 뒤에도 남는 NG가 MIL로 진짜 못 읽는 이미지다. 이 이미지를 9장의 방법으로 분석한다.
- 전수검사도 같은 큰 Timeout으로 돌려야 인식률을 볼 수 있다. 200ms로 돌리면 결과에 다시 시간 요인이 섞인다.
- 실행 후 비교 명령: `python barcode_log_analyzer.py Barcode.txt --compare-batches out.csv`
  - 같은 로그에 배치를 여러 번 돌려도 된다. 배치마다 열이 추가된다.

## 11. 미해결 질문

1. **생산 당시(8/13~8/21) 설정이 무엇이었나?** Distortion, DownSize, Timeout 값이 필요하다.
   - Distortion=1에 200ms였다면 F6의 91%가 그것으로 설명된다.
   - 1차 배치와 같은 설정이었다면 생산 중에만 있는 조건(AOI 동시 처리 부하 등)이 원인이다. 이 경우 NG 파일 재검사로는 원인을 재현할 수 없다.
2. **왜 59C\* 제품만 실패하나?** 코드의 물리적 크기, 셀 수, 마킹 방식, 조명, 표면 재질이 다른 제품과 무엇이 다른지 확인해야 한다. 제품 특성이 원인이라면 전역 설정을 바꾸기보다 레시피별 DownSize가 맞을 수 있다.
3. 전수검사를 할 때 다른 제품에서 DownSize=1의 부작용(새 NG, 처리 시간)이 없는지 확인해야 한다.

## 12. 산출물

GitHub `Lwonwoo/test` 저장소, 브랜치 `claude/barcode-read-failure-analysis-rt69vn`의 `analysis/` 폴더에 있다.

| 파일 | 설명 |
|---|---|
| `BARCODE_NG_ANALYSIS.md` | 이 문서 |
| `barcode_log_analyzer.py` | 로그 분석기. Python 3 표준 라이브러리만 사용한다. 옵션: `--csv`(검사 1건당 1행), `--compare-batches`(기준 배치 NG의 배치별 결과) |
| `ng378_batch1_vs_batch2.csv` | 1차 배치 NG 378장의 1차·2차 시도 시간과 분류 |
