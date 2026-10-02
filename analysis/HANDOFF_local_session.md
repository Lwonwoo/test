# 로컬 세션 인수인계 메모 (첫 메시지로 붙여넣기)

## 목표

MPTILib New_Barcode(MIL DataMatrix)에서 바코드 인식이 실패하는 원인을 찾는다.
MIL 런타임(릴리즈) 라이선스라서 디버거를 쓸 수 없다. 로그와 이미지만으로 판단해야 한다.

## 경로

| 항목 | 경로 |
|---|---|
| 소스 | `D:\work\AOI\pemtoFrameworkAll_R_4.0.0.7__Temp\MPTILib\New_Barcode` (cpp, h) |
| 생산 NG 이미지 | `C:\Users\USER\Downloads\Barcode_log_temp\log_temp\BCode` |
| 마지막 검사 이미지 | `D:\log_temp\Logimage\20261002102642` (10:26:42, Timeout=400, NG) |
| 설정 파일 | `C:\barcode\TestData\CItoP_dll.dat` |

설정 파일의 `[DataMatrix]` 섹션 현재 값은 `Distortion=0`, `DownSize=1`, `ThresholdMode=1`, `InspMilTimeOut=400`, `SearchMILRange=50` 이다.

## 로그(2026-10-02 Barcode.txt)에서 확인된 사실

- 검사 1건마다 McodeRead를 최대 4회 시도한다. 구조는 (변형 2가지) × (극성 2가지)이고, 극성은 실패하면 바꿔서 다시 읽는 설계다.
  - 4,680건 동안 1·3번째 시도는 한 번도 성공하지 못했다. 처음 시도하는 극성이 항상 틀린 것이다.
  - 성공은 2번째와 4번째 시도에서만 나왔다.
- 로그의 `ForOther Reasons.` 1줄은 실패한 시도 1회이고, `Status : InspOK`는 성공한 시도다.
  - 실패 6,953회가 전부 같은 문구여서 timeout과 not-found가 구분되지 않는다.
- Timeout은 McodeRead 한 번에 적용된다. 200ms로 설정하면 시도마다 약 300ms에서 잘린다.
- 1차 배치(4,259장, DownSize=2, Timeout=200) 결과는 NG 378장이다.
  - NG는 전부 FOV 333×345 제품(코드가 `59C*`로 시작, 23자리)에서 나왔다. 해당 제품 3,391장 중 378장이고, 다른 FOV 868장에서는 NG가 0장이다.
  - NG 378장의 모든 시도가 160ms 안에 끝났다. 시간 부족이 아니다.
- 2차 배치(같은 378장, DownSize=1, Timeout=200)에서는 201장이 OK가 됐다. 남은 177장은 이렇게 갈린다.
  - 159장은 한 시도 이상이 240~303ms에서 잘렸다. 시간 상한에 걸린 것이다.
  - 18장은 모든 시도가 190ms 이전에 실패했다. 시간과 무관한 인식 실패다.
- 생산 NG 이미지 중 91%(3,881/4,259)가 오프라인에서는 읽혔다.
- Distortion=1 테스트는 Timeout 200으로만 진행했다. "인식 불가"와 "200ms 안에 인식 불가"가 분리되지 않은 결과다.

## 코드에서 확인할 것

1. 재시도 루프에서 1·2번째 시도와 3·4번째 시도가 무엇이 다른지 (전처리, ThresholdMode 등)
2. 상태 로깅
   - `McodeGetResult(..., M_STATUS + M_TYPE_MIL_INT, &status)`에서 status 변수 타입이 `MIL_INT`인지
   - `M_STATUS_TIMEOUT_END`와 `M_STATUS_NOT_FOUND`에 해당하는 case가 있는지
   - 모든 실패가 `ForOther`로 빠지는 이유
3. `M_TIMEOUT`을 어디서 설정하는지, 그리고 200인데 왜 약 300ms에서 끊기는지 (McodeRead 앞뒤의 전처리 시간인지)
4. DownSize 구현. `MimResize`라면 보간 방식이 `M_NEAREST_NEIGHBOR`인지 `M_AVERAGE`/`M_BILINEAR`인지
5. `Distortion`, `ThresholdMode`, `SearchMILRange`가 각각 어떤 McodeControl 파라미터로 들어가는지
6. 셀 크기 관련 컨트롤(`M_CELL_SIZE_MIN`/`MAX` 등)을 설정하는지, 기본값을 쓰는지
7. 시도마다 바꾼 컨텍스트 값을 다음 이미지 전에 복구하는지 (우선순위 낮음)

## 이미지에서 확인할 것

- 59C\* 제품의 NG 이미지와 OK 이미지를 비교한다.
  - 셀 크기(px/cell), 대비, quiet zone, 손상 여부
  - DownSize=2(1/2 축소)일 때 셀이 몇 px까지 줄어드는지
- 시간과 무관하게 실패한 18장을 우선 본다. 목록은 GitHub `Lwonwoo/test` 저장소의 `claude/barcode-read-failure-analysis-rt69vn` 브랜치, `analysis/ng378_batch1_vs_batch2.csv`에서 `b2_class=NG_NO_TIMEOUT`인 행이다.

## 다음 실험 (인식 여부 우선이므로 timeout을 크게)

| 실행 | DownSize | Distortion | InspMilTimeOut | 대상 | 목적 |
|---|---|---|---|---|---|
| A | 1 | 0 | 3000 | 177장 | 2차 배치 NG 중 시간 때문에 실패한 건 분리 |
| B | 1 | 1 | 3000 | 177장 | 시간 제한이 없을 때 Distortion이 인식을 돕는지 |
| C | 2 | 0 | 3000 | 378장 | 대조군. 1차 배치 NG가 시간 문제가 아니었는지 확인 |

로그 비교 명령: `python barcode_log_analyzer.py Barcode.txt --compare-batches out.csv`
(스크립트는 같은 브랜치의 `analysis/` 폴더에 있다. 표준 라이브러리만 사용한다.)
