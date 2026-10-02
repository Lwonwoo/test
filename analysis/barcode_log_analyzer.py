#!/usr/bin/env python3
"""MPTILib New_Barcode 로그(Barcode.txt) 분석기 - 표준 라이브러리만 사용.

사용법:
    python barcode_log_analyzer.py Barcode.txt                 # 요약 출력
    python barcode_log_analyzer.py Barcode.txt --csv out.csv   # 검사 1건당 1행 CSV
    python barcode_log_analyzer.py Barcode.txt --compare-batches ng.csv
        # 1차 배치 NG 이미지가 이후 모든 배치에서 어떻게 됐는지 파일명 기준으로 비교 (배치마다 열 추가)
        # 설정(DownSize/Distortion/InspMilTimeOut)을 바꿔 가며 같은 로그에 배치를 여러 번 돌려도 된다.

로그 해석 전제 (소스 미확인 상태의 추정):
  - "PrepocProcess start" ~ "PrepocProcess end" 가 검사 1건.
  - "MIL Insp : ForOther Reasons." 1줄 = 실패한 디코드 시도 1회,
    "MIL Insp : Status : InspOK" = 성공한 시도. (시간 분포상 가장 일관된 해석)
  - 시도 시간 = 직전 로그 시각과의 차이(ms). 전처리 시간이 섞여 있다.
  - Timeout=200 에서 시도 시간이 약 300ms 에서 잘리는 현상이 관찰되어,
    시도 시간 >= Timeout + cap_margin 이면 timeout 의심으로 표시한다.
    (2차 배치 NG 의 최장 시도 시간은 110~189ms 군과 240~303ms 군으로 갈라진다.)
  - 성공 시도 시간 >= Timeout 이면 OK_MARGINAL (부하가 걸리면 NG 로 넘어갈 수 있는 건).
"""
import argparse
import collections
import csv
import datetime as dt
import re
import sys

TS_RE = re.compile(r'^\s*(\d{4})-(\d{2})-\s?(\d{1,2}) (\d{2}):(\d{2}):(\d{2})\.(\d{3}) - (.*)$')
SIM_RE = re.compile(r'\[Simulate Batch\] (\d+)/(\d+)\s+(\S+)\s+->\s+(OK|NG) \(([\d.]+) ms\)')


def parse(path):
    recs, cur, batch = [], None, 0
    with open(path, encoding='latin-1') as f:
        for raw in f:
            m = TS_RE.match(raw.rstrip('\r\n'))
            if not m:
                continue
            y, mo, d, h, mi, s, ms = map(int, m.groups()[:7])
            t = dt.datetime(y, mo, d, h, mi, s, ms * 1000)
            msg = m.group(8)
            if msg.startswith('PrepocProcess start'):
                cur = dict(t0=t, fov='', timeout=None, save=False, t_roi=None,
                           fails=[], ok_t=None, result=None, file='', batch=0, idx=0)
                recs.append(cur)
            elif cur is None:
                continue
            elif msg.startswith('PrePoc Start'):
                mm = re.search(r'FOV_X:(\d+), FOV_Y:(\d+)', msg)
                cur['fov'] = f'{mm.group(1)}x{mm.group(2)}'
            elif 'inputROIimg' in msg:
                mm = re.search(r'Timeout=(\d+)', msg)
                cur['timeout'] = int(mm.group(1)) if mm else None
                cur['t_roi'] = t
                cur['save'] = '_save' in msg
            elif msg.startswith('MIL Insp : ForOther'):
                cur['fails'].append(t)
            elif msg.startswith('MIL Insp : Status : InspOK'):
                cur['ok_t'] = t
            elif msg.startswith('PrepocProcess end Result'):
                cur['result'] = int(re.search(r'Result : (\d+)', msg).group(1))
            elif msg.startswith('[Simulate Batch]') and 'Done' not in msg:
                mm = SIM_RE.search(msg)
                if mm:
                    if int(mm.group(1)) == 1:
                        batch += 1
                    cur['batch'], cur['idx'], cur['file'] = batch, int(mm.group(1)), mm.group(3)

    def ms(a, b):
        return round((b - a).total_seconds() * 1000)

    for r in recs:
        prev, steps = r['t_roi'], []
        for t in r['fails']:
            steps.append(ms(prev, t) if prev else None)
            prev = t
        r['fail_ms'] = steps
        r['ok_ms'] = ms(prev, r['ok_t']) if (r['ok_t'] and prev) else None
    return recs


