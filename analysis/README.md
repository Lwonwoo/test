# New_Barcode 로그 분석 (2026-10-02 Barcode.txt)

- `barcode_log_analyzer.py`: Barcode.txt 를 파싱하는 스크립트입니다. 표준 라이브러리만 쓰므로 Windows Python 에서 그대로 실행됩니다.
  - `python barcode_log_analyzer.py Barcode.txt --csv all.csv`: 검사 1건을 1행으로 내보냅니다.
  - `python barcode_log_analyzer.py Barcode.txt --compare-batches ng.csv`: 1차 배치 NG 이미지가 이후 모든 배치에서 어떻게 됐는지 이미지별로 비교합니다(배치마다 열 추가).
- `BARCODE_NG_ANALYSIS.md`: 분석 결과 전체 정리본입니다. 새 세션은 이 문서로 시작합니다.
- `ng378_batch1_vs_batch2.csv`: 1차 배치(DownSize=2) NG 378장과 2차 배치(DownSize=1) 결과를 비교한 표입니다.

| 컬럼 | 의미 |
|---|---|
| `b1_fail_ms` / `b2_fail_ms` | 실패한 시도별 소요 시간(ms)입니다. 직전 로그와의 시각 차이이므로 전처리 시간이 섞여 있습니다. |
| `b2_success_ms` | 성공한 시도의 소요 시간입니다. |
| `b2_class` | `OK`: 성공<br>`OK_MARGINAL`: 성공했지만 성공 시도 시간이 Timeout 이상(부하가 걸리면 NG 가 될 수 있음)<br>`NG_TIMEOUT_SUSPECT`: 한 시도라도 Timeout+40ms 이상 걸린 실패(시간 상한에 걸렸을 가능성)<br>`NG_NO_TIMEOUT`: 모든 시도가 빨리 끝난 실패(MIL 이 스스로 포기 → 이미지·파라미터 문제) |

로그 해석의 전제는 소스를 보지 못한 상태에서 세운 추정입니다. `MIL Insp : ForOther Reasons.` 1줄을 실패한 디코드 시도 1회로 보고, `Status : InspOK` 를 성공한 시도로 봅니다.
소스를 확인하면 이 전제부터 검증해야 합니다.