def classify(r, cap_margin):
    """OK / OK_MARGINAL / NG_TIMEOUT_SUSPECT / NG_NO_TIMEOUT."""
    tmo = r['timeout'] or 200
    lim = tmo + cap_margin
    if r['result'] == 1:
        return 'OK_MARGINAL' if (r['ok_ms'] or 0) >= tmo else 'OK'
    return 'NG_TIMEOUT_SUSPECT' if any(x is not None and x >= lim for x in r['fail_ms']) else 'NG_NO_TIMEOUT'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('log')
    ap.add_argument('--csv')
    ap.add_argument('--compare-batches')
    ap.add_argument('--base', type=int, default=1, help='비교 기준 배치 번호 (기본 1)')
    ap.add_argument('--cap-margin', type=int, default=40,
                    help='Timeout + 이 값(ms) 이상 걸린 시도를 timeout 의심으로 본다 (기본 40)')
    a = ap.parse_args()
    recs = parse(a.log)

    groups = collections.OrderedDict()
    for r in recs:
        key = f"batch{r['batch']}" if r['batch'] else 'live'
        groups.setdefault(key, []).append(r)
    for key, rs in groups.items():
        ok = sum(1 for r in rs if r['result'] == 1)
        print(f'[{key}] total={len(rs)} OK={ok} NG={len(rs) - ok}')
        pat = collections.Counter(
            (f"OK@attempt{len(r['fails']) + 1}" if r['result'] == 1 else f"NG({len(r['fails'])} fails)") for r in rs)
        print('   success position:', dict(sorted(pat.items())))
        fov = collections.defaultdict(lambda: [0, 0])
        for r in rs:
            fov[r['fov']][0] += 1
            fov[r['fov']][1] += r['result'] == 0
        print('   FOV total/NG:', {k: tuple(v) for k, v in sorted(fov.items(), key=lambda kv: -kv[1][0])})
        cls = collections.Counter(classify(r, a.cap_margin) for r in rs)
        print('   class:', dict(cls))
        print('   timeout:', dict(collections.Counter(r['timeout'] for r in rs)))

    if a.csv:
        with open(a.csv, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['batch', 'idx', 'file', 'start', 'fov', 'timeout', 'result', 'fails',
                        'fail_ms', 'success_ms', 'class'])
            for r in recs:
                w.writerow([r['batch'] or 'live', r['idx'], r['file'], r['t0'].strftime('%H:%M:%S.%f')[:-3],
                            r['fov'], r['timeout'], r['result'], len(r['fails']),
                            ' '.join(str(x) for x in r['fail_ms']), r['ok_ms'] or '', classify(r, a.cap_margin)])
        print('csv ->', a.csv)

    if a.compare_batches:
        # 기준 배치(--base)의 NG 이미지를 파일명으로 묶어, 모든 배치 결과를 열로 나란히 둔다.
        by_batch = collections.defaultdict(dict)
        for r in recs:
            if r['batch']:
                by_batch[r['batch']][r['file']] = r
        batches = sorted(by_batch)
        base = by_batch.get(a.base, {})
        targets = [fn for fn, r in base.items() if r['result'] == 0]
        header = ['file', 'fov']
        for b in batches:
            header += [f'b{b}_timeout', f'b{b}_result', f'b{b}_fail_ms', f'b{b}_success_ms', f'b{b}_class']
        n = {b: collections.Counter() for b in batches}
        with open(a.compare_batches, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(header)
            for fn in targets:
                row = [fn, base[fn]['fov']]
                for b in batches:
                    r = by_batch[b].get(fn)
                    if r is None:
                        row += [''] * 5
                        continue
                    c = classify(r, a.cap_margin)
                    n[b][c] += 1
                    row += [r['timeout'], r['result'], ' '.join(map(str, r['fail_ms'])), r['ok_ms'] or '', c]
                w.writerow(row)
        print(f'batch{a.base} NG {len(targets)}장의 배치별 결과 -> {a.compare_batches}')
        for b in batches:
            print(f'   batch{b}:', dict(n[b]))


if __name__ == '__main__':
    sys.exit(main())
